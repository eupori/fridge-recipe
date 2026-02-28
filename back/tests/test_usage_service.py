"""
usage_service.py 테스트

- get_remaining(): 초기 잔여 횟수
- increment(): 사용 후 잔여 감소
- check_limit(): 제한 초과 여부
- IP별 독립 카운트
"""

import pytest

from app.services.usage_service import UsageService


class TestUsageService:
    def test_initial_remaining(self, db):
        """첫 사용 전 잔여 횟수 = daily_limit"""
        svc = UsageService(db)
        assert svc.get_remaining("192.168.1.1", limit=3) == 3

    def test_increment_decreases_remaining(self, db):
        """increment 후 잔여 횟수 감소"""
        svc = UsageService(db)
        remaining = svc.increment("192.168.1.1", limit=3)
        assert remaining == 2

    def test_multiple_increments(self, db):
        """여러 번 increment"""
        svc = UsageService(db)
        svc.increment("192.168.1.1", limit=3)
        svc.increment("192.168.1.1", limit=3)
        remaining = svc.increment("192.168.1.1", limit=3)
        assert remaining == 0

    def test_check_limit_initially_true(self, db):
        """초기 상태에서 사용 가능"""
        svc = UsageService(db)
        assert svc.check_limit("192.168.1.1", limit=3) is True

    def test_check_limit_after_exhausted(self, db):
        """제한 소진 후 False"""
        svc = UsageService(db)
        for _ in range(3):
            svc.increment("192.168.1.1", limit=3)
        assert svc.check_limit("192.168.1.1", limit=3) is False

    def test_independent_ip_tracking(self, db):
        """다른 IP는 독립적으로 카운트"""
        svc = UsageService(db)
        svc.increment("192.168.1.1", limit=3)
        svc.increment("192.168.1.1", limit=3)
        # 다른 IP는 아직 사용하지 않음
        assert svc.get_remaining("192.168.1.2", limit=3) == 3

    def test_remaining_never_negative(self, db):
        """잔여 횟수는 0 미만이 되지 않음"""
        svc = UsageService(db)
        for _ in range(5):
            svc.increment("192.168.1.1", limit=3)
        assert svc.get_remaining("192.168.1.1", limit=3) == 0
