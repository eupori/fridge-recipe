"""
/api/v1/stats 엔드포인트 테스트
"""

import pytest


class TestStatsAPI:
    def test_get_stats_success(self, client):
        """GET /api/v1/stats 성공"""
        resp = client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_recipes_generated" in data
        assert "total_users" in data

    def test_get_stats_returns_integers(self, client):
        """통계 값이 정수"""
        resp = client.get("/api/v1/stats")
        data = resp.json()
        assert isinstance(data["total_recipes_generated"], int)
        assert isinstance(data["total_users"], int)
