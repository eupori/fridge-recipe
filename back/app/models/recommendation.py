from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import JSON, Column, DateTime, String

from app.core.database import Base


class RecommendationRecord(Base):
    """추천 결과 DB 모델 (JSON 저장 방식)"""

    __tablename__ = "recommendations"

    id = Column(String(50), primary_key=True)  # "rec_a1b2c3d4e5"
    created_at = Column(DateTime, nullable=False)
    data = Column(JSON, nullable=False)  # RecommendationResponse 전체를 JSON으로


class Constraints(BaseModel):
    """조리 제약 조건"""

    time_limit_min: int = Field(default=15, ge=5, le=60, description="최대 조리 시간 (분)")
    servings: int = Field(default=1, ge=1, le=6, description="인분 수")
    tools: list[str] = Field(default_factory=list, description="사용 가능한 조리 도구 목록")
    exclude: list[str] = Field(default_factory=list, description="제외할 재료 목록 (알레르기 등)")


class RecommendationCreate(BaseModel):
    """레시피 추천 생성 요청"""

    ingredients: list[str] = Field(
        min_length=1, description="냉장고에 있는 재료 목록 (최소 1개 이상)"
    )
    constraints: Constraints = Field(default_factory=Constraints, description="조리 제약 조건")


class Recipe(BaseModel):
    """레시피 상세 정보"""

    title: str = Field(description="레시피 제목")
    time_min: int = Field(description="조리 시간 (분)")
    servings: int = Field(description="인분 수")
    summary: str = Field(description="레시피 요약 설명")
    image_url: str | None = Field(default=None, description="레시피 이미지 URL")

    # 이 레시피에 필요한 '총 재료'(보유/추가 합친 기준 목록)
    ingredients_total: list[str] = Field(description="레시피에 필요한 전체 재료 목록")

    # 사용자가 입력한 재료(=보유)와 비교해 분리한 결과
    ingredients_have: list[str] = Field(description="사용자가 이미 보유한 재료")
    ingredients_need: list[str] = Field(description="구매가 필요한 재료")

    steps: list[str] = Field(description="조리 순서 (4-8단계)")
    tips: list[str] = Field(default_factory=list, description="조리 팁")
    warnings: list[str] = Field(default_factory=list, description="주의사항")


class ShoppingItem(BaseModel):
    """장보기 아이템"""

    item: str = Field(description="구매할 재료명")
    qty: float | int | None = Field(default=None, description="수량")
    unit: str | None = Field(default=None, description="단위 (예: 개, 봉, ml, g)")
    category: str | None = Field(default=None, description="카테고리 (예: 채소, 육류, 조미료)")


class RecommendationResponse(BaseModel):
    """레시피 추천 응답"""

    id: str = Field(description="추천 ID (rec_로 시작하는 고유 식별자)")
    created_at: datetime = Field(description="생성 일시")
    recipes: list[Recipe] = Field(
        description="추천된 레시피 목록 (정확히 3개)", min_length=3, max_length=3
    )
    shopping_list: list[ShoppingItem] = Field(
        description="통합 장보기 리스트 (모든 레시피의 구매 필요 재료를 중복 제거하여 집계)"
    )
