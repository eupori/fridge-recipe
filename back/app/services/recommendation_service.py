from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.recipe_cache import RecipeCache
from app.models.recommendation import (
    Recipe,
    RecommendationCreate,
    RecommendationRecord,
    RecommendationResponse,
    ShoppingItem,
)
from app.services.coupang_service import CoupangLinkService
from app.services.image_search_service import ImageSearchService
from app.services.llm_adapter import MockRecipeLLMAdapter, RecipeLLMAdapter
from app.services.validation import validate_response
from app.services.youtube_adapter import YouTubeRecipeAdapter

logger = logging.getLogger(__name__)

CACHE_EXPIRY_DAYS = 7


def build_cache_key(payload: RecommendationCreate) -> str:
    """재료 + 제약조건으로 캐시 키 생성 (SHA256)"""
    parts = {
        "ingredients": sorted(i.strip().lower() for i in payload.ingredients),
        "time_limit": payload.constraints.time_limit_min,
        "servings": payload.constraints.servings,
        "exclude": sorted(e.strip().lower() for e in payload.constraints.exclude),
    }
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def lookup_cache(cache_key: str, db: Session) -> RecommendationResponse | None:
    """캐시에서 레시피 조회. 만료되었으면 None 반환."""
    entry = db.query(RecipeCache).filter(RecipeCache.cache_key == cache_key).first()
    if not entry:
        return None

    # 7일 경과 시 만료
    if datetime.now(UTC) - entry.created_at.replace(tzinfo=UTC) > timedelta(days=CACHE_EXPIRY_DAYS):
        db.delete(entry)
        db.commit()
        logger.info(f"캐시 만료 삭제: key={cache_key[:12]}...")
        return None

    entry.hit_count += 1
    db.commit()
    logger.info(f"캐시 히트: key={cache_key[:12]}... (hits={entry.hit_count})")
    return RecommendationResponse.model_validate(entry.recommendation_data)


def save_cache(cache_key: str, response: RecommendationResponse, db: Session) -> None:
    """레시피 결과를 캐시에 저장"""
    entry = RecipeCache(
        cache_key=cache_key,
        recommendation_data=response.model_dump(mode="json"),
        created_at=datetime.now(UTC),
        hit_count=0,
    )
    db.merge(entry)
    db.commit()
    logger.info(f"캐시 저장: key={cache_key[:12]}...")


def normalize_ingredient(ingredient: str) -> str:
    """
    재료명에서 분량, 수량, 수식어를 제거하여 정규화

    예시:
        "신선한 계란 1개" -> "계란"
        "계란 2개" -> "계란"
        "김치 100g" -> "김치"
        "다진 마늘 1큰술" -> "마늘"
    """
    if not ingredient:
        return ""

    text = ingredient.strip()

    # 1. 분량/수량 패턴 제거 (숫자 + 단위)
    # 예: "1개", "2큰술", "100g", "1/2컵" 등
    text = re.sub(
        r"\d+(/\d+)?\s*(개|g|kg|ml|L|큰술|작은술|컵|줌|꼬집|조각|장|쪽|알|마리|근|톨|봉지|팩|통|캔)?",
        "",
        text,
    )

    # 2. 흔한 수식어 제거
    modifiers = [
        "신선한",
        "싱싱한",
        "잘 익은",
        "익은",
        "다진",
        "썬",
        "채썬",
        "굵게 썬",
        "얇게 썬",
        "작게 썬",
        "큼직하게 썬",
        "곱게 간",
        "갈아놓은",
        "삶은",
        "데친",
        "냉동",
        "해동한",
        "적당량",
        "약간",
        "조금",
        "충분한",
        "넉넉한",
    ]
    for mod in modifiers:
        text = text.replace(mod, "")

    # 3. 앞뒤 공백 제거 및 중간 공백 정리
    text = " ".join(text.split()).strip()

    return text


def deduplicate_shopping_list(ingredients: set[str]) -> list[str]:
    """
    장보기 리스트에서 중복 재료 제거 (정규화 후 비교)

    Args:
        ingredients: 필요한 재료 집합

    Returns:
        중복 제거된 재료 리스트 (정렬됨)
    """
    # 정규화된 재료명 -> 원본 재료명 매핑 (첫 번째 것 유지)
    normalized_map: dict[str, str] = {}

    for ing in ingredients:
        normalized = normalize_ingredient(ing)
        if normalized and normalized not in normalized_map:
            # 정규화된 이름을 저장 (분량 없는 깔끔한 이름)
            normalized_map[normalized] = normalized

    return sorted(normalized_map.values())


