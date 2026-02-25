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
from app.data.ingredient_synonyms import canonicalize_ingredient
from app.models.recipe_cache import RecipeCache
from app.models.recommendation import (
    Recipe,
    RecommendationCreate,
    RecommendationRecord,
    RecommendationResponse,
    ReferenceVideo,
    ShoppingItem,
)
from app.services.coupang_service import CoupangLinkService
from app.services.image_search_service import ImageSearchService
from app.services.llm_adapter import (
    DetailedRecipeLLMAdapter,
    MockRecipeLLMAdapter,
    QuickRecipeLLMAdapter,
    RecipeLLMAdapter,
)
from app.services.reference_service import gather_references
from app.services.validation import validate_response
from app.services.youtube_adapter import YouTubeRecipeAdapter

logger = logging.getLogger(__name__)

_llm_semaphore: asyncio.Semaphore | None = None


def get_llm_semaphore() -> asyncio.Semaphore:
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(settings.max_concurrent_llm)
    return _llm_semaphore


def build_cache_key(payload: RecommendationCreate) -> str:
    """재료 + 제약조건으로 캐시 키 생성 (SHA256, 동의어 정규화 적용)"""
    parts = {
        "ingredients": sorted(
            canonicalize_ingredient(i) for i in payload.ingredients
        ),
        "time_limit": payload.constraints.time_limit_min,
        "servings": payload.constraints.servings,
        "exclude": sorted(e.strip().lower() for e in payload.constraints.exclude),
        "quality": payload.constraints.quality_level,
    }
    raw = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def lookup_cache(cache_key: str, db: Session) -> RecommendationResponse | None:
    """캐시에서 레시피 조회. 만료되었으면 None 반환."""
    entry = db.query(RecipeCache).filter(RecipeCache.cache_key == cache_key).first()
    if not entry:
        return None

    if datetime.now(UTC) - entry.created_at.replace(tzinfo=UTC) > timedelta(days=settings.cache_expiry_days):
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
    정규화(normalize_ingredient) + 부분 매칭으로 퍼지 비교

    Args:
        user_ingredients: 사용자가 보유한 재료 목록
        recipe_ingredients: 레시피에 필요한 재료 목록

    Returns:
        (보유 재료, 필요 재료) 튜플
    """
    # 사용자 재료 정규화 세트 (원본 + 정규화)
    user_normalized = set()
    for i in user_ingredients:
        if not i or not i.strip():
            continue
        user_normalized.add(i.strip().lower())
        normalized = normalize_ingredient(i)
        if normalized:
            user_normalized.add(normalized.lower())

    have = []
    need = []

    for ri in recipe_ingredients:
        trimmed = ri.strip()
        if not trimmed:
            continue

        # 매칭 시도: 1) 원본 매칭, 2) 정규화 매칭, 3) 부분 매칭(포함 관계)
        ri_lower = trimmed.lower()
        ri_norm = normalize_ingredient(trimmed).lower()

        matched = (
            ri_lower in user_normalized
            or ri_norm in user_normalized
            or any(u in ri_norm or ri_norm in u for u in user_normalized if u)
        )

        if matched:
            have.append(trimmed)
        else:
            need.append(trimmed)

    return sorted(have), sorted(need)


async def create_recommendation(
    payload: RecommendationCreate, db: Session, skip_images: bool = False
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

    # 캐시 미스 → Semaphore 내에서 LLM 호출만 (이미지는 밖에서)
    async with get_llm_semaphore():
        # 1. 레시피 생성 어댑터 선택 (quality_level별 분기)
        provider = settings.recipe_provider
        quality = payload.constraints.quality_level
        logger.info(f"레시피 Provider: {provider}, Quality: {quality}")

        # 1.5 레퍼런스 수집 (카테고리별 역색인 매칭)
        reference_context = ""
        if provider != "mock":
            try:
                categories, methods = RecipeLLMAdapter.pick_categories()
                reference_context = await gather_references(
                    payload.ingredients,
                    quality,
                    exclude=payload.constraints.exclude,
                    categories=categories,
                    methods=methods,
                )
                if reference_context:
                    logger.info(f"레퍼런스 수집 완료: {len(reference_context)}자")
            except Exception as e:
                logger.warning(f"레퍼런스 수집 실패 (무시): {e}")
                reference_context = ""

        if provider == "mock":
            recipes_raw = MockRecipeLLMAdapter().generate_recipes(payload)
        elif quality == "fast":
            # 번개 모드: Haiku 직접 호출 (subprocess → to_thread)
            try:
                recipes_raw = await asyncio.to_thread(
                    QuickRecipeLLMAdapter().generate_recipes, payload,
                    reference_context=reference_context
                )
            except Exception as e:
                logger.warning(f"[번개] Haiku 실패, 더미 레시피 반환: {e}")
                recipes_raw = MockRecipeLLMAdapter().generate_recipes(payload)
        elif quality == "detailed":
            # 정밀 모드: Sonnet 강화 프롬프트 (subprocess → to_thread)
            try:
                recipes_raw = await asyncio.to_thread(
                    DetailedRecipeLLMAdapter().generate_recipes, payload,
                    reference_context=reference_context
                )
            except Exception as e:
                logger.warning(f"[정밀] Sonnet 실패, 기본 어댑터 폴백: {e}")
                recipes_raw = await asyncio.to_thread(
                    RecipeLLMAdapter().generate_recipes, payload,
                    reference_context=reference_context
                )
        elif provider == "youtube":
            try:
                recipes_raw = await YouTubeRecipeAdapter().generate_recipes(payload)
            except Exception as e:
                logger.warning(f"YouTube+Haiku 실패, Sonnet 폴백: {e}")
                try:
                    recipes_raw = await asyncio.to_thread(
                        RecipeLLMAdapter().generate_recipes, payload,
                        reference_context=reference_context
                    )
                except Exception as e2:
                    logger.error(f"Sonnet 폴백도 실패, 더미 레시피 반환: {e2}")
                    recipes_raw = MockRecipeLLMAdapter().generate_recipes(payload)
        else:
            # anthropic (기존 동작, subprocess → to_thread)
            recipes_raw = await asyncio.to_thread(
                RecipeLLMAdapter().generate_recipes, payload,
                reference_context=reference_context
            )

        llm_elapsed = time.monotonic() - start_time
        logger.info(f"레시피 생성 완료: {llm_elapsed:.1f}초 (provider={provider})")

    # 3. 이미지 처리 (세마포어 밖, 번개/skip_images 모드는 스킵) + YouTube 참고 영상 (정밀 모드)
    video_results: list[ReferenceVideo | None] = [None] * len(recipes_raw)

    if quality == "fast" or skip_images:
        logger.info("[이미지 스킵] fast 모드 또는 skip_images")
        image_results = [None] * len(recipes_raw)
    else:
        image_service = ImageSearchService(quality_level=quality)
        # 정밀 모드: 퀄리티 우선, 시간 제한 없이 완료까지 대기 (gunicorn 120s 내)
        if quality == "detailed":
            image_timeout = max(90 - llm_elapsed, 45)
        else:
            image_timeout = max(28 - llm_elapsed, 5)
        logger.info(f"이미지 검색 시작: {len(recipes_raw)}개 레시피 (타임아웃: {image_timeout:.1f}초)")
        image_tasks = [image_service.get_image(recipe.title) for recipe in recipes_raw]

        # 정밀 모드: YouTube 영상도 병렬 검색
        if quality == "detailed" and settings.youtube_api_key:
            try:
                from app.services.youtube_video_service import YouTubeVideoService

                yt_service = YouTubeVideoService()
                yt_tasks = [yt_service.find_reference_video(r.title) for r in recipes_raw]
                logger.info(f"[정밀] YouTube 참고 영상 검색 시작: {len(recipes_raw)}개")

                # 각 태스크를 개별 타임아웃으로 래핑하여 부분 결과 보존
                wrapped_img = [
                    asyncio.wait_for(t, timeout=image_timeout) for t in image_tasks
                ]
                wrapped_yt = [
                    asyncio.wait_for(t, timeout=image_timeout) for t in yt_tasks
                ]
                all_tasks = wrapped_img + wrapped_yt
                all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

                image_results = list(all_results[: len(recipes_raw)])
                video_results = list(all_results[len(recipes_raw) :])
            except ImportError as e:
                logger.warning(f"[정밀] YouTube 모듈 임포트 실패, 영상 없이 진행: {e}")
                wrapped_img = [
                    asyncio.wait_for(t, timeout=image_timeout) for t in image_tasks
                ]
                image_results = await asyncio.gather(*wrapped_img, return_exceptions=True)
        else:
            wrapped_img = [
                asyncio.wait_for(t, timeout=image_timeout) for t in image_tasks
            ]
            image_results = await asyncio.gather(*wrapped_img, return_exceptions=True)

    # 5. ingredients_have, ingredients_need 분리 + 이미지 URL + 참고 영상 추가
    final_recipes = []
    for i, (recipe, img_result) in enumerate(zip(recipes_raw, image_results, strict=False)):
        have, need = split_have_need(payload.ingredients, recipe.ingredients_total)

        # 이미지 검색 실패 처리
        if isinstance(img_result, Exception):
            err_type = type(img_result).__name__
            logger.warning(f"이미지 검색 실패 ({recipe.title}): [{err_type}] {img_result}")
            img_url = None
        else:
            img_url = img_result

        # YouTube 영상 결과 처리
        ref_video = None
        if i < len(video_results) and video_results[i] is not None:
            vr = video_results[i]
            if isinstance(vr, ReferenceVideo):
                ref_video = vr
            elif isinstance(vr, Exception):
                logger.warning(f"YouTube 영상 검색 실패 ({recipe.title}): {vr}")

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
            nutrition=recipe.nutrition,
            substitutes=recipe.substitutes or [],
            storage_tip=recipe.storage_tip,
            reference_video=ref_video,
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
        id=rec_id,
        created_at=datetime.now(UTC),
        quality_level=quality,
        recipes=final_recipes,
        shopping_list=shopping_list,
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
    # 품질 검증 실패(제목 재료 누락 등) 시 캐시 스킵 → 다음 요청에서 재생성
    skip_cache = getattr(response, "_skip_cache", False)
    if skip_cache:
        logger.info("품질 검증 미달로 캐시 저장 스킵 (다음 요청 시 재생성)")
    else:
        try:
            save_cache(cache_key, response, db)
        except Exception as e:
            logger.warning(f"캐시 저장 실패 (무시): {e}")

    # 9. 비용 추정 로깅
    llm_costs = {"anthropic": 0.035, "youtube": 0.010, "mock": 0.0}
    quality_llm_overrides = {"fast": 0.007, "detailed": 0.065}
    image_provider = settings.image_search_provider.lower()
    # 정밀 모드 이미지 비용 (고품질 모델)
    if quality == "detailed":
        img_costs_per = {"gemini": 0.060, "google": 0.005, "unsplash": 0.0, "mock": 0.0}
    else:
        img_costs_per = {"gemini": 0.039, "google": 0.005, "unsplash": 0.0, "mock": 0.0}
    llm_cost = quality_llm_overrides.get(quality, llm_costs.get(provider, 0.015))
    num_images = sum(1 for r in final_recipes if r.image_url)
    num_videos = sum(1 for r in final_recipes if r.reference_video)
    img_cost = img_costs_per.get(image_provider, 0.0) * num_images
    total_cost = llm_cost + img_cost
    elapsed = time.monotonic() - start_time
    logger.info(
        f"💰 Cost: LLM=${llm_cost:.3f}, Image=${img_cost:.3f}, Total=${total_cost:.3f} "
        f"(provider={provider}, image={image_provider}, videos={num_videos}, {elapsed:.1f}s)"
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
