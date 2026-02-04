from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import settings
from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
    Recipe,
    ShoppingItem,
)
from app.services.llm_adapter import RecipeLLMAdapter, MockRecipeLLMAdapter
from app.services.image_search_service import ImageSearchService
from app.services.validation import validate_response

logger = logging.getLogger(__name__)

# NOTE: MVP용 인메모리 저장소(배포/재시작 시 사라짐)
_STORE: dict[str, RecommendationResponse] = {}


def split_have_need(
    user_ingredients: list[str],
    recipe_ingredients: list[str]
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
    user_map = {i.strip().lower(): i.strip() for i in user_ingredients if i and i.strip()}
    recipe_map = {i.strip().lower(): i.strip() for i in recipe_ingredients if i and i.strip()}

    # 보유 재료: 사용자가 가진 것 중 레시피에 필요한 것
    have_keys = user_set & recipe_set
    have = sorted([recipe_map[k] for k in have_keys])

    # 필요 재료: 레시피에 필요한 것 중 사용자가 없는 것
    need_keys = recipe_set - user_set
    need = sorted([recipe_map[k] for k in need_keys])

    return have, need


async def create_recommendation(payload: RecommendationCreate) -> RecommendationResponse:
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

    # 1. LLM 어댑터 선택 (mock 또는 실제)
    if settings.llm_provider == "mock":
        llm_adapter = MockRecipeLLMAdapter()
    else:
        llm_adapter = RecipeLLMAdapter()

    # 2. LLM으로 레시피 생성 (ingredients_total만 포함)
    recipes_raw = llm_adapter.generate_recipes(payload)

    # 3. 이미지 검색 서비스 초기화
    image_service = ImageSearchService()

    # 4. 이미지 병렬 검색 (3개 레시피 동시 처리)
    logger.info(f"이미지 검색 시작: {len(recipes_raw)}개 레시피")
    image_tasks = [
        image_service.get_image(recipe.title)
        for recipe in recipes_raw
    ]
    image_results = await asyncio.gather(*image_tasks, return_exceptions=True)

    # 5. ingredients_have, ingredients_need 분리 + 이미지 URL 추가
    final_recipes = []
    for recipe, img_result in zip(recipes_raw, image_results):
        have, need = split_have_need(
            payload.ingredients,
            recipe.ingredients_total
        )

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
            warnings=recipe.warnings or []
        )
        final_recipes.append(final_recipe)

    logger.info(f"이미지 검색 완료: {sum(1 for r in final_recipes if r.image_url)}개 성공")

    # 4. 장보기 리스트 생성 (모든 레시피의 필요 재료 중복 제거)
    all_need: set[str] = set()
    for r in final_recipes:
        all_need |= {x for x in r.ingredients_need if x}

    shopping_list = [ShoppingItem(item=i) for i in sorted(list(all_need))]

    # 5. 응답 객체 생성
    rec_id = f"rec_{uuid4().hex[:10]}"
    response = RecommendationResponse(
        id=rec_id,
        created_at=datetime.now(timezone.utc),
        recipes=final_recipes,
        shopping_list=shopping_list
    )

    # 6. 검증 (LLM 출력이 규칙 만족하는지 확인)
    validate_response(response, payload)

    # 7. 메모리 저장 및 반환
    _STORE[rec_id] = response
    logger.info(f"레시피 생성 완료: ID={rec_id}")
    return response


def get_recommendation(recommendation_id: str) -> RecommendationResponse | None:
    return _STORE.get(recommendation_id)
