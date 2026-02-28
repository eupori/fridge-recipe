import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.job import JobStatus
from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
)
from app.models.search_history import SearchHistoryCreate
from app.models.user import User
from app.services.auth_service import get_current_user_optional
from app.services.ingredient_checker import check_ingredients_with_llm
from app.services.ingredient_validator import sanitize_ingredients, validate_ingredients
from app.services.job_manager import create_job, get_job, update_job
from app.services.recommendation_service import (
    build_cache_key,
    create_recommendation,
    get_recommendation,
    lookup_cache,
)
from app.services.search_history_service import SearchHistoryService
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="레시피 추천 생성",
    description="냉장고 재료와 제약조건을 기반으로 새로운 레시피 추천을 생성합니다.",
    responses={
        200: {
            "description": "레시피 추천이 성공적으로 생성됨",
            "content": {
                "application/json": {
                    "example": {
                        "id": "rec_abc1234567",
                        "created_at": "2026-01-31T12:00:00",
                        "recipes": [
                            {
                                "title": "김치볶음밥",
                                "time_min": 10,
                                "servings": 1,
                                "summary": "간단하고 맛있는 김치볶음밥",
                                "image_url": None,
                                "ingredients_total": ["밥", "김치", "참기름"],
                                "ingredients_have": ["밥", "김치"],
                                "ingredients_need": ["참기름"],
                                "steps": ["김치를 잘게 썬다", "팬에 기름을 두르고 김치를 볶는다"],
                                "tips": [],
                                "warnings": [],
                            }
                        ],
                        "shopping_list": [
                            {"item": "참기름", "qty": None, "unit": None, "category": None}
                        ],
                    }
                }
            },
        },
        400: {"description": "잘못된 요청 (검증 실패)"},
    },
)
async def post_recommendations(
    payload: RecommendationCreate,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    ## 레시피 추천 생성

    냉장고에 있는 재료와 조리 제약조건을 입력하면 3개의 레시피와 통합 장보기 리스트를 반환합니다.

    ### 요청 예시
    - **ingredients**: 냉장고에 있는 재료 목록 (최소 1개 이상)
    - **constraints**: 조리 제약조건
      - time_limit_min: 최대 조리 시간 (5-60분, 기본값: 15분)
      - servings: 인분 (1-6인분, 기본값: 1인분)
      - tools: 사용 가능한 조리 도구
      - exclude: 제외할 재료

    ### 응답
    - 정확히 3개의 레시피
    - 각 레시피는 보유 재료와 구매 필요 재료로 분리됨
    - 통합된 장보기 리스트 (중복 제거됨)
    """
    # 재료 정제 (프롬프트 인젝션 방지)
    payload.ingredients = sanitize_ingredients(payload.ingredients)

    # 재료 검증 (비식품/위험 재료 차단)
    blocked = validate_ingredients(payload.ingredients)
    if blocked:
        blocked_str = ", ".join(blocked)
        raise HTTPException(
            status_code=400,
            detail=f"식품이 아닌 재료가 포함되어 있습니다: {blocked_str}. 먹을 수 있는 재료만 입력해주세요.",
        )

    if not payload.ingredients:
        raise HTTPException(status_code=400, detail="유효한 재료를 입력해주세요.")

    # LLM 기반 식재료 검증 (Haiku)
    non_food = await check_ingredients_with_llm(payload.ingredients)
    if non_food:
        non_food_str = ", ".join(non_food)
        raise HTTPException(
            status_code=400,
            detail=f"식재료가 아닌 항목이 포함되어 있습니다: {non_food_str}. 먹을 수 있는 재료만 입력해주세요.",
        )

    # 사용량 체크
    usage_service = UsageService(db)
    # Nginx가 설정하는 X-Real-IP 헤더 사용 (X-Forwarded-For는 스푸핑 가능)
    client_ip = request.headers.get("x-real-ip", request.client.host if request.client else "unknown").strip()
    remaining = None

    if current_user:
        # 로그인 사용자 일일 제한 (user_id 기반)
        user_key = f"user:{current_user.id}"
        remaining = usage_service.get_remaining(user_key, limit=settings.user_daily_limit)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"일일 이용 횟수({settings.user_daily_limit}회)를 초과했습니다. 내일 다시 이용해주세요!",
                    "remaining": 0,
                },
                headers={"X-Daily-Remaining": "0"},
            )
    else:
        # 비로그인 사용자 일일 제한 (IP 기반)
        remaining = usage_service.get_remaining(client_ip)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "일일 무료 이용 횟수를 초과했습니다. 로그인하면 더 많이 이용할 수 있어요!",
                    "remaining": 0,
                },
                headers={"X-Daily-Remaining": "0"},
            )

    try:
        response = await create_recommendation(payload, db)

        # 사용량 증가
        if current_user:
            user_key = f"user:{current_user.id}"
            remaining = usage_service.increment(user_key, limit=settings.user_daily_limit)
        else:
            remaining = usage_service.increment(client_ip)

        # 로그인 사용자의 경우 검색 기록 저장
        if current_user:
            search_history_service = SearchHistoryService(db)
            search_history_service.create(
                user_id=current_user.id,
                data=SearchHistoryCreate(
                    recommendation_id=response.id,
                    ingredients=payload.ingredients,
                    time_limit_min=payload.constraints.time_limit_min,
                    servings=payload.constraints.servings,
                    recipe_titles=[r.title for r in response.recipes],
                    recipe_images=[r.image_url for r in response.recipes],
                ),
            )

        # 응답에 남은 횟수 헤더 추가
        headers = {}
        if remaining is not None:
            headers["X-Daily-Remaining"] = str(remaining)

        return JSONResponse(
            content=response.model_dump(mode="json"),
            headers=headers,
        )
    except ValueError as e:
        msg = str(e)
        user_msg = {
            "recipes_must_be_3": "레시피 생성에 실패했습니다. 다시 시도해주세요.",
            "time_limit_exceeded": "시간 제한 내에 만들 수 있는 레시피를 찾지 못했습니다.",
            "steps_length_invalid": "레시피 생성에 실패했습니다. 다시 시도해주세요.",
        }.get(msg)
        if user_msg is None:
            if "exclude_ingredient_detected" in msg:
                ingredient = msg.split(": ", 1)[-1] if ": " in msg else ""
                user_msg = f"제외 재료({ingredient})가 포함된 레시피가 생성되었습니다. 다시 시도해주세요."
            else:
                user_msg = "레시피 생성에 실패했습니다. 다시 시도해주세요."
        raise HTTPException(status_code=400, detail=user_msg) from e


@router.get(
    "/{recommendation_id}",
    response_model=RecommendationResponse,
    summary="레시피 추천 조회",
    description="저장된 레시피 추천을 ID로 조회합니다.",
    responses={
        200: {"description": "레시피 추천 조회 성공"},
        404: {"description": "해당 ID의 추천을 찾을 수 없음"},
    },
)
def get_recommendations(
    recommendation_id: str,
    db: Session = Depends(get_db),
):
    """
    ## 레시피 추천 조회

    이전에 생성된 레시피 추천을 ID로 조회합니다.

    ### Path Parameters
    - **recommendation_id**: 추천 ID (예: rec_abc1234567)

    ### 응답
    - 생성 시점의 전체 추천 데이터 (레시피 3개 + 장보기 리스트)
    """
    rec = get_recommendation(recommendation_id, db)
    if rec is None:
        raise HTTPException(status_code=404, detail="not_found")
    return rec


# --- 비동기 큐 엔드포인트 ---


async def _background_generate(
    job_id: str,
    payload: RecommendationCreate,
    user_id: str | None,
    client_ip: str,
) -> None:
    """백그라운드에서 레시피 생성 (Job 상태 업데이트)"""
    update_job(job_id, status="processing", progress=5)
    db = SessionLocal()
    try:
        # LLM 기반 식재료 검증 (블록리스트 통과 후 추가 검증)
        non_food = await check_ingredients_with_llm(payload.ingredients)
        if non_food:
            non_food_str = ", ".join(non_food)
            update_job(
                job_id,
                status="failed",
                error=f"식재료가 아닌 항목이 포함되어 있습니다: {non_food_str}. 먹을 수 있는 재료만 입력해주세요.",
            )
            return
        update_job(job_id, progress=10)

        response = await create_recommendation(payload, db, skip_images=True)
        update_job(job_id, progress=80)

        # 사용량 증가
        usage_service = UsageService(db)
        if user_id:
            usage_service.increment(f"user:{user_id}", limit=settings.user_daily_limit)
        else:
            usage_service.increment(client_ip)

        # 검색 기록 저장
        if user_id:
            search_history_service = SearchHistoryService(db)
            search_history_service.create(
                user_id=user_id,
                data=SearchHistoryCreate(
                    recommendation_id=response.id,
                    ingredients=payload.ingredients,
                    time_limit_min=payload.constraints.time_limit_min,
                    servings=payload.constraints.servings,
                    recipe_titles=[r.title for r in response.recipes],
                    recipe_images=[r.image_url for r in response.recipes],
                ),
            )

        update_job(
            job_id,
            status="completed",
            progress=100,
            recommendation_id=response.id,
        )
    except Exception as e:
        logger.error(f"백그라운드 레시피 생성 실패 (job={job_id}): {e}")
        update_job(job_id, status="failed", error=str(e))
    finally:
        db.close()


@router.post(
    "/async",
    summary="비동기 레시피 추천 생성",
    description="레시피 추천을 비동기로 생성하고 Job ID를 반환합니다. 캐시 히트 시 즉시 recommendation_id를 반환합니다.",
)
async def post_recommendations_async(
    payload: RecommendationCreate,
    request: Request,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    # 재료 정제 (프롬프트 인젝션 방지) — 블록리스트만 (즉시 반환)
    payload.ingredients = sanitize_ingredients(payload.ingredients)

    # 재료 검증 (블록리스트 — 즉시, LLM 검증은 Job 내부에서)
    blocked = validate_ingredients(payload.ingredients)
    if blocked:
        blocked_str = ", ".join(blocked)
        raise HTTPException(
            status_code=400,
            detail=f"식품이 아닌 재료가 포함되어 있습니다: {blocked_str}. 먹을 수 있는 재료만 입력해주세요.",
        )

    if not payload.ingredients:
        raise HTTPException(status_code=400, detail="유효한 재료를 입력해주세요.")

    # 사용량 체크
    usage_service = UsageService(db)
    client_ip = request.headers.get(
        "x-real-ip", request.client.host if request.client else "unknown"
    ).strip()

    if current_user:
        user_key = f"user:{current_user.id}"
        remaining = usage_service.get_remaining(user_key, limit=settings.user_daily_limit)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"일일 이용 횟수({settings.user_daily_limit}회)를 초과했습니다. 내일 다시 이용해주세요!",
                    "remaining": 0,
                },
                headers={"X-Daily-Remaining": "0"},
            )
    else:
        remaining = usage_service.get_remaining(client_ip)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "일일 무료 이용 횟수를 초과했습니다. 로그인하면 더 많이 이용할 수 있어요!",
                    "remaining": 0,
                },
                headers={"X-Daily-Remaining": "0"},
            )

    # 캐시 히트 시 즉시 반환
    cache_key = build_cache_key(payload)
    cached = lookup_cache(cache_key, db)
    if cached is not None:
        from datetime import UTC, datetime
        from uuid import uuid4

        from app.models.recommendation import RecommendationRecord

        new_id = f"rec_{uuid4().hex[:10]}"
        cloned = cached.model_copy(update={"id": new_id, "created_at": datetime.now(UTC)})
        record = RecommendationRecord(
            id=new_id, created_at=cloned.created_at, data=cloned.model_dump(mode="json")
        )
        db.add(record)
        db.commit()

        # 사용량 증가
        if current_user:
            remaining = usage_service.increment(
                f"user:{current_user.id}", limit=settings.user_daily_limit
            )
        else:
            remaining = usage_service.increment(client_ip)

        # 검색 기록 저장
        if current_user:
            SearchHistoryService(db).create(
                user_id=current_user.id,
                data=SearchHistoryCreate(
                    recommendation_id=new_id,
                    ingredients=payload.ingredients,
                    time_limit_min=payload.constraints.time_limit_min,
                    servings=payload.constraints.servings,
                    recipe_titles=[r.title for r in cloned.recipes],
                    recipe_images=[r.image_url for r in cloned.recipes],
                ),
            )

        headers = {}
        if remaining is not None:
            headers["X-Daily-Remaining"] = str(remaining)
        return JSONResponse(
            content={"job_id": None, "recommendation_id": new_id},
            headers=headers,
        )

    # 캐시 미스 → Job 생성 + 백그라운드 처리
    job_id = create_job()
    asyncio.create_task(
        _background_generate(
            job_id,
            payload,
            user_id=current_user.id if current_user else None,
            client_ip=client_ip,
        )
    )
    return {"job_id": job_id, "recommendation_id": None}


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatus,
    summary="작업 상태 조회",
    description="비동기 레시피 생성 작업의 상태를 조회합니다.",
)
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return job
