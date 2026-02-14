"""
Guest usage service

비로그인 사용자의 일일 사용량 체크 및 증가
"""

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.guest_usage import GuestUsage


class UsageService:
    def __init__(self, db: Session):
        self.db = db

    def get_remaining(self, ip_address: str) -> int:
        """남은 사용 횟수 반환"""
        usage = (
            self.db.query(GuestUsage)
            .filter(
                GuestUsage.ip_address == ip_address,
                GuestUsage.usage_date == date.today(),
            )
            .first()
        )
        if not usage:
            return settings.guest_daily_limit
        return max(0, settings.guest_daily_limit - usage.count)

    def increment(self, ip_address: str) -> int:
        """사용 횟수 증가 후 남은 횟수 반환"""
        usage = (
            self.db.query(GuestUsage)
            .filter(
                GuestUsage.ip_address == ip_address,
                GuestUsage.usage_date == date.today(),
            )
            .first()
        )
        if not usage:
            usage = GuestUsage(
                ip_address=ip_address,
                usage_date=date.today(),
                count=1,
            )
            self.db.add(usage)
        else:
            usage.count += 1
        self.db.commit()
        return max(0, settings.guest_daily_limit - usage.count)

    def check_limit(self, ip_address: str) -> bool:
        """제한 초과 여부 (True = 사용 가능)"""
        return self.get_remaining(ip_address) > 0
