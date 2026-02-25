"""
Rating service

레시피 별점 평가 관련 비즈니스 로직
"""

from uuid import UUID

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.rating import (
    RatingCreate,
    RatingResponse,
    RecipeRating,
    RecipeRatingStats,
    RecommendationRatingStats,
)


class RatingService:
    """별점 평가 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def rate_recipe(self, user_id: UUID, data: RatingCreate) -> RatingResponse:
        """레시피 평가 (upsert: 기존 평가 있으면 업데이트)"""
        existing = (
            self.db.query(RecipeRating)
            .filter_by(
                recommendation_id=data.recommendation_id,
                recipe_index=data.recipe_index,
                user_id=user_id,
            )
            .first()
        )

        if existing:
            existing.rating = data.rating
            self.db.commit()
            self.db.refresh(existing)
            return RatingResponse(
                id=str(existing.id),
                recommendation_id=existing.recommendation_id,
                recipe_index=existing.recipe_index,
                rating=existing.rating,
                created_at=existing.created_at,
            )

        new_rating = RecipeRating(
            recommendation_id=data.recommendation_id,
            recipe_index=data.recipe_index,
            rating=data.rating,
            user_id=user_id,
        )
        self.db.add(new_rating)
        self.db.commit()
        self.db.refresh(new_rating)

        return RatingResponse(
            id=str(new_rating.id),
            recommendation_id=new_rating.recommendation_id,
            recipe_index=new_rating.recipe_index,
            rating=new_rating.rating,
            created_at=new_rating.created_at,
        )

    def get_rating_stats(
        self, recommendation_id: str, user_id: UUID | None = None
    ) -> RecommendationRatingStats:
        """추천의 각 레시피별 평가 통계 조회"""
        rows = (
            self.db.query(
                RecipeRating.recipe_index,
                func.avg(RecipeRating.rating).label("avg"),
                func.count().label("cnt"),
            )
            .filter_by(recommendation_id=recommendation_id)
            .group_by(RecipeRating.recipe_index)
            .all()
        )

        stats_map = {
            r.recipe_index: RecipeRatingStats(
                recipe_index=r.recipe_index,
                average_rating=round(float(r.avg), 1),
                count=r.cnt,
            )
            for r in rows
        }

        # 내 평가 조회
        if user_id:
            my_ratings = (
                self.db.query(RecipeRating)
                .filter_by(recommendation_id=recommendation_id, user_id=user_id)
                .all()
            )
            for mr in my_ratings:
                if mr.recipe_index in stats_map:
                    stats_map[mr.recipe_index].my_rating = mr.rating

        recipes = []
        for i in range(3):
            if i in stats_map:
                recipes.append(stats_map[i])
            else:
                recipes.append(
                    RecipeRatingStats(recipe_index=i, average_rating=0, count=0)
                )

        return RecommendationRatingStats(
            recommendation_id=recommendation_id, recipes=recipes
        )


def get_rating_service(db: Session = Depends(get_db)) -> RatingService:
    """FastAPI 의존성 주입용"""
    return RatingService(db)
