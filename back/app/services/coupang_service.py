"""쿠팡 파트너스 링크 생성 서비스"""

from __future__ import annotations

import logging
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)


class CoupangLinkService:
    """쿠팡 파트너스 검색 링크 생성"""

    BASE_URL = "https://www.coupang.com/np/search"

    def __init__(self):
        self.tracking_id = settings.coupang_partners_tracking_id
        self.sub_id = settings.coupang_partners_sub_id

    @property
    def enabled(self) -> bool:
        return bool(self.tracking_id)

    def generate_search_url(self, ingredient: str) -> str | None:
        """
        재료명으로 쿠팡 검색 URL 생성

        Args:
            ingredient: 재료명 (예: "김치", "계란")

        Returns:
            쿠팡 파트너스 검색 URL 또는 None (트래킹 ID 미설정 시)
        """
        if not self.tracking_id:
            return None

        params = f"component=&q={quote(ingredient)}&channel=user&tracker={self.tracking_id}"
        if self.sub_id:
            params += f"&subId={self.sub_id}"

        return f"{self.BASE_URL}?{params}"
