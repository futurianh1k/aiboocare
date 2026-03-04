"""
데이터베이스 세션 관리 모듈

참고: SQLAlchemy 2.0 비동기 세션
https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.base import Base  # 모델 베이스 클래스 임포트

# 비동기 엔진 생성
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # 연결 유효성 검사
    pool_size=10,
    max_overflow=20,
)

# 세션 팩토리
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """데이터베이스 테이블 초기화 (개발용)
    
    프로덕션에서는 Alembic 마이그레이션 사용
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """데이터베이스 연결 종료"""
    await async_engine.dispose()
