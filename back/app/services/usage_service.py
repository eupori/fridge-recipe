"""
Usage service

사용자(로그인/비로그인)의 일일 사용량 체크 및 증가
- 비로그인: IP 기반, guest_daily_limit 적용
- 로그인: user:{id} 키 기반, user_daily_limit 적용
"""

from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.guest_usage import GuestUsage


class UsageService:
    def __init__(self, db: Session):
        self.db = db

    def get_remaining(self, key: str, limit: int | None = None) -> int:
        """남은 사용 횟수 반환"""
        daily_limit = limit if limit is not None else settings.guest_daily_limit
        usage = (
            self.db.query(GuestUsage)
            .filter(
                GuestUsage.ip_address == key,
                GuestUsage.usage_date == date.today(),
            )
            .first()
        )
        if not usage:
            return daily_limit
        return max(0, daily_limit - usage.count)

    def increment(self, key: str, limit: int | None = None) -> int:
        """사용 횟수 증가 후 남은 횟수 반환 (UPSERT로 레이스 컨디션 방지)"""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        try:
            # PostgreSQL UPSERT
            stmt = pg_insert(GuestUsage).values(
                ip_address=key,
                usage_date=date.today(),
                count=1,
            ).on_conflict_do_update(
                constraint="uq_guest_usage_ip_date",
                set_={"count": GuestUsage.count + 1},
            )
            self.db.execute(stmt)
            self.db.commit()
        except Exception:
            # SQLite 폴백 (개발환경)
            self.db.rollback()
            usage = (
                self.db.query(GuestUsage)
                .filter(
                    GuestUsage.ip_address == key,
                    GuestUsage.usage_date == date.today(),
                )
                .first()
            )
            if not usage:
                usage = GuestUsage(
                    ip_address=key,
                    usage_date=date.today(),
                    count=1,
                )
                self.db.add(usage)
            else:
                usage.count += 1
            self.db.commit()

        return self.get_remaining(key, limit)

    def check_limit(self, key: str, limit: int | None = None) -> bool:
        """제한 초과 여부 (True = 사용 가능)"""
        return self.get_remaining(key, limit) > 0
