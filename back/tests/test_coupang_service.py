"""
coupang_service.py 테스트

- generate_search_url(): tracking_id 포함, 한글 인코딩, None 반환
- enabled 프로퍼티
"""

from unittest.mock import patch

import pytest

from app.services.coupang_service import CoupangLinkService


class TestCoupangLinkService:
    def test_generate_url_with_tracking_id(self):
        """tracking_id 설정 시 URL 반환"""
        with patch.object(CoupangLinkService, "__init__", lambda self: None):
            svc = CoupangLinkService()
            svc.tracking_id = "AF1234"
            svc.sub_id = None
            url = svc.generate_search_url("김치")
            assert url is not None
            assert "AF1234" in url
            assert "coupang.com" in url

    def test_generate_url_korean_encoding(self):
        """한글 재료명이 URL 인코딩됨"""
        with patch.object(CoupangLinkService, "__init__", lambda self: None):
            svc = CoupangLinkService()
            svc.tracking_id = "AF1234"
            svc.sub_id = None
            url = svc.generate_search_url("계란")
            assert url is not None
            assert "%EA%B3%84%EB%9E%80" in url  # 계란 URL 인코딩

    def test_generate_url_with_sub_id(self):
        """sub_id도 URL에 포함"""
        with patch.object(CoupangLinkService, "__init__", lambda self: None):
            svc = CoupangLinkService()
            svc.tracking_id = "AF1234"
            svc.sub_id = "mysub"
            url = svc.generate_search_url("김치")
            assert url is not None
            assert "subId=mysub" in url

    def test_generate_url_returns_none_without_tracking_id(self):
        """tracking_id 미설정 시 None 반환"""
        with patch.object(CoupangLinkService, "__init__", lambda self: None):
            svc = CoupangLinkService()
            svc.tracking_id = None
            svc.sub_id = None
            assert svc.generate_search_url("김치") is None

    def test_generate_url_returns_none_with_empty_tracking_id(self):
        """tracking_id가 빈 문자열이면 None"""
        with patch.object(CoupangLinkService, "__init__", lambda self: None):
            svc = CoupangLinkService()
            svc.tracking_id = ""
            svc.sub_id = None
            assert svc.generate_search_url("김치") is None

    def test_enabled_property_true(self):
        """tracking_id 설정 시 enabled=True"""
        with patch.object(CoupangLinkService, "__init__", lambda self: None):
            svc = CoupangLinkService()
            svc.tracking_id = "AF1234"
            svc.sub_id = None
            assert svc.enabled is True

    def test_enabled_property_false(self):
        """tracking_id 미설정 시 enabled=False"""
        with patch.object(CoupangLinkService, "__init__", lambda self: None):
            svc = CoupangLinkService()
            svc.tracking_id = None
            svc.sub_id = None
            assert svc.enabled is False