def split_have_need(
    user_ingredients: list[str], recipe_ingredients: list[str]
) -> tuple[list[str], list[str]]:
    """
    사용자 재료와 레시피 재료를 비교하여 보유/필요 재료 분리

    Args:
        user_ingredients: 사용자가 보유한 재료 목록
        recipe_ingredients: 레시피에 필요한 재료 목록

    Returns:
        (보유 재료, 필요 재료) 튜플
    """
    # 정규화: 공백 제거 + 소문자 변환
    user_set = {i.strip().lower() for i in user_ingredients if i and i.strip()}
    recipe_set = {i.strip().lower() for i in recipe_ingredients if i and i.strip()}

    # 원본 대소문자 유지를 위해 매핑 생성
    recipe_map = {i.strip().lower(): i.strip() for i in recipe_ingredients if i and i.strip()}

    # 보유 재료: 사용자가 가진 것 중 레시피에 필요한 것
    have_keys = user_set & recipe_set
    have = sorted([recipe_map[k] for k in have_keys])

    # 필요 재료: 레시피에 필요한 것 중 사용자가 없는 것
    need_keys = recipe_set - user_set
    need = sorted([recipe_map[k] for k in need_keys])

    return have, need


async def create_recommendation(
    payload: RecommendationCreate, db: Session
) -> RecommendationResponse:
    """
    사용자 재료로 레시피 추천 생성 (LLM 통합 + 이미지 검색)

    Args:
        payload: 사용자 입력 (재료, 제약사항)

    Returns:
        RecommendationResponse: 3개 레시피 + 장보기 리스트

    Raises:
        ValueError: 검증 실패 시
    """
    logger.info(f"레시피 생성 요청: 재료={payload.ingredients}, 제약={payload.constraints}")
    start_time = time.monotonic()

    # 0. 캐시 조회
    cache_key = build_cache_key(payload)
    cached = lookup_cache(cache_key, db)
    if cached is not None:
        # 새 ID로 클론하여 반환
        new_id = f"rec_{uuid4().hex[:10]}"
        cloned = cached.model_copy(update={"id": new_id, "created_at": datetime.now(UTC)})
        record = RecommendationRecord(
            id=new_id, created_at=cloned.created_at, data=cloned.model_dump(mode="json")
        )
        db.add(record)
        db.commit()
        elapsed = time.monotonic() - start_time
        logger.info(
            f"💰 Cost: LLM=$0.000, Image=$0.000, Total=$0.000 "
            f"(cache hit, {elapsed:.1f}s)"
        )
        logger.info(f"캐시에서 레시피 반환: ID={new_id} (캐시키={cache_key[:12]}...)")
        return cloned

    # 1. 레시피 생성 어댑터 선택 (youtube → anthropic → mock)
    provider = settings.recipe_provider
    logger.info(f"레시피 Provider: {provider}")

    if provider == "mock":
        recipes_raw = MockRecipeLLMAdapter().generate_recipes(payload)
    elif provider == "youtube":
        try:
            recipes_raw = await YouTubeRecipeAdapter().generate_recipes(payload)
        except Exception as e:
            logger.warning(f"YouTube+Haiku 실패, Sonnet 폴백: {e}")
            try:
                recipes_raw = RecipeLLMAdapter().generate_recipes(payload)
            except Exception as e2:
                logger.error(f"Sonnet 폴백도 실패, 더미 레시피 반환: {e2}")
                recipes_raw = MockRecipeLLMAdapter().generate_recipes(payload)
    else:
        # anthropic (기존 동작)
        recipes_raw = RecipeLLMAdapter().generate_recipes(payload)

    llm_elapsed = time.monotonic() - start_time
    logger.info(f"레시피 생성 완료: {llm_elapsed:.1f}초 (provider={provider})")

    # 3. 이미지 검색 서비스 초기화
    image_service = ImageSearchService()

    # 4. 이미지 병렬 검색 (API Gateway 30초 제한 대비 동적 타임아웃)
    image_timeout = max(28 - llm_elapsed, 5)
    logger.info(f"이미지 검색 시작: {len(recipes_raw)}개 레시피 (타임아웃: {image_timeout:.1f}초)")
    image_tasks = [image_service.get_image(recipe.title) for recipe in recipes_raw]
    try:
        image_results = await asyncio.wait_for(
            asyncio.gather(*image_tasks, return_exceptions=True),
            timeout=image_timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(f"이미지 생성 타임아웃 ({image_timeout:.1f}초 초과), 이미지 없이 진행")
        image_results = [None] * len(recipes_raw)

    # 5. ingredients_have, ingredients_need 분리 + 이미지 URL 추가
    final_recipes = []
    for recipe, img_result in zip(recipes_raw, image_results, strict=False):
        have, need = split_have_need(payload.ingredients, recipe.ingredients_total)

        # 이미지 검색 실패 처리
        if isinstance(img_result, Exception):
            logger.error(f"이미지 검색 실패 ({recipe.title}): {img_result}")
            img_url = None
        else:
            img_url = img_result

        # Recipe 객체 재생성 (have/need 필드 + 이미지 URL 업데이트)
        final_recipe = Recipe(
            title=recipe.title,
            time_min=recipe.time_min,
            servings=recipe.servings,
            summary=recipe.summary,
            image_url=img_url,  # Google/Unsplash/Mock 이미지
            ingredients_total=recipe.ingredients_total,
            ingredients_have=have,
            ingredients_need=need,
            steps=recipe.steps,
            tips=recipe.tips or [],
            warnings=recipe.warnings or [],
        )
        final_recipes.append(final_recipe)

    logger.info(f"이미지 검색 완료: {sum(1 for r in final_recipes if r.image_url)}개 성공")

    # 4. 장보기 리스트 생성 (모든 레시피의 필요 재료 중복 제거 + 정규화)
    all_need: set[str] = set()
    for r in final_recipes:
        all_need |= {x for x in r.ingredients_need if x}

    # 정규화하여 중복 제거 (예: "계란 1개", "계란 2개" → "계란")
    deduplicated = deduplicate_shopping_list(all_need)

    # 쿠팡 파트너스 링크 생성
    coupang = CoupangLinkService()
    shopping_list = [
        ShoppingItem(item=i, purchase_url=coupang.generate_search_url(i))
        for i in deduplicated
    ]

    # 5. 응답 객체 생성
    rec_id = f"rec_{uuid4().hex[:10]}"
    response = RecommendationResponse(
        id=rec_id, created_at=datetime.now(UTC), recipes=final_recipes, shopping_list=shopping_list
    )

    # 6. 검증 (LLM 출력이 규칙 만족하는지 확인)
    validate_response(response, payload)

    # 7. DB 저장 및 반환
    record = RecommendationRecord(
        id=rec_id, created_at=response.created_at, data=response.model_dump(mode="json")
    )
    db.add(record)
    db.commit()

    # 8. 캐시에 저장 (다음 동일 요청 시 LLM/이미지 비용 절약)
    try:
        save_cache(cache_key, response, db)
    except Exception as e:
        logger.warning(f"캐시 저장 실패 (무시): {e}")

    # 9. 비용 추정 로깅
    llm_costs = {"anthropic": 0.015, "youtube": 0.005, "mock": 0.0}
    image_provider = settings.image_search_provider.lower()
    img_costs_per = {"gemini": 0.039, "google": 0.005, "unsplash": 0.0, "mock": 0.0}
    llm_cost = llm_costs.get(provider, 0.015)
    num_images = sum(1 for r in final_recipes if r.image_url)
    img_cost = img_costs_per.get(image_provider, 0.0) * num_images
    total_cost = llm_cost + img_cost
    elapsed = time.monotonic() - start_time
    logger.info(
        f"💰 Cost: LLM=${llm_cost:.3f}, Image=${img_cost:.3f}, Total=${total_cost:.3f} "
        f"(provider={provider}, image={image_provider}, {elapsed:.1f}s)"
    )

    logger.info(f"레시피 생성 완료: ID={rec_id}")
    return response


def get_recommendation(recommendation_id: str, db: Session) -> RecommendationResponse | None:
    """
    DB에서 추천 결과 조회

    Args:
        recommendation_id: 추천 ID (rec_로 시작)
        db: DB 세션

    Returns:
        RecommendationResponse 또는 None (없을 경우)
    """
    record = (
        db.query(RecommendationRecord).filter(RecommendationRecord.id == recommendation_id).first()
    )

    if not record:
        return None

    return RecommendationResponse.model_validate(record.data)
