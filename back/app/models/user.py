"""
User model and schemas

사용자 인증을 위한 최소한의 모델
- 이메일 + 비밀번호만 필수
- 닉네임은 선택사항
"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


# SQLAlchemy ORM 모델
class User(Base):
    """사용자 DB 모델"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic 스키마
class UserCreate(BaseModel):
    """회원가입 요청 스키마"""
    email: EmailStr
    password: str = Field(..., min_length=6, description="최소 6자 이상")


class UserLogin(BaseModel):
    """로그인 요청 스키마"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """사용자 응답 스키마 (비밀번호 제외)"""
    id: str
    email: str
    nickname: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT 토큰 응답 스키마"""
    access_token: str
    token_type: str = "bearer"
