"""
Ratings API endpoints

- POST /ratings - 레시피 별점 평가
- GET /ratings/{recommendation_id} - 평가 통계 조회
"""

from fastapi import APIRouter, Depends

from app.models.rating import RatingCreate, RatingResponse, RecommendationRatingStats
from app.models.user import User
from app.services.auth_service import get_current_user, get_current_user_optional
from app.services.rating_service import RatingService, get_rating_service

router = APIRouter()


@router.post("", response_model=RatingResponse)
async def rate_recipe(
    data: RatingCreate,
    current_user: User = Depends(get_current_user),
    rating_service: RatingService = Depends(get_rating_service),
):
    """
    레시피 별점 평가 (1-5)

    인증 필요: Authorization: Bearer {token}
    이미 평가한 레시피는 점수가 업데이트됩니다.
    """
    return rating_service.rate_recipe(current_user.id, data)


@router.get("/{recommendation_id}", response_model=RecommendationRatingStats)
async def get_rating_stats(
    recommendation_id: str,
    current_user: User | None = Depends(get_current_user_optional),
    rating_service: RatingService = Depends(get_rating_service),
):
    """
    추천의 각 레시피별 평가 통계 조회

    인증 선택: 로그인 시 내 평가도 포함
    """
    user_id = current_user.id if current_user else None
    return rating_service.get_rating_stats(recommendation_id, user_id)
