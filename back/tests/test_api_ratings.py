"""
/api/v1/ratings 엔드포인트 테스트
"""

import pytest


class TestRatingsAPI:
    def test_rate_requires_auth(self, client):
        """인증 없이 평가 시 401"""
        resp = client.post(
            "/api/v1/ratings",
            json={"recommendation_id": "rec_test", "recipe_index": 0, "rating": 4},
        )
        assert resp.status_code == 401

    def test_rate_success(self, client, auth_headers):
        """인증된 사용자 평가 성공"""
        resp = client.post(
            "/api/v1/ratings",
            json={"recommendation_id": "rec_test", "recipe_index": 0, "rating": 4},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["rating"] == 4

    def test_rate_invalid_rating_value(self, client, auth_headers):
        """유효하지 않은 별점 (0 또는 6)"""
        resp = client.post(
            "/api/v1/ratings",
            json={"recommendation_id": "rec_test", "recipe_index": 0, "rating": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_rate_invalid_recipe_index(self, client, auth_headers):
        """유효하지 않은 레시피 인덱스 (3 이상)"""
        resp = client.post(
            "/api/v1/ratings",
            json={"recommendation_id": "rec_test", "recipe_index": 3, "rating": 4},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_get_stats(self, client):
        """통계 조회 (인증 불필요)"""
        resp = client.get("/api/v1/ratings/rec_test123")
        assert resp.status_code == 200
        data = resp.json()
        assert "recipes" in data
        assert len(data["recipes"]) == 3
