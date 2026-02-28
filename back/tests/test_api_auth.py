"""
/api/v1/auth 엔드포인트 테스트
"""

import pytest


class TestSignup:
    def test_signup_success(self, client):
        """회원가입 성공"""
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "new@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert "id" in data

    def test_signup_duplicate_email(self, client):
        """중복 이메일 가입 실패"""
        client.post(
            "/api/v1/auth/signup",
            json={"email": "dup@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "dup@example.com", "password": "password123"},
        )
        assert resp.status_code == 400

    def test_signup_short_password(self, client):
        """비밀번호 6자 미만 실패"""
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "short@example.com", "password": "12345"},
        )
        assert resp.status_code == 422

    def test_signup_invalid_email(self, client):
        """잘못된 이메일 형식"""
        resp = client.post(
            "/api/v1/auth/signup",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        """로그인 성공"""
        client.post(
            "/api/v1/auth/signup",
            json={"email": "login@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "password123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client):
        """잘못된 비밀번호"""
        client.post(
            "/api/v1/auth/signup",
            json={"email": "wrong@example.com", "password": "password123"},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email(self, client):
        """미등록 이메일"""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "noone@example.com", "password": "password123"},
        )
        assert resp.status_code == 401


class TestGetMe:
    def test_me_with_auth(self, client, auth_headers):
        """인증된 사용자 정보 조회"""
        resp = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"

    def test_me_without_auth(self, client):
        """인증 없이 조회 시 401"""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        """잘못된 토큰으로 조회 시 401"""
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert resp.status_code == 401
