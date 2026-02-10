"""
LLM 어댑터 - Claude API를 사용한 레시피 생성
"""

from __future__ import annotations

import json
import logging
import random

from anthropic import Anthropic

from app.core.config import settings
from app.data.allergen_derivatives import expand_exclusions
from app.models.recommendation import Recipe, RecommendationCreate

logger = logging.getLogger(__name__)


class RecipeLLMAdapter:
    """Claude API를 사용한 레시피 생성 어댑터"""

    # 다양성을 위한 요리 스타일 리스트
    COOKING_STYLES = [
        "전통 한식",
        "퓨전 요리",
        "간단 자취 요리",
        "건강식",
        "야식 메뉴",
        "브런치 메뉴",
        "도시락 반찬",
        "술안주",
        "분식",
        "양식 스타일",
        "일식 스타일",
        "중식 스타일",
    ]

    COOKING_METHODS = [
        "볶음 요리 중심",
        "국/찌개 포함",
        "구이 요리 포함",
        "찜 요리 포함",
        "무침/샐러드 포함",
        "전/부침 포함",
        "면 요리 포함",
        "밥 요리 중심",
    ]

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY가 설정되지 않았습니다")

        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.llm_max_tokens

    def generate_recipes(self, payload: RecommendationCreate, max_retries: int = 2) -> list[Recipe]:
        """
        사용자 재료와 제약사항으로 3개 레시피 생성 (재시도 로직 포함)

        Args:
            payload: 사용자 입력 (재료, 제약사항)
            max_retries: 최대 재시도 횟수

        Returns:
            List[Recipe]: 3개의 레시피 (ingredients_total만 포함, have/need는 별도 처리)

        Raises:
            ValueError: API 호출 실패 또는 파싱 실패
        """
        for attempt in range(max_retries):
            try:
                # 1. 프롬프트 구성
                system_prompt = self._build_system_prompt()
                user_prompt = self._build_user_prompt(payload)

                # 2. Claude API 호출
                logger.info(f"LLM 레시피 생성 시도 {attempt + 1}/{max_retries}")
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )

                # 3. 응답 파싱
                content = response.content[0].text
                logger.debug(f"LLM 응답: {content[:200]}...")
                recipes_data = self._parse_response(content)

                # 4. Pydantic 모델로 변환 (기본값으로 빈 리스트 제공)
                recipes = []
                for r in recipes_data:
                    # ingredients_have, ingredients_need는 나중에 설정
                    # 여기서는 일단 빈 리스트로 초기화
                    recipe = Recipe(
                        title=r.get("title", "제목 없음"),
                        time_min=r.get("time_min", 15),
                        servings=r.get("servings", payload.constraints.servings),
                        summary=r.get("summary", ""),
                        image_url=None,  # 나중에 설정
                        ingredients_total=r.get("ingredients_total", []),
                        ingredients_have=[],  # 나중에 설정
                        ingredients_need=[],  # 나중에 설정
                        steps=r.get("steps", []),
                        tips=r.get("tips", []),
                        warnings=r.get("warnings", []),
                    )
                    recipes.append(recipe)

                # 5. 레시피 개수 검증
                if len(recipes) != 3:
                    raise ValueError(f"레시피 개수 오류: {len(recipes)}개 생성됨 (3개 필요)")

                logger.info(f"LLM 레시피 생성 성공: {len(recipes)}개")
                return recipes

            except Exception as e:
                logger.warning(f"LLM 생성 실패 (시도 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    # 최종 실패 시 더미 데이터 폴백
                    logger.error(f"LLM 생성 최종 실패, 더미 레시피 반환: {str(e)}")
                    return self._fallback_dummy_recipes(payload)
                # 재시도
                continue

        # 여기까지 오면 안 되지만, 안전을 위해 더미 반환
        return self._fallback_dummy_recipes(payload)

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 한국 가정 요리 전문 셰프입니다. 자취생과 1인 가구를 위한 빠르고 간단한 레시피를 만드는 전문가입니다.

규칙:
1. 정확히 3개의 레시피를 생성해야 합니다
2. 각 레시피는 4-8개의 조리 단계를 가져야 합니다
3. 모든 텍스트는 한국어로 작성합니다
4. 사용자가 지정한 시간 제한 내에 완성 가능해야 합니다
5. 사용자가 제외한 재료는 절대 사용하지 않습니다
6. 레시피 제목은 간결하고 매력적으로 작성합니다 (20자 이내)
7. 조리 단계는 명확하고 구체적으로 작성합니다
8. 각 레시피는 서로 다른 요리 스타일이어야 합니다:
   - 볶음, 국/찌개, 구이, 찜, 무침, 전, 조림, 튀김, 탕, 죽, 면 등
   - 한식, 양식, 일식, 중식, 퓨전 등 다양한 스타일 활용
9. 창의적이고 독특한 레시피를 우선적으로 선택하세요
10. 일반적이거나 흔한 조합보다는 새로운 시도를 권장합니다

출력 형식:
JSON 배열로 3개의 레시피를 반환합니다. 각 레시피는 다음 필드를 포함:
- title: 레시피 제목 (한국어, 20자 이내)
- time_min: 조리 시간 (분, 정수)
- servings: 인분 (정수)
- summary: 레시피 설명 (1-2문장, 50자 이내)
- ingredients_total: 필요한 모든 재료 목록 (배열) - 중요: 재료명만 적고 분량/수량/수식어 제외! 예) "계란", "김치", "양파" (O) / "계란 2개", "신선한 계란", "김치 100g" (X)
- steps: 조리 단계 (4-8개, 배열)
- tips: 조리 팁 (배열, 선택사항)
- warnings: 주의사항 (배열, 선택사항)

