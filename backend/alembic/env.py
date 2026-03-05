"""
Alembic 마이그레이션 환경 설정

동기 SQLAlchemy + PostgreSQL 지원
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# 앱 모델 및 설정 임포트
from app.core.config import settings
from app.db.session import Base

# 모델 임포트 (마이그레이션 자동 감지를 위해 필요)
from app.models import *  # noqa: F401, F403

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 메타데이터 설정
target_metadata = Base.metadata


def get_url() -> str:
    """데이터베이스 URL 반환 (동기 드라이버용)"""
    return settings.DATABASE_URL


def run_migrations_offline() -> None:
    """오프라인 모드 마이그레이션 실행
    
    SQL 스크립트만 생성 (실제 DB 연결 없음)
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """온라인 모드 마이그레이션 실행
    
    실제 DB에 연결하여 마이그레이션 적용
    """
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
