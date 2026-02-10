"""
Favorite service

- 즐겨찾기 추가/삭제/조회
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.favorite import (
    Favorite,
    FavoriteCheck,
    FavoriteCreate,
    FavoriteResponse,
    RecipeLikeCount,
    RecommendationLikeStats,
)


class FavoriteService:
    """즐겨찾기 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def add_favorite(self, user_id: UUID, data: FavoriteCreate) -> FavoriteResponse:
        """즐겨찾기 추가"""
        # 이미 즐겨찾기 되어 있는지 확인
        existing = (
            self.db.query(Favorite)
            .filter(
                Favorite.user_id == user_id,
                Favorite.recommendation_id == data.recommendation_id,
                Favorite.recipe_index == data.recipe_index,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이미 즐겨찾기에 추가되어 있습니다."
            )

        favorite = Favorite(
            user_id=user_id,
            recommendation_id=data.recommendation_id,
            recipe_index=data.recipe_index,
            recipe_title=data.recipe_title,
            recipe_image_url=data.recipe_image_url,
        )
        self.db.add(favorite)
        self.db.commit()
        self.db.refresh(favorite)

        return FavoriteResponse(
            id=str(favorite.id),
            recommendation_id=favorite.recommendation_id,
            recipe_index=favorite.recipe_index,
            recipe_title=favorite.recipe_title,
            recipe_image_url=favorite.recipe_image_url,
            created_at=favorite.created_at,
        )

    def remove_favorite(self, user_id: UUID, favorite_id: UUID) -> None:
        """즐겨찾기 삭제"""
        favorite = (
            self.db.query(Favorite)
            .filter(Favorite.id == favorite_id, Favorite.user_id == user_id)
            .first()
        )

        if not favorite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="즐겨찾기를 찾을 수 없습니다."
            )

        self.db.delete(favorite)
        self.db.commit()

    def get_user_favorites(self, user_id: UUID) -> list[FavoriteResponse]:
        """사용자의 모든 즐겨찾기 조회"""
        favorites = (
            self.db.query(Favorite)
            .filter(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
            .all()
        )

        return [
            FavoriteResponse(
                id=str(f.id),
                recommendation_id=f.recommendation_id,
                recipe_index=f.recipe_index,
                recipe_title=f.recipe_title,
                recipe_image_url=f.recipe_image_url,
                created_at=f.created_at,
            )
            for f in favorites
        ]

    def check_favorite(
        self, user_id: UUID, recommendation_id: str, recipe_index: int
    ) -> FavoriteCheck:
        """특정 레시피의 즐겨찾기 여부 확인"""
        favorite = (
            self.db.query(Favorite)
            .filter(
                Favorite.user_id == user_id,
                Favorite.recommendation_id == recommendation_id,
                Favorite.recipe_index == recipe_index,
            )
            .first()
        )

        return FavoriteCheck(
            is_favorite=favorite is not None, favorite_id=str(favorite.id) if favorite else None
        )

    def get_recommendation_like_stats(self, recommendation_id: str) -> RecommendationLikeStats:
        """추천의 각 레시피별 좋아요 수 집계"""
        results = (
            self.db.query(Favorite.recipe_index, func.count(Favorite.id).label("like_count"))
            .filter(Favorite.recommendation_id == recommendation_id)
            .group_by(Favorite.recipe_index)
            .all()
        )

        # 기본값 0으로 초기화
        stats = {0: 0, 1: 0, 2: 0}
        for recipe_index, like_count in results:
            stats[recipe_index] = like_count

        return RecommendationLikeStats(
            recommendation_id=recommendation_id,
            recipes=[
                RecipeLikeCount(recipe_index=idx, like_count=count)
                for idx, count in sorted(stats.items())
            ],
        )


def get_favorite_service(db: Session = Depends(get_db)) -> FavoriteService:
    """FastAPI 의존성 주입용"""
    return FavoriteService(db)
