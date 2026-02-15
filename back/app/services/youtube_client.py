"""
공유 YouTube API 클라이언트 + 쿼터 Circuit Breaker

YouTube Data API v3의 일일 쿼터(10,000 units)를 추적하고,
소진 시 자동으로 API 호출을 차단합니다.

쿼터 비용:
- search.list: 100 units
- videos.list: 1 unit

youtube_adapter.py, youtube_video_service.py 모두 이 클라이언트를 사용합니다.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone, timedelta

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# 레시피 관련 키워드 (랭킹용, 양쪽 서비스에서 공유)
RECIPE_KEYWORDS = ["레시피", "요리", "만들기", "만드는", "간단", "자취", "초간단", "백종원"]

# KST timezone
KST = timezone(timedelta(hours=9))

# 쿼터 비용 상수
SEARCH_COST = 100  # search.list
DETAILS_COST = 1   # videos.list


@dataclass
class VideoInfo:
    """YouTube 영상 메타데이터"""

    video_id: str
    title: str
    description: str
    view_count: int
    channel_title: str


class YouTubeQuotaTracker:
    """
    인메모리 YouTube API 쿼터 추적기 (싱글톤)

    - 일일 10,000 units 추적 (KST 기준 자정 리셋)
    - 80% 도달 시 경고 로그
    - 100% 도달 또는 403 연속 시 circuit open
    - 영상 검색 결과 인메모리 캐시 (동일 쿼리 재검색 방지)
    """

    DAILY_LIMIT = 10_000
    WARN_THRESHOLD = 0.8   # 80%에서 경고
    COOLDOWN_SECONDS = 300  # 403 후 5분 쿨다운

    def __init__(self):
        self._units_used: int = 0
        self._date: date = datetime.now(KST).date()
        self._circuit_open: bool = False
        self._circuit_open_until: float = 0
        self._consecutive_403: int = 0
        # 영상 검색 결과 캐시: query → list[video_id]
        self._search_cache: dict[str, list[str]] = {}
        # 영상 상세 정보 캐시: video_id → VideoInfo
        self._details_cache: dict[str, dict] = {}

    def _maybe_reset(self):
        """KST 자정 기준으로 일일 카운터 리셋"""
        today = datetime.now(KST).date()
        if today != self._date:
            logger.info(
                f"YouTube 쿼터 일일 리셋: {self._units_used} units 사용됨 "
                f"({self._date} → {today})"
            )
            self._units_used = 0
            self._date = today
            self._circuit_open = False
            self._circuit_open_until = 0
            self._consecutive_403 = 0
            self._search_cache.clear()
            self._details_cache.clear()

    @property
    def is_available(self) -> bool:
        """API 호출 가능 여부"""
        self._maybe_reset()

        # 쿨다운 중인지 확인
        if self._circuit_open:
            if time.monotonic() < self._circuit_open_until:
                return False
            # 쿨다운 해제
            logger.info("YouTube 쿼터 circuit breaker 쿨다운 해제")
            self._circuit_open = False
            self._consecutive_403 = 0

        return self._units_used < self.DAILY_LIMIT

    def consume(self, units: int) -> bool:
        """
        쿼터 소비 시도. 가용하면 True, 불가하면 False.

        Args:
            units: 소비할 쿼터 units

        Returns:
            True if consumed, False if quota exhausted
        """
        self._maybe_reset()

        if not self.is_available:
            logger.warning(
                f"YouTube 쿼터 차단: {self._units_used}/{self.DAILY_LIMIT} units "
                f"(circuit_open={self._circuit_open})"
            )
            return False

        self._units_used += units

        # 80% 경고
        usage_pct = self._units_used / self.DAILY_LIMIT
        if usage_pct >= self.WARN_THRESHOLD and (self._units_used - units) / self.DAILY_LIMIT < self.WARN_THRESHOLD:
            logger.warning(
                f"⚠️ YouTube 쿼터 {usage_pct:.0%} 사용: "
                f"{self._units_used}/{self.DAILY_LIMIT} units"
            )

        # 100% 도달
        if self._units_used >= self.DAILY_LIMIT:
            logger.error(
                f"🚫 YouTube 쿼터 소진: {self._units_used}/{self.DAILY_LIMIT} units. "
                f"내일 자정(KST)까지 YouTube API 비활성화."
            )
            self._circuit_open = True

        return True

    def report_403(self):
        """403 에러 보고 → circuit open (쿨다운)"""
        self._consecutive_403 += 1
        if self._consecutive_403 >= 2:
            self._circuit_open = True
            self._circuit_open_until = time.monotonic() + self.COOLDOWN_SECONDS
            logger.error(
                f"🚫 YouTube API 403 연속 {self._consecutive_403}회 → "
                f"circuit open ({self.COOLDOWN_SECONDS}초 쿨다운)"
            )

    def report_success(self):
        """성공 호출 보고 → 403 카운터 리셋"""
        self._consecutive_403 = 0

    @property
    def remaining_units(self) -> int:
        self._maybe_reset()
        return max(0, self.DAILY_LIMIT - self._units_used)

    @property
    def usage_stats(self) -> dict:
        self._maybe_reset()
        return {
            "units_used": self._units_used,
            "daily_limit": self.DAILY_LIMIT,
            "remaining": self.remaining_units,
            "usage_pct": round(self._units_used / self.DAILY_LIMIT * 100, 1),
            "circuit_open": self._circuit_open,
            "search_cache_size": len(self._search_cache),
            "details_cache_size": len(self._details_cache),
        }

    def get_cached_search(self, query: str) -> list[str] | None:
        return self._search_cache.get(query)

    def cache_search(self, query: str, video_ids: list[str]):
        self._search_cache[query] = video_ids

    def get_cached_details(self, video_id: str) -> dict | None:
        return self._details_cache.get(video_id)

    def cache_details(self, video_id: str, info: dict):
        self._details_cache[video_id] = info


# 모듈 레벨 싱글톤
_quota_tracker = YouTubeQuotaTracker()


def get_quota_tracker() -> YouTubeQuotaTracker:
    """쿼터 트래커 싱글톤 반환"""
    return _quota_tracker


class YouTubeAPIClient:
    """
    공유 YouTube API 클라이언트

    - 쿼터 트래커와 연동하여 자동 차단
    - 검색 결과/상세 정보 인메모리 캐시
    - httpx.AsyncClient 재사용
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.youtube_api_key
        if not self.api_key:
            raise ValueError("YOUTUBE_API_KEY가 설정되지 않았습니다")
        self.quota = _quota_tracker

    async def search(
        self,
        query: str,
        max_results: int = 5,
        client: httpx.AsyncClient | None = None,
    ) -> list[str]:
        """
        YouTube 검색 (100 units)

        Args:
            query: 검색 쿼리
            max_results: 최대 결과 수
            client: 재사용할 httpx 클라이언트 (없으면 새로 생성)

        Returns:
            video ID 리스트 (쿼터 소진 시 빈 리스트)
        """
        # 캐시 확인
        cached = self.quota.get_cached_search(query)
        if cached is not None:
            logger.debug(f"YouTube 검색 캐시 히트: '{query}' ({len(cached)}개)")
            return cached

        # 쿼터 확인
        if not self.quota.consume(SEARCH_COST):
            return []

        async def _do_search(c: httpx.AsyncClient) -> list[str]:
            resp = await c.get(
                YOUTUBE_SEARCH_URL,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": max_results,
                    "relevanceLanguage": "ko",
                    "regionCode": "KR",
                    "order": "relevance",
                    "key": self.api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            video_ids = []
            for item in data.get("items", []):
                vid = item["id"].get("videoId")
                if vid:
                    video_ids.append(vid)
            return video_ids

        try:
            if client:
                result = await _do_search(client)
            else:
                async with httpx.AsyncClient(timeout=20) as c:
                    result = await _do_search(c)

            self.quota.report_success()
            self.quota.cache_search(query, result)
            logger.info(f"YouTube 검색 완료: '{query}' → {len(result)}개")
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                self.quota.report_403()
                logger.error("YouTube API 할당량 초과 또는 API 키 오류 (403)")
            else:
                logger.error(f"YouTube 검색 HTTP 에러: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"YouTube 검색 실패: [{type(e).__name__}] {e}")
            return []

    async def get_video_details(
        self,
        video_ids: list[str],
        client: httpx.AsyncClient | None = None,
    ) -> list[VideoInfo]:
        """
        영상 상세 정보 조회 (1 unit)

        Args:
            video_ids: 조회할 video ID 리스트
            client: 재사용할 httpx 클라이언트

        Returns:
            VideoInfo 리스트 (쿼터 소진 시 빈 리스트)
        """
        if not video_ids:
            return []

        # 캐시에서 먼저 조회
        cached_videos: list[VideoInfo] = []
        uncached_ids: list[str] = []

        for vid in video_ids:
            cached = self.quota.get_cached_details(vid)
            if cached:
                cached_videos.append(VideoInfo(**cached))
            else:
                uncached_ids.append(vid)

        # 모두 캐시에 있으면 API 호출 불필요
        if not uncached_ids:
            logger.debug(f"YouTube 상세 정보 캐시 히트: {len(cached_videos)}개")
            return cached_videos

        # 쿼터 확인
        if not self.quota.consume(DETAILS_COST):
            return cached_videos  # 캐시에 있는 것만 반환

        ids_str = ",".join(uncached_ids[:15])

        async def _do_details(c: httpx.AsyncClient) -> list[VideoInfo]:
            resp = await c.get(
                YOUTUBE_VIDEOS_URL,
                params={
                    "part": "snippet,statistics",
                    "id": ids_str,
                    "key": self.api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            videos = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})

                try:
                    view_count = int(stats.get("viewCount", 0))
                except (ValueError, TypeError):
                    view_count = 0

                info = VideoInfo(
                    video_id=item["id"],
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    view_count=view_count,
                    channel_title=snippet.get("channelTitle", ""),
                )
                videos.append(info)

                # 캐시에 저장
                self.quota.cache_details(item["id"], {
                    "video_id": info.video_id,
                    "title": info.title,
                    "description": info.description,
                    "view_count": info.view_count,
                    "channel_title": info.channel_title,
                })

            return videos

        try:
            if client:
                fetched = await _do_details(client)
            else:
                async with httpx.AsyncClient(timeout=20) as c:
                    fetched = await _do_details(c)

            self.quota.report_success()
            all_videos = cached_videos + fetched
            logger.info(f"YouTube 상세 정보 조회 완료: {len(all_videos)}개 (캐시: {len(cached_videos)}, API: {len(fetched)})")
            return all_videos

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                self.quota.report_403()
            logger.error(f"YouTube 상세 정보 조회 실패: [{type(e).__name__}] {e}")
            return cached_videos
        except Exception as e:
            logger.error(f"YouTube 상세 정보 조회 실패: [{type(e).__name__}] {e}")
            return cached_videos