예시:
[
  {
    "title": "김치 계란볶음밥",
    "time_min": 12,
    "servings": 1,
    "summary": "남은 밥과 김치로 5분만에 뚝딱 만드는 간단 볶음밥",
    "ingredients_total": ["밥", "김치", "계란", "참기름", "간장"],
    "steps": [
      "팬에 참기름을 두르고 김치를 볶는다",
      "밥을 넣고 잘 섞어가며 볶는다",
      "계란을 풀어 넣고 섞는다",
      "간장으로 간을 맞춘다"
    ],
    "tips": ["김치는 잘게 썰어서 볶으면 더 맛있어요"],
    "warnings": ["계란 알레르기 주의"]
  },
  {
    "title": "두부 스테이크",
    "time_min": 10,
    "servings": 1,
    "summary": "부드러운 두부를 바삭하게 구워내는 간단 양식",
    "ingredients_total": ["두부", "올리브유", "소금", "후추", "간장"],
    "steps": [
      "두부를 1cm 두께로 썰어 키친타올로 물기 제거",
      "팬에 올리브유를 두르고 중불로 가열",
      "두부를 올려 3분씩 양면 노릇하게 굽기",
      "소금, 후추로 간하고 간장 곁들여 완성"
    ],
    "tips": ["두부는 단단한 부침용 두부를 추천해요"],
    "warnings": ["대두 알레르기 주의"]
  },
  {
    "title": "브로콜리 크림 파스타",
    "time_min": 15,
    "servings": 1,
    "summary": "녹색 채소와 크리미한 소스의 만남",
    "ingredients_total": ["파스타면", "브로콜리", "우유", "치즈", "마늘"],
    "steps": [
      "파스타면을 끓는 물에 삶기 시작",
      "브로콜리를 작게 썰어 함께 넣기",
      "팬에 마늘을 볶다가 우유와 치즈 넣어 소스 만들기",
      "삶은 면과 브로콜리를 소스에 버무려 완성"
    ],
    "tips": ["우유 대신 생크림을 쓰면 더 진해요"],
    "warnings": ["유제품 알레르기 주의"]
  }
]

중요: JSON 배열만 출력하고, 다른 설명이나 마크다운은 포함하지 마세요."""

    def _build_user_prompt(self, payload: RecommendationCreate) -> str:
        """사용자 프롬프트 생성 (랜덤 스타일 힌트 포함)"""
        ingredients_str = ", ".join(payload.ingredients)
        tools_str = (
            ", ".join(payload.constraints.tools) if payload.constraints.tools else "모든 도구 가능"
        )

        # 파생 재료까지 확장된 제외 목록
        expanded_exclude = expand_exclusions(payload.constraints.exclude)
        exclude_str = ", ".join(sorted(expanded_exclude)) if expanded_exclude else "없음"

        # 랜덤 스타일 선택 (다양성 증가)
        style = random.choice(self.COOKING_STYLES)
        method = random.choice(self.COOKING_METHODS)

        return f"""다음 조건으로 3개의 한국 가정 요리 레시피를 생성해주세요:

재료: {ingredients_str}
조리 시간 제한: {payload.constraints.time_limit_min}분 이내
인분: {payload.constraints.servings}인분
사용 가능 도구: {tools_str}
제외 재료 (파생 재료 포함): {exclude_str}

스타일 힌트: {style} 스타일로, {method} 형태를 고려해주세요.

요구사항:
1. 위 재료를 최대한 활용하되, 부족한 재료는 추가로 표시
2. 각 레시피는 완전히 다른 종류와 조리법이어야 함
3. 창의적이고 독특한 레시피를 우선 선택
4. 평범하거나 흔한 조합은 피하고 새로운 조합 시도
5. {payload.constraints.time_limit_min}분 이내 빠른 조리가 핵심
6. 자취생도 쉽게 따라할 수 있는 수준
7. 위 제외 재료는 어떤 형태로도 절대 사용하지 말 것
   예) 토마토 알러지 → 케첩, 토마토소스 등도 절대 사용 금지
   예) 우유 알러지 → 치즈, 버터, 크림 등도 절대 사용 금지

