"""
/api/v1/recommendations 엔드포인트 테스트

주의: POST 엔드포인트는 LLM 호출이 필요하므로 GET만 테스트
"""

import pytest

from app.services.ingredient_validator import validate_ingredients


class TestRecommendationsAPI:
    def test_get_nonexistent_returns_404(self, client):
        """존재하지 않는 추천 ID로 조회 시 404"""
        resp = client.get("/api/v1/recommendations/rec_nonexistent")
        assert resp.status_code == 404

    def test_post_empty_ingredients_returns_400(self, client):
        """빈 재료 목록으로 생성 시 400"""
        resp = client.post(
            "/api/v1/recommendations",
            json={
                "ingredients": [],
                "constraints": {"time_limit_min": 15, "servings": 1},
            },
        )
        assert resp.status_code == 400 or resp.status_code == 422

    def test_blocked_ingredient_detected(self):
        """차단 재료 검증 (단위 테스트)"""
        blocked = validate_ingredients(["표백제"])
        assert len(blocked) > 0
