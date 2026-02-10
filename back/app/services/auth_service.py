"""
Authentication service

- 회원가입/로그인 로직
- JWT 토큰 관리
- 현재 사용자 조회
"""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import TokenResponse, User, UserCreate, UserLogin, UserResponse

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

        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다.",
            )

        # JWT 토큰 생성
        access_token = create_access_token(data={"sub": str(user.id)})
        return TokenResponse(access_token=access_token)

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
