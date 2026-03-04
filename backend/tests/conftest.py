"""
pytest 픽스처 설정

테스트 환경:
- 인메모리 SQLite 또는 테스트용 PostgreSQL
- 테스트 사용자 생성
- 인증된 클라이언트 픽스처
"""

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.security import hash_password
from app.main import app
from app.models.base import Base
from app.models.user import AdminUser, UserRole


# 테스트용 데이터베이스 URL (SQLite 인메모리)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """세션 범위 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """테스트용 데이터베이스 엔진"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션"""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> dict:
    """테스트용 사용자 생성"""
    plain_password = "TestPassword123"
    user = AdminUser(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=hash_password(plain_password),
        name="테스트 사용자",
        role=UserRole.ADMIN,
        is_active=True,
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return {
        "id": str(user.id),
        "email": user.email,
        "password": plain_password,  # 테스트용 평문 비밀번호
        "name": user.name,
        "role": user.role.value,
    }


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """테스트용 비인증 HTTP 클라이언트"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(
    db_session: AsyncSession,
    test_user: dict,
) -> AsyncGenerator[AsyncClient, None]:
    """테스트용 인증된 HTTP 클라이언트"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        # 로그인하여 토큰 획득
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )
        
        # 쿠키 설정
        if response.status_code == 200:
            # 응답 쿠키를 클라이언트에 설정
            for cookie_name, cookie_value in response.cookies.items():
                client.cookies.set(cookie_name, cookie_value)
        
        yield client
    
    app.dependency_overrides.clear()
