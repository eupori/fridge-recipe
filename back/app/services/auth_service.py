"""
Authentication service

- 회원가입/로그인 로직
- JWT 토큰 관리
- 현재 사용자 조회
- 카카오 소셜 로그인
"""

import logging
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import TokenResponse, User, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthService:
    """인증 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def signup(self, data: UserCreate) -> UserResponse:
        """회원가입"""
        # 이메일 중복 체크
        existing = self.db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이미 등록된 이메일입니다."
            )

        # 사용자 생성
        user = User(
            email=data.email,
            password_hash=get_password_hash(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        return UserResponse(
            id=str(user.id), email=user.email, nickname=user.nickname, created_at=user.created_at
        )

    def login(self, data: UserLogin) -> TokenResponse:
        """로그인하여 JWT 토큰 반환"""
        user = self.db.query(User).filter(User.email == data.email).first()

        if user and not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="카카오로 가입된 계정입니다. 카카오 로그인을 이용해주세요.",
            )

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        # JWT 토큰 생성
        access_token = create_access_token(data={"sub": str(user.id)})
        return TokenResponse(access_token=access_token)

    async def kakao_authenticate(self, code: str, redirect_uri: str) -> TokenResponse:
        """카카오 OAuth 인증"""
        # 1. 카카오 토큰 교환
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://kauth.kakao.com/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.kakao_rest_api_key,
                    "client_secret": settings.kakao_client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )

        if token_resp.status_code != 200:
            logger.error("Kakao token exchange failed: %s", token_resp.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="카카오 인증에 실패했습니다.",
            )

        kakao_access_token = token_resp.json().get("access_token")

        # 2. 카카오 사용자 정보 조회
        async with httpx.AsyncClient() as client:
            user_resp = await client.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {kakao_access_token}"},
            )

        if user_resp.status_code != 200:
            logger.error("Kakao user info failed: %s", user_resp.text)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="카카오 사용자 정보를 가져올 수 없습니다.",
            )

        kakao_data = user_resp.json()
        kakao_id = str(kakao_data["id"])
        kakao_account = kakao_data.get("kakao_account", {})
        email = kakao_account.get("email")
        nickname = kakao_account.get("profile", {}).get("nickname")

        # 3. 사용자 찾기/생성
        user = self._find_or_create_kakao_user(kakao_id, email, nickname)

        # 4. JWT 발급
        access_token = create_access_token(data={"sub": str(user.id)})
        return TokenResponse(access_token=access_token)

    def _find_or_create_kakao_user(
        self, kakao_id: str, email: str | None, nickname: str | None
    ) -> User:
        """카카오 사용자 찾기 또는 생성"""
        # provider + provider_id로 검색
        user = (
            self.db.query(User)
            .filter(User.provider == "kakao", User.provider_id == kakao_id)
            .first()
        )
        if user:
            return user

        # 이메일로 기존 사용자 검색 → 연동
        if email:
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                user.provider = "kakao"
                user.provider_id = kakao_id
                self.db.commit()
                self.db.refresh(user)
                return user

        # 새 사용자 생성
        user = User(
            email=email,
            password_hash=None,
            provider="kakao",
            provider_id=kakao_id,
            nickname=nickname,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        logger.info("New Kakao user created: %s", kakao_id)
        return user

    def get_user_by_id(self, user_id: UUID) -> User | None:
        """ID로 사용자 조회"""
        return self.db.query(User).filter(User.id == user_id).first()


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """FastAPI 의존성 주입용"""
    return AuthService(db)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """현재 로그인한 사용자 반환 (인증 필수)"""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="인증이 필요합니다.")

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다."
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="토큰에 사용자 정보가 없습니다."
        )

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다."
        )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """현재 로그인한 사용자 반환 (선택적 - 로그인 안 해도 됨)"""
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return db.query(User).filter(User.id == UUID(user_id)).first()
