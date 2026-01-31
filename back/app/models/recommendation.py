from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class Constraints(BaseModel):
    time_limit_min: int = Field(default=15, ge=5, le=60)
    servings: int = Field(default=1, ge=1, le=6)
    tools: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class RecommendationCreate(BaseModel):
    ingredients: list[str] = Field(min_length=1)
    constraints: Constraints = Field(default_factory=Constraints)


class Recipe(BaseModel):
    title: str
    time_min: int
    servings: int
    summary: str
    image_url: str | None = None

    # 이 레시피에 필요한 '총 재료'(보유/추가 합친 기준 목록)
    ingredients_total: list[str]

    # 사용자가 입력한 재료(=보유)와 비교해 분리한 결과
    ingredients_have: list[str]
    ingredients_need: list[str]

    steps: list[str]
    tips: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ShoppingItem(BaseModel):
    item: str
    qty: float | int | None = None
    unit: str | None = None
    category: str | None = None


class RecommendationResponse(BaseModel):
    id: str
    created_at: datetime
    recipes: list[Recipe]
    shopping_list: list[ShoppingItem]
