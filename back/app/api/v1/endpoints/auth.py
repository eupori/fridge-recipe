"""
Authentication API endpoints

- POST /auth/signup - 회원가입
- POST /auth/login - 로그인
- GET /auth/me - 내 정보 조회
"""

from fastapi import APIRouter, Depends

from app.models.user import TokenResponse, User, UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService, get_auth_service, get_current_user

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
        created_at=current_user.created_at,
    )
