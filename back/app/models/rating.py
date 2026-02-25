"""
Rating model and schemas

사용자가 레시피에 부여한 별점 평가
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# SQLAlchemy ORM 모델
class RecipeRating(Base):
    """레시피 별점 DB 모델"""

    __tablename__ = "recipe_ratings"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_id", "recipe_index", "user_id", name="uq_rating_user"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    recommendation_id = Column(String(50), nullable=False, index=True)
    recipe_index = Column(Integer, nullable=False)  # 0, 1, 2
    rating = Column(Integer, nullable=False)  # 1-5
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("User", backref="ratings")


# Pydantic 스키마
class RatingCreate(BaseModel):
    """별점 평가 요청"""

    recommendation_id: str
    recipe_index: int = Field(..., ge=0, le=2)
    rating: int = Field(..., ge=1, le=5)


class RatingResponse(BaseModel):
    """별점 평가 응답"""

    id: str
    recommendation_id: str
    recipe_index: int
    rating: int
    created_at: datetime

    model_config = {"from_attributes": True}


class RecipeRatingStats(BaseModel):
    """개별 레시피 평가 통계"""

    recipe_index: int
    average_rating: float
    count: int
    my_rating: int | None = None


class RecommendationRatingStats(BaseModel):
    """추천의 모든 레시피 평가 통계"""

    recommendation_id: str
    recipes: list[RecipeRatingStats]
