"""
rating_service.py 테스트

- rate_recipe(): 생성 및 upsert
- get_rating_stats(): 통계 집계
"""

import pytest

from app.models.rating import RatingCreate
from app.services.rating_service import RatingService


class TestRatingService:
    def test_rate_recipe_creates_new(self, db, test_user):
        """새 평가 생성"""
        svc = RatingService(db)
        result = svc.rate_recipe(
            test_user.id,
            RatingCreate(recommendation_id="rec_test123", recipe_index=0, rating=4),
        )
        assert result.rating == 4
        assert result.recipe_index == 0

    def test_rate_recipe_upsert_updates(self, db, test_user):
        """같은 레시피에 재평가하면 업데이트"""
        svc = RatingService(db)
        svc.rate_recipe(
            test_user.id,
            RatingCreate(recommendation_id="rec_test123", recipe_index=0, rating=3),
        )
        result = svc.rate_recipe(
            test_user.id,
            RatingCreate(recommendation_id="rec_test123", recipe_index=0, rating=5),
        )
        assert result.rating == 5

    def test_get_rating_stats_empty(self, db):
        """평가 없을 때 기본값"""
        svc = RatingService(db)
        stats = svc.get_rating_stats("rec_nonexist")
        assert len(stats.recipes) == 3
        for r in stats.recipes:
            assert r.count == 0
            assert r.average_rating == 0

    def test_get_rating_stats_with_data(self, db, test_user):
        """평가 후 통계 계산"""
        svc = RatingService(db)
        svc.rate_recipe(
            test_user.id,
            RatingCreate(recommendation_id="rec_stats", recipe_index=0, rating=4),
        )
        stats = svc.get_rating_stats("rec_stats")
        r0 = stats.recipes[0]
        assert r0.count == 1
        assert r0.average_rating == 4.0

    def test_get_rating_stats_includes_my_rating(self, db, test_user):
        """로그인 사용자의 내 평가 포함"""
        svc = RatingService(db)
        svc.rate_recipe(
            test_user.id,
            RatingCreate(recommendation_id="rec_my", recipe_index=1, rating=3),
        )
        stats = svc.get_rating_stats("rec_my", user_id=test_user.id)
        r1 = stats.recipes[1]
        assert r1.my_rating == 3

    def test_get_rating_stats_no_my_rating_without_user(self, db, test_user):
        """user_id 없으면 my_rating은 None"""
        svc = RatingService(db)
        svc.rate_recipe(
            test_user.id,
            RatingCreate(recommendation_id="rec_nouser", recipe_index=2, rating=5),
        )
        stats = svc.get_rating_stats("rec_nouser")
        r2 = stats.recipes[2]
        assert r2.my_rating is None
