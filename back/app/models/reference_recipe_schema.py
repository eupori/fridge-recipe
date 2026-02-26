"""레퍼런스 레시피 API 응답 스키마"""

from datetime import datetime

from pydantic import BaseModel


class ReferenceRecipeListItem(BaseModel):
    """목록용 레시피 요약"""

    id: int
    title: str
    category: str
    key_ingredients: list[str]
    time_min: int | None = None
    servings: int | None = None
    view_count: int = 0
    source: str

    class Config:
        from_attributes = True


class ReferenceRecipeDetail(BaseModel):
    """상세 레시피"""

    id: int
    title: str
    category: str
    key_ingredients: list[str]
    all_ingredients: list[str]
    steps: list[str]
    technique: str | None = None
    time_min: int | None = None
    servings: int | None = None
    view_count: int = 0
    rating: int | None = None
    source: str
    source_url: str
    crawled_at: datetime | None = None

    class Config:
        from_attributes = True


class ReferenceRecipeListResponse(BaseModel):
    """페이지네이션된 목록 응답"""

    items: list[ReferenceRecipeListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class CategoryCount(BaseModel):
    """카테고리별 레시피 개수"""

    category: str
    count: int


class SitemapEntry(BaseModel):
    """사이트맵용 엔트리"""

    id: int
    title: str
    category: str
    crawled_at: datetime | None = None

    class Config:
        from_attributes = True
