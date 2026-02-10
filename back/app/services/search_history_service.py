"""
Search history service

- 검색 기록 생성/조회/삭제
- 최근 7일 기록만 반환
"""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.search_history import (
    SearchHistory,
    SearchHistoryCreate,
    SearchHistoryResponse,
)


class SearchHistoryService:
    """검색 기록 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: UUID, data: SearchHistoryCreate) -> SearchHistory:
        """검색 기록 저장"""
        history = SearchHistory(
            user_id=user_id,
            recommendation_id=data.recommendation_id,
            ingredients=data.ingredients,
            time_limit_min=data.time_limit_min,
            servings=data.servings,
            recipe_titles=data.recipe_titles,
            recipe_images=data.recipe_images,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def get_user_histories(self, user_id: UUID, limit: int = 20) -> list[SearchHistoryResponse]:
        """사용자의 최근 7일 검색 기록 조회"""
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        histories = (
            self.db.query(SearchHistory)
            .filter(
                SearchHistory.user_id == user_id,
                SearchHistory.searched_at >= seven_days_ago,
            )
            .order_by(SearchHistory.searched_at.desc())
            .limit(limit)
            .all()
        )

        return [
            SearchHistoryResponse(
                id=str(h.id),
                recommendation_id=h.recommendation_id,
                ingredients=h.ingredients,
                time_limit_min=h.time_limit_min,
                servings=h.servings,
                recipe_titles=h.recipe_titles,
                recipe_images=h.recipe_images or [],
                searched_at=h.searched_at,
            )
            for h in histories
        ]

    def delete(self, user_id: UUID, history_id: UUID) -> None:
        """검색 기록 삭제"""
        history = (
            self.db.query(SearchHistory)
            .filter(
                SearchHistory.id == history_id,
                SearchHistory.user_id == user_id,
            )
            .first()
        )

        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="검색 기록을 찾을 수 없습니다."
            )

        self.db.delete(history)
        self.db.commit()

    def delete_all(self, user_id: UUID) -> int:
        """모든 검색 기록 삭제, 삭제된 개수 반환"""
        deleted_count = (
            self.db.query(SearchHistory).filter(SearchHistory.user_id == user_id).delete()
        )
        self.db.commit()
        return deleted_count


def get_search_history_service(db: Session = Depends(get_db)) -> SearchHistoryService:
    """FastAPI 의존성 주입용"""
    return SearchHistoryService(db)
