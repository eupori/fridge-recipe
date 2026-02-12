"""
YouTube 검색 + Haiku 구조화 어댑터

YouTube Data API v3로 인기 레시피 영상을 검색한 뒤,
Haiku 4.5로 영상 메타데이터에서 레시피 정보를 구조화합니다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx
from anthropic import Anthropic

from app.core.config import settings
from app.data.allergen_derivatives import expand_exclusions
from app.models.recommendation import Recipe, RecommendationCreate

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


@dataclass
class VideoInfo:
    """YouTube 영상 메타데이터"""

    video_id: str
    title: str
    description: str
    view_count: int
    channel_title: str


class YouTubeRecipeAdapter:
    """YouTube 검색 + Haiku 구조화로 레시피 생성"""

    def __init__(self):
        if not settings.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY가 설정되지 않았습니다")
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다 (Haiku 호출용)")

        self.youtube_api_key = settings.youtube_api_key
        self.haiku_client = Anthropic(api_key=settings.anthropic_api_key)

    async def generate_recipes(self, payload: RecommendationCreate) -> list[Recipe]:
        """
        YouTube 검색 → Haiku 구조화로 레시피 3개 생성

        Args:
            payload: 사용자 입력 (재료, 제약사항)

        Returns:
            list[Recipe]: 3개 레시피 (image_url=None, 이미지는 기존 서비스가 처리)

        Raises:
            ValueError: 검색 결과 부족 또는 구조화 실패
        """
        # 1. 검색 쿼리 생성
        queries = self._build_search_queries(payload)
        logger.info(f"YouTube 검색 쿼리: {queries}")

        # 2. YouTube 검색
        video_ids = await self._search_youtube(queries)
        if not video_ids:
            raise ValueError("YouTube 검색 결과가 없습니다")

        # 3. 영상 상세 정보 조회
        videos = await self._get_video_details(video_ids)
        if not videos:
            raise ValueError("YouTube 영상 상세 정보를 가져올 수 없습니다")

        # 4. 필터링 및 랭킹
        ranked = self._filter_and_rank(videos, payload)
        if len(ranked) < 3:
            raise ValueError(f"관련 영상이 부족합니다: {len(ranked)}개 (최소 3개 필요)")

        # 5. Haiku로 레시피 구조화
        recipes = self._structure_with_haiku(ranked[:8], payload)
        return recipes

    def _build_search_queries(self, payload: RecommendationCreate) -> list[str]:
        """재료 기반 YouTube 검색 쿼리 생성"""
        ingredients = payload.ingredients
        time_limit = payload.constraints.time_limit_min

        queries = []

        # 메인 쿼리: 상위 재료 3개 + "레시피 간단"
        main_ingredients = " ".join(ingredients[:3])
        queries.append(f"{main_ingredients} 레시피 간단")

        # 보조 쿼리: 시간 제한 포함
        if len(ingredients) >= 2:
            queries.append(f"{ingredients[0]} {ingredients[1]} 요리 {time_limit}분")

        # 보조 쿼리: 개별 재료 레시피
        if len(ingredients) >= 1:
            queries.append(f"{ingredients[0]} 요리 레시피 자취")

        return queries

    async def _search_youtube(self, queries: list[str], max_results_per_query: int = 5) -> list[str]:
        """YouTube Data API v3 검색, 중복 제거된 video ID 반환"""
        seen_ids: set[str] = set()
        video_ids: list[str] = []

        async with httpx.AsyncClient(timeout=10) as client:
            for query in queries:
                try:
                    resp = await client.get(
                        YOUTUBE_SEARCH_URL,
                        params={
                            "part": "snippet",
                            "q": query,
                            "type": "video",
                            "maxResults": max_results_per_query,
                            "relevanceLanguage": "ko",
                            "regionCode": "KR",
                            "order": "relevance",
                            "key": self.youtube_api_key,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    for item in data.get("items", []):
                        vid = item["id"].get("videoId")
                        if vid and vid not in seen_ids:
                            seen_ids.add(vid)
                            video_ids.append(vid)

                except httpx.HTTPStatusError as e:
                    logger.warning(f"YouTube 검색 실패 (쿼리: {query}): {e.response.status_code}")
                    if e.response.status_code == 403:
                        raise ValueError("YouTube API 할당량 초과 또는 API 키 오류") from e
                except httpx.RequestError as e:
                    logger.warning(f"YouTube 검색 네트워크 오류 (쿼리: {query}): {e}")

        logger.info(f"YouTube 검색 완료: {len(video_ids)}개 영상 발견")
        return video_ids

    async def _get_video_details(self, video_ids: list[str]) -> list[VideoInfo]:
        """videos.list API로 영상 설명, 조회수 등 상세 정보 조회"""
        if not video_ids:
            return []

        # API는 최대 50개까지 한 번에 조회 가능
        ids_str = ",".join(video_ids[:15])

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                YOUTUBE_VIDEOS_URL,
                params={
                    "part": "snippet,statistics",
                    "id": ids_str,
                    "key": self.youtube_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})

            videos.append(
                VideoInfo(
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    view_count=int(stats.get("viewCount", 0)),
                    channel_title=snippet.get("channelTitle", ""),
                )
            )

        logger.info(f"YouTube 상세 정보 조회 완료: {len(videos)}개")
        return videos

    def _filter_and_rank(self, videos: list[VideoInfo], payload: RecommendationCreate) -> list[VideoInfo]:
        """영상을 관련성 + 인기도로 필터링/정렬"""
        exclude_set = expand_exclusions(payload.constraints.exclude)

        filtered = []
        for video in videos:
            title_lower = video.title.lower()

            # 제외 재료가 제목에 있으면 스킵
            if any(e in title_lower for e in exclude_set if e):
                logger.debug(f"제외 재료 포함, 스킵: {video.title}")
                continue

            filtered.append(video)

        # 레시피 관련성 점수 + 조회수로 정렬
        recipe_keywords = ["레시피", "요리", "만들기", "만드는", "간단", "자취", "초간단", "백종원"]

        def score(v: VideoInfo) -> float:
            title_lower = v.title.lower()
            # 레시피 키워드 매칭 점수
            keyword_score = sum(1 for kw in recipe_keywords if kw in title_lower)
            # 사용자 재료 매칭 점수
            ingredient_score = sum(1 for ing in payload.ingredients if ing in title_lower)
            # 조회수 점수 (로그 스케일)
            import math

            view_score = math.log10(max(v.view_count, 1))
            return keyword_score * 3 + ingredient_score * 5 + view_score

        filtered.sort(key=score, reverse=True)
        return filtered

    def _structure_with_haiku(
        self, videos: list[VideoInfo], payload: RecommendationCreate
    ) -> list[Recipe]:
        """Haiku 4.5로 영상 메타데이터에서 레시피 구조화"""
        # 영상 정보를 텍스트로 변환
        video_summaries = []
        for i, v in enumerate(videos, 1):
            # 설명은 500자까지만 (토큰 절약)
            desc = v.description[:500] if v.description else "(설명 없음)"
            video_summaries.append(
                f"[영상 {i}] 제목: {v.title}\n"
                f"채널: {v.channel_title}\n"
                f"조회수: {v.view_count:,}회\n"
                f"설명:\n{desc}"
            )

        videos_text = "\n\n---\n\n".join(video_summaries)

        # 제외 재료 (파생 포함)
        expanded_exclude = expand_exclusions(payload.constraints.exclude)
        exclude_str = ", ".join(sorted(expanded_exclude)) if expanded_exclude else "없음"

        system_prompt = """당신은 한국 가정 요리 전문가입니다. YouTube 영상 정보를 분석하여 레시피를 구조화합니다.

