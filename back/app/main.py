import os
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import create_tables

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 DB 테이블 생성"""
    create_tables()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Fridge-Recipe API",
        lifespan=lifespan,
        description="""
        ## 냉장고 재료 기반 레시피 추천 API

        한국 사용자(자취생/1인가구·신혼)를 위한 이중언어(한국어/영어) 레시피 추천 서비스입니다.

        ### 주요 기능

        * **레시피 추천 생성**: 냉장고 재료를 입력하면 15분 이내로 만들 수 있는 레시피 3개 제공
        * **장보기 리스트**: 통합된 구매 필요 재료 목록 제공
        * **제약 조건**: 시간 제한, 인분, 조리 도구, 제외 재료 설정 가능

        ### 사용 흐름

        1. POST `/api/v1/recommendations` - 재료와 제약조건을 입력하여 추천 생성
        2. 응답으로 받은 `id`를 사용하여 추천 조회 가능
        3. GET `/api/v1/recommendations/{id}` - 저장된 추천 결과 조회
        """,
        version="0.1.0",
        contact={
            "name": "Fridge-Recipe Team",
        },
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Daily-Remaining"],
    )

    @app.get(
        "/health",
        tags=["health"],
        summary="헬스체크",
        description="서버 상태와 환경을 확인합니다.",
        responses={
            200: {
                "description": "서버가 정상 작동 중",
                "content": {"application/json": {"example": {"ok": True, "env": "dev"}}},
            }
        },
    )
    def health():
        """
        ## 헬스체크 엔드포인트

        서버가 정상적으로 실행 중인지 확인하고 현재 환경 정보를 반환합니다.

        ### 응답
        - **ok**: 서버 정상 여부 (항상 true)
        - **env**: 현재 환경 (dev, staging, prod 등)
        """
        return {"ok": True, "env": settings.app_env}

    app.include_router(api_router, prefix="/api/v1")

    # 정적 파일 서빙 (이미지 캐시 등)
    images_dir = Path(__file__).parent.parent / "data" / "images"
    os.makedirs(images_dir, exist_ok=True)
    app.mount("/static/images", StaticFiles(directory=str(images_dir)), name="static-images")

    return app


app = create_app()
