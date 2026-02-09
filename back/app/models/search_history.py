"""
Search history model and schemas

사용자의 레시피 검색 기록 저장 (최근 7일 보관)
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# SQLAlchemy ORM 모델
class SearchHistory(Base):
    """검색 기록 DB 모델"""
    __tablename__ = "search_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    recommendation_id = Column(String(50), nullable=False)

    # 검색 조건 (다시 검색 기능용)
    ingredients = Column(JSON, nullable=False)  # ["계란", "김치", "양파"]
    time_limit_min = Column(Integer, nullable=False)
    servings = Column(Integer, nullable=False)

    # 결과 캐시 (미리보기용)
    recipe_titles = Column(JSON, nullable=False)  # ["김치볶음밥", "계란말이", "스크램블"]
    recipe_images = Column(JSON, nullable=True)  # [url1, url2, url3]

    searched_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = relationship("User", backref="search_histories")


# Pydantic 스키마
class SearchHistoryCreate(BaseModel):
    """검색 기록 생성 (내부 사용)"""
    recommendation_id: str
    ingredients: list[str]
    time_limit_min: int
    servings: int
    recipe_titles: list[str]
    recipe_images: list[str | None]


class SearchHistoryResponse(BaseModel):
    """검색 기록 응답"""
    id: str
    recommendation_id: str
    ingredients: list[str]
    time_limit_min: int
    servings: int
    recipe_titles: list[str]
    recipe_images: list[str | None]
    searched_at: datetime

    model_config = {"from_attributes": True}