규칙:
1. 정확히 3개의 서로 다른 레시피를 생성
2. 각 레시피는 4-8개의 조리 단계
3. 모든 텍스트는 한국어
4. 시간 제한을 반드시 준수
5. 제외 재료는 어떤 형태로도 사용 금지
6. 영상 정보를 참고하되, 실제로 실현 가능한 레시피로 구성
7. 재료명은 분량/수량 없이 재료명만 (예: "계란" O, "계란 2개" X)
8. 반드시 한 끼 식사(또는 든든한 간식)로 먹을 수 있는 실제 요리만 추천
   - 양념, 소스, 오일, 드레싱, 조미료만 만드는 레시피는 절대 포함 금지
   - 예: "마늘 고추기름", "간장 소스", "양념장", "장아찌" 등은 요리가 아닙니다
   - 재료가 적더라도 볶음밥, 국, 전, 볶음 등 실제 요리를 만들어야 합니다

출력: JSON 배열만 반환 (마크다운/설명 없이)
각 레시피 필드: title, time_min, servings, summary, ingredients_total, steps, tips, warnings"""

        user_prompt = f"""아래 YouTube 영상 정보를 분석하여, 사용자 조건에 맞는 레시피 3개를 JSON으로 구조화해주세요.

중요: 반드시 한 끼 식사로 먹을 수 있는 실제 요리만 추천하세요!
양념/소스/오일/장아찌/조미료 레시피는 절대 포함하지 마세요.
사용자 재료가 양념류(마늘, 고추, 파 등)뿐이더라도 밥, 계란, 면 등 기본 식재료를 추가하여 실제 식사가 되는 요리를 만드세요.

