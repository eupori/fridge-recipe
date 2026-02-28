"""
Meal Plan models and schemas

주간 식단 플래너를 위한 모델
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class MealPlan(Base):
    """식단 플래너 DB 모델"""

    __tablename__ = "meal_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    week_start = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    slots = relationship("MealSlot", back_populates="meal_plan", cascade="all, delete-orphan")


class MealSlot(Base):
    """식단 슬롯 DB 모델"""

    __tablename__ = "meal_slots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    meal_plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meal_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week = Column(Integer, nullable=False)  # 0=월 ~ 6=일
    meal_type = Column(String(10), nullable=False)  # breakfast, lunch, dinner
    recommendation_id = Column(String(50), nullable=False)
    recipe_index = Column(Integer, nullable=False)
    recipe_title = Column(String(200), nullable=False)
    recipe_image_url = Column(String(500), nullable=True)

    meal_plan = relationship("MealPlan", back_populates="slots")

    __table_args__ = (
        UniqueConstraint("meal_plan_id", "day_of_week", "meal_type", name="uq_slot_day_meal"),
    )


# Pydantic 스키마
class MealPlanCreate(BaseModel):
    """식단 생성 요청"""

    title: str = Field(..., max_length=100)
    week_start: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class MealSlotCreate(BaseModel):
    """슬롯 추가 요청"""

    day_of_week: int = Field(..., ge=0, le=6)
    meal_type: str = Field(..., pattern=r"^(breakfast|lunch|dinner)$")
    recommendation_id: str
    recipe_index: int = Field(..., ge=0, le=2)
    recipe_title: str = Field(..., max_length=200)
    recipe_image_url: str | None = None


class MealSlotResponse(BaseModel):
    """슬롯 응답"""

    id: str
    day_of_week: int
    meal_type: str
    recommendation_id: str
    recipe_index: int
    recipe_title: str
    recipe_image_url: str | None

    model_config = {"from_attributes": True}


class MealPlanResponse(BaseModel):
    """식단 상세 응답"""

    id: str
    title: str
    week_start: str
    slots: list[MealSlotResponse]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MealPlanListItem(BaseModel):
    """식단 목록 아이템"""

    id: str
    title: str
    week_start: str
    slot_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
