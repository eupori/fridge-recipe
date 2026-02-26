"""레퍼런스 레시피 공개 API — SEO 페이지용"""

import time

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.reference_recipe import ReferenceRecipe
from app.models.reference_recipe_schema import (
    CategoryCount,
    ReferenceRecipeDetail,
    ReferenceRecipeListResponse,
    SitemapEntry,
)

router = APIRouter()

# 인메모리 캐시
_cache: dict[str, tuple[float, object]] = {}


def _get_cached(key: str, ttl: int):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None


def _set_cached(key: str, data: object):
    _cache[key] = (time.time(), data)


@router.get("/categories", response_model=list[CategoryCount])
def get_categories():
    """카테고리별 레시피 개수"""
    cached = _get_cached("categories", 3600)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        rows = (
            db.query(ReferenceRecipe.category, func.count(ReferenceRecipe.id))
            .group_by(ReferenceRecipe.category)
            .order_by(func.count(ReferenceRecipe.id).desc())
            .all()
        )
        result = [CategoryCount(category=cat, count=cnt) for cat, cnt in rows]
        _set_cached("categories", result)
        return result
    finally:
        db.close()


@router.get("/sitemap", response_model=list[SitemapEntry])
def get_sitemap():
    """사이트맵용 전체 ID 목록"""
    cached = _get_cached("sitemap", 3600)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        rows = (
            db.query(ReferenceRecipe)
            .with_entities(
                ReferenceRecipe.id,
                ReferenceRecipe.title,
                ReferenceRecipe.category,
                ReferenceRecipe.crawled_at,
            )
            .order_by(ReferenceRecipe.id)
            .all()
        )
        result = [
            SitemapEntry(id=r.id, title=r.title, category=r.category, crawled_at=r.crawled_at)
            for r in rows
        ]
        _set_cached("sitemap", result)
        return result
    finally:
        db.close()


@router.get("/{recipe_id}", response_model=ReferenceRecipeDetail)
def get_recipe(recipe_id: int):
    """레시피 상세"""
    cache_key = f"recipe:{recipe_id}"
    cached = _get_cached(cache_key, 60)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        recipe = db.query(ReferenceRecipe).filter(ReferenceRecipe.id == recipe_id).first()
        if not recipe:
            raise HTTPException(status_code=404, detail="레시피를 찾을 수 없습니다.")
        result = ReferenceRecipeDetail.model_validate(recipe)
        _set_cached(cache_key, result)
        return result
    finally:
        db.close()


@router.get("", response_model=ReferenceRecipeListResponse)
def get_recipes(
    category: str | None = Query(None, description="카테고리 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    per_page: int = Query(20, ge=1, le=100, description="페이지당 개수"),
):
    """레시피 목록 (페이지네이션)"""
    cache_key = f"list:{category}:{page}:{per_page}"
    cached = _get_cached(cache_key, 60)
    if cached is not None:
        return cached

    db = SessionLocal()
    try:
        query = db.query(ReferenceRecipe)
        if category:
            query = query.filter(ReferenceRecipe.category == category)

        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)

        items = (
            query.order_by(ReferenceRecipe.view_count.desc(), ReferenceRecipe.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        result = ReferenceRecipeListResponse(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
        )
        _set_cached(cache_key, result)
        return result
    finally:
        db.close()