=== 사용자 조건 ===
보유 재료: {', '.join(payload.ingredients)}
조리 시간 제한: {payload.constraints.time_limit_min}분 이내
인분: {payload.constraints.servings}인분
제외 재료 (파생 포함): {exclude_str}

=== YouTube 영상 정보 ===
{videos_text}

=== 출력 형식 ===
[
  {{
    "title": "레시피 제목 (20자 이내)",
    "time_min": 조리시간(분),
    "servings": 인분수,
    "summary": "한 줄 설명 (50자 이내)",
    "ingredients_total": ["재료1", "재료2", ...],
    "steps": ["단계1", "단계2", ...],
    "tips": ["팁1"],
    "warnings": ["주의사항1"]
  }},
  ...
]

JSON 배열만 출력하세요."""

        logger.info("Haiku로 레시피 구조화 시작")
        response = self.haiku_client.messages.create(
            model=settings.haiku_model,
            max_tokens=settings.haiku_max_tokens,
            temperature=settings.haiku_temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        content = response.content[0].text
        logger.debug(f"Haiku 응답: {content[:200]}...")

        # JSON 파싱
        recipes_data = self._parse_response(content)

        # Pydantic 모델 변환
        recipes = []
        for r in recipes_data:
            recipe = Recipe(
                title=r.get("title", "제목 없음"),
                time_min=r.get("time_min", 15),
                servings=r.get("servings", payload.constraints.servings),
                summary=r.get("summary", ""),
                image_url=None,
                ingredients_total=r.get("ingredients_total", []),
                ingredients_have=[],
                ingredients_need=[],
                steps=r.get("steps", []),
                tips=r.get("tips", []),
                warnings=r.get("warnings", []),
            )
            recipes.append(recipe)

        if len(recipes) != 3:
            raise ValueError(f"Haiku가 {len(recipes)}개 레시피 생성 (3개 필요)")

        logger.info(f"YouTube+Haiku 레시피 생성 성공: {[r.title for r in recipes]}")
        return recipes

    def _parse_response(self, content: str) -> list[dict]:
        """Haiku 응답에서 JSON 배열 추출"""
        content = content.strip()

        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            json_str = content[start:end].strip()
        else:
            json_str = content

        recipes_data = json.loads(json_str)

        if not isinstance(recipes_data, list):
            raise ValueError("Haiku 응답이 배열 형태가 아닙니다")

        return recipes_data