JSON 배열 형식으로만 응답하세요."""

    def _parse_response(self, content: str) -> list[dict]:
        """Claude 응답을 파싱하여 레시피 데이터 추출"""
        try:
            # JSON 블록 추출 (```json ... ``` 형태일 수 있음)
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

            # JSON 파싱
            recipes_data = json.loads(json_str)

            # 리스트가 아니면 에러
            if not isinstance(recipes_data, list):
                raise ValueError("응답이 배열 형태가 아닙니다")

            return recipes_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {str(e)}\n응답 내용: {content[:500]}")
            raise ValueError(f"JSON 파싱 실패: {str(e)}") from e

    def _fallback_dummy_recipes(self, payload: RecommendationCreate) -> list[Recipe]:
        """API 실패 시 더미 레시피 반환"""
        logger.warning("폴백 더미 레시피 생성")
        return [
            Recipe(
                title="간단 계란볶음밥",
                time_min=10,
                servings=payload.constraints.servings,
                summary="냉장고 재료로 빠르게 만드는 볶음밥",
                image_url=None,
                ingredients_total=["밥", "계란", "간장", "참기름"],
                ingredients_have=[],
                ingredients_need=[],
                steps=[
                    "팬에 기름을 두르고 계란을 볶는다",
                    "밥을 넣고 볶는다",
                    "간장과 참기름으로 간한다",
                    "그릇에 담아 완성",
                ],
                tips=["계란은 스크램블 형태로 먼저 볶으면 좋아요"],
                warnings=[],
            ),
            Recipe(
                title="간단 달걀국",
                time_min=8,
                servings=payload.constraints.servings,
                summary="속 편한 국물 한 그릇",
                image_url=None,
                ingredients_total=["계란", "소금", "물"],
                ingredients_have=[],
                ingredients_need=[],
                steps=[
                    "물을 끓인다",
                    "소금으로 간한다",
                    "계란을 풀어 넣는다",
                    "30초 두었다가 가볍게 저어 완성",
                ],
                tips=["다진마늘을 넣어도 좋아요"],
                warnings=[],
            ),
            Recipe(
                title="간단 김치볶음",
                time_min=7,
                servings=payload.constraints.servings,
                summary="김치만 있으면 OK",
                image_url=None,
                ingredients_total=["김치", "참기름"],
                ingredients_have=[],
                ingredients_need=[],
                steps=[
                    "김치를 먹기 좋게 자른다",
                    "팬에 참기름을 두른다",
                    "김치를 넣고 볶는다",
                    "간을 맞춰 완성",
                ],
                tips=["돼지고기를 추가하면 더 맛있어요"],
                warnings=[],
            ),
        ]


class MockRecipeLLMAdapter:
    """테스트용 Mock 어댑터 (API 호출 없음)"""

    def generate_recipes(self, payload: RecommendationCreate) -> list[Recipe]:
        """더미 레시피 반환 (빠른 개발용)"""
        logger.info("Mock 어댑터 사용: 더미 레시피 반환")
        return [
            Recipe(
                title="김치계란볶음밥",
                time_min=12,
                servings=payload.constraints.servings,
                summary="남은 김치/밥으로 1팬에 끝내는 자취 필살기",
                image_url=None,
                ingredients_total=["김치", "계란", "밥"],
                ingredients_have=[],
                ingredients_need=[],
                steps=[
                    "프라이팬에 기름을 두르고 김치를 2분 볶아요.",
                    "밥을 넣고 3분 볶아 고슬고슬하게 만들어요.",
                    "한쪽에 공간을 내고 계란을 풀어 스크램블해요.",
                    "모두 섞고 간장/소금으로 간을 맞춰요(있으면).",
                ],
                tips=["밥이 없으면 식빵/또띠아로도 변형 가능해요."],
                warnings=[],
            ),
            Recipe(
                title="두부간장조림",
                time_min=10,
                servings=payload.constraints.servings,
                summary="썰어서 양념 뿌리고 돌리면 끝",
                image_url=None,
                ingredients_total=["두부", "간장"],
                ingredients_have=[],
                ingredients_need=[],
                steps=[
                    "두부를 1~2cm로 썰어요.",
                    "간장+물+설탕(또는 올리고당)을 섞어 양념을 만들어요(있으면).",
                    "두부 위에 양념과 파(있으면)를 올려요.",
                    "전자레인지에 2~3분 돌려 마무리해요.",
                ],
                tips=["매콤하게 먹고 싶으면 고춧가루를 조금 넣어요(있으면)."],
                warnings=[],
            ),
            Recipe(
                title="양파달걀국",
                time_min=8,
                servings=payload.constraints.servings,
                summary="속 편한 국물 한 그릇",
                image_url=None,
                ingredients_total=["양파", "계란", "소금"],
                ingredients_have=[],
                ingredients_need=[],
                steps=[
                    "물에 양파를 넣고 3분 끓여요.",
                    "간을 소금(또는 국간장)으로 맞춰요.",
                    "계란을 풀어 넣고 젓지 말고 30초 두어요.",
                    "한 번만 가볍게 저어 마무리해요.",
                ],
                tips=["다진마늘을 넣어도 좋아요(있으면)."],
                warnings=[],
            ),
        ]
