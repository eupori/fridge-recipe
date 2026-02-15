"""
정밀 모드용 YouTube 인기 영상 검색 서비스

레시피 제목으로 YouTube에서 인기 요리 영상을 검색하여
ReferenceVideo 모델로 반환합니다.

공유 YouTubeAPIClient를 사용하여 쿼터를 추적합니다.
"""

from __future__ import annotations

import logging
import math

from app.models.recommendation import ReferenceVideo
from app.services.youtube_client import (
    RECIPE_KEYWORDS,
    YouTubeAPIClient,
)

logger = logging.getLogger(__name__)


class YouTubeVideoService:
    """정밀 모드용 YouTube 인기 영상 검색"""

    def __init__(self):
        self.yt_client = YouTubeAPIClient()

    async def find_reference_video(self, recipe_title: str) -> ReferenceVideo | None:
        """
        레시피 제목으로 YouTube 인기 영상 1개 검색

        Args:
            recipe_title: 레시피 제목 (한국어)

        Returns:
            ReferenceVideo 또는 None (검색 실패/쿼터 소진 시)
        """
        try:
            # 쿼터 확인 (search 100 + details 1 = 101 units 필요)
            if not self.yt_client.quota.is_available:
                logger.info(f"YouTube 쿼터 소진, 영상 검색 스킵: '{recipe_title}'")
                return None

            # 1. YouTube 검색 (max_results=3으로 줄여 쿼터 절약)
            video_ids = await self.yt_client.search(
                f"{recipe_title} 레시피", max_results=3
            )
            if not video_ids:
                logger.warning(f"YouTube 검색 결과 없음: '{recipe_title}'")
                return None

            # 2. 상세 정보 조회
            videos = await self.yt_client.get_video_details(video_ids)
            if not videos:
                return None

            # 3. 랭킹 후 최상위 1개 반환
            ranked = sorted(videos, key=lambda v: self._score(v, recipe_title), reverse=True)
            best = ranked[0]
            thumbnail_url = f"https://img.youtube.com/vi/{best.video_id}/hqdefault.jpg"

            ref_video = ReferenceVideo(
                video_id=best.video_id,
                title=best.title,
                channel=best.channel_title,
                view_count=best.view_count,
                thumbnail_url=thumbnail_url,
            )
            logger.info(
                f"YouTube 참고 영상 선택: '{recipe_title}' → '{best.title}' "
                f"(조회수: {best.view_count:,})"
            )
            return ref_video

        except Exception as e:
            logger.error(f"YouTube 영상 검색 실패 ({recipe_title}): {e}")
            return None

    @staticmethod
    def _score(video, recipe_title: str) -> float:
        """관련성 + 인기도 점수 계산"""
        title_lower = video.title.lower()
        keyword_score = sum(1 for kw in RECIPE_KEYWORDS if kw in title_lower)
        title_match = 5 if recipe_title in video.title else 0
        view_score = math.log10(max(video.view_count, 1))
        return keyword_score * 3 + title_match + view_score
