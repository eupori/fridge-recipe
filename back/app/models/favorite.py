"""
Favorite model and schemas

사용자가 즐겨찾기한 레시피 저장
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# SQLAlchemy ORM 모델
class Favorite(Base):
    """즐겨찾기 DB 모델"""
    __tablename__ = "favorites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    recommendation_id = Column(String(50), nullable=False)
    recipe_index = Column(Integer, nullable=False)  # 0, 1, 2
    recipe_title = Column(String(200), nullable=False)  # 캐시용
    recipe_image_url = Column(String(500), nullable=True)  # 캐시용
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="favorites")


# Pydantic 스키마
class FavoriteCreate(BaseModel):
    """즐겨찾기 추가 요청"""
    recommendation_id: str
    recipe_index: int  # 0, 1, 2
    recipe_title: str
    recipe_image_url: str | None = None


class FavoriteResponse(BaseModel):
    """즐겨찾기 응답"""
    id: str
    recommendation_id: str
    recipe_index: int
    recipe_title: str
    recipe_image_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FavoriteCheck(BaseModel):
    """즐겨찾기 여부 확인 응답"""
    is_favorite: bool
    favorite_id: str | None = None


class RecipeLikeCount(BaseModel):
    """개별 레시피 좋아요 수"""
    recipe_index: int
    like_count: int


class RecommendationLikeStats(BaseModel):
    """추천의 모든 레시피 좋아요 통계"""
    recommendation_id: str
    recipes: list[RecipeLikeCount]
