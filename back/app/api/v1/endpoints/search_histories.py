"""
Search Histories API endpoints

- GET /search-histories - 최근 7일 검색 기록 조회
- DELETE /search-histories/{id} - 특정 기록 삭제
- DELETE /search-histories/all - 모든 기록 삭제
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.models.search_history import SearchHistoryResponse
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.search_history_service import (
    SearchHistoryService,
    get_search_history_service,
)


router = APIRouter()


@router.get("", response_model=list[SearchHistoryResponse])
def get_search_histories(
    limit: int = Query(default=20, ge=1, le=100, description="최대 조회 개수"),
    current_user: User = Depends(get_current_user),
    service: SearchHistoryService = Depends(get_search_history_service),
):
    """
    최근 7일 검색 기록 조회

    인증 필요: Authorization: Bearer {token}
    """
    return service.get_user_histories(current_user.id, limit=limit)


@router.delete("/all")
def delete_all_search_histories(
    current_user: User = Depends(get_current_user),
    service: SearchHistoryService = Depends(get_search_history_service),
):
    """
    모든 검색 기록 삭제

    인증 필요: Authorization: Bearer {token}
    """
    deleted_count = service.delete_all(current_user.id)
    return {"ok": True, "deleted_count": deleted_count}


@router.delete("/{history_id}")
def delete_search_history(
    history_id: UUID,
    current_user: User = Depends(get_current_user),
    service: SearchHistoryService = Depends(get_search_history_service),
):
    """
    특정 검색 기록 삭제

    인증 필요: Authorization: Bearer {token}
    """
    service.delete(current_user.id, history_id)
    return {"ok": True}
