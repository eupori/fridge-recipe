"""
Authentication API endpoints

- POST /auth/signup - 회원가입
- POST /auth/login - 로그인
- POST /auth/kakao - 카카오 로그인
- GET /auth/me - 내 정보 조회
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.user import TokenResponse, User, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService, get_auth_service, get_current_user


class KakaoLoginRequest(BaseModel):
    code: str
    redirect_uri: str

router = APIRouter()


@router.post("/signup", response_model=UserResponse)
def signup(data: UserCreate, auth_service: AuthService = Depends(get_auth_service)):
    """
    회원가입

    - **email**: 유효한 이메일 주소
    - **password**: 최소 6자 이상

    이메일이 이미 등록되어 있으면 400 에러를 반환합니다.
    """
    return auth_service.signup(data)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, auth_service: AuthService = Depends(get_auth_service)):
    """
    로그인

    - **email**: 등록된 이메일 주소
    - **password**: 비밀번호

    성공 시 JWT 액세스 토큰을 반환합니다.
    """
    return auth_service.login(data)


@router.post("/kakao", response_model=TokenResponse)
async def kakao_login(
    data: KakaoLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    카카오 로그인

    - **code**: 카카오 인가 코드
    - **redirect_uri**: 리다이렉트 URI

    카카오 인증 후 JWT 액세스 토큰을 반환합니다.
    """
    return await auth_service.kakao_authenticate(data.code, data.redirect_uri)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    내 정보 조회

    인증 필요: Authorization: Bearer {token}
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        nickname=current_user.nickname,
        provider=current_user.provider,
        created_at=current_user.created_at,
    )
