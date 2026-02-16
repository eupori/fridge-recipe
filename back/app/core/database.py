"""
Database connection configuration

PostgreSQL 연결 (Supabase 또는 Neon 지원)
- 비동기 SQLAlchemy 사용
- 연결 풀링 설정
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy 모델 기본 클래스"""

    pass


# 데이터베이스 URL이 설정되지 않은 경우 SQLite 폴백 (개발용)
if settings.database_url:
    SQLALCHEMY_DATABASE_URL = settings.database_url
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./fridge_recipe.db"

# SQLite 연결 시 추가 설정
connect_args = {}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,  # 연결 상태 확인
}

# PostgreSQL 연결 풀링 최적화 (Supabase Session Pooler 사용 시)
if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
        "pool_recycle": 300,  # 5분마다 연결 갱신
    })

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI 의존성 주입용 DB 세션 생성기"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """모든 테이블 생성 (개발용)"""
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception:
        # 여러 gunicorn 워커가 동시에 시작할 때 race condition 방지
        pass
