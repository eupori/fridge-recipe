"""
공통 테스트 fixture

- 인메모리 SQLite 엔진 (session scope)
- 트랜잭션 롤백으로 테스트 격리
- FastAPI TestClient + DB 의존성 오버라이드
- 테스트 유저 + JWT 인증
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.main import create_app
from app.models.user import User


@pytest.fixture(scope="session")
def engine():
    """인메모리 SQLite 엔진 (세션 전체에서 1회 생성)"""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture
def db(engine):
    """각 테스트마다 트랜잭션 열고 롤백 (데이터 격리)"""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    # 중첩 트랜잭션 지원 (session.commit() 호출 시 실제 커밋 방지)
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    """FastAPI TestClient (get_db 오버라이드)"""
    from fastapi.testclient import TestClient

    app = create_app()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db) -> User:
    """테스트 유저 생성"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user) -> str:
    """테스트 유저 JWT 토큰"""
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(auth_token) -> dict:
    """인증 헤더"""
    return {"Authorization": f"Bearer {auth_token}"}
