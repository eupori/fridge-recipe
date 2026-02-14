from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.recommendation import (
    RecommendationCreate,
    RecommendationResponse,
)
from app.models.search_history import SearchHistoryCreate
from app.models.user import User
from app.services.auth_service import get_current_user_optional
from app.services.recommendation_service import create_recommendation, get_recommendation
from app.services.search_history_service import SearchHistoryService
from app.services.usage_service import UsageService

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
    # 비로그인 사용자 일일 사용량 체크
    usage_service = UsageService(db)
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
    remaining = None

    if not current_user:
        remaining = usage_service.get_remaining(client_ip)
        if remaining <= 0:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "일일 무료 이용 횟수를 초과했습니다. 로그인하면 무제한으로 이용할 수 있어요!",
                    "remaining": 0,
                },
                headers={"X-Daily-Remaining": "0"},
            )

    try:
        response = await create_recommendation(payload, db)

        # 비로그인 사용자 사용량 증가
        if not current_user:
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
        raise HTTPException(status_code=400, detail=str(e)) from e


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
