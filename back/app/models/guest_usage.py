"""
Guest usage tracking model

비로그인 사용자의 일일 사용량을 IP 기반으로 추적
"""

from datetime import date

from sqlalchemy import Column, Date, Integer, String, UniqueConstraint

from app.core.database import Base


class GuestUsage(Base):
    """비로그인 사용자 일일 사용량 DB 모델"""

    __tablename__ = "guest_usage"
    __table_args__ = (
        UniqueConstraint("ip_address", "usage_date", name="uq_guest_usage_ip_date"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(String(45), nullable=False, index=True)
    usage_date = Column(Date, nullable=False, default=date.today, index=True)
    count = Column(Integer, default=0, nullable=False)
