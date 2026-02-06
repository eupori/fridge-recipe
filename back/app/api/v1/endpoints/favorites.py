"""
Favorites API endpoints

- POST /favorites - 즐겨찾기 추가
- GET /favorites - 내 즐겨찾기 목록
- DELETE /favorites/{id} - 즐겨찾기 삭제
- GET /favorites/check - 즐겨찾기 여부 확인
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.models.favorite import FavoriteCreate, FavoriteResponse, FavoriteCheck
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.favorite_service import FavoriteService, get_favorite_service


router = APIRouter()


@router.post("", response_model=FavoriteResponse)
def add_favorite(
    data: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    즐겨찾기 추가

    인증 필요: Authorization: Bearer {token}
    """
    return favorite_service.add_favorite(current_user.id, data)


@router.get("", response_model=list[FavoriteResponse])
def get_favorites(
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    내 즐겨찾기 목록 조회

    인증 필요: Authorization: Bearer {token}
    """
    return favorite_service.get_user_favorites(current_user.id)


@router.delete("/{favorite_id}")
def remove_favorite(
    favorite_id: UUID,
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    즐겨찾기 삭제

    인증 필요: Authorization: Bearer {token}
    """
    favorite_service.remove_favorite(current_user.id, favorite_id)
    return {"ok": True}


@router.get("/check", response_model=FavoriteCheck)
def check_favorite(
    recommendation_id: str = Query(...),
    recipe_index: int = Query(..., ge=0, le=2),
    current_user: User = Depends(get_current_user),
    favorite_service: FavoriteService = Depends(get_favorite_service)
):
    """
    특정 레시피의 즐겨찾기 여부 확인

    인증 필요: Authorization: Bearer {token}
    """
    return favorite_service.check_favorite(
        current_user.id,
        recommendation_id,
        recipe_index
    )
