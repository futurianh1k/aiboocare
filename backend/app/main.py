"""
AI Care Companion - FastAPI 메인 애플리케이션

독거노인 돌봄 AI 어시스턴트 백엔드 서버
"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.session import close_db, init_db

# 워커 활성화 여부 (환경변수로 제어)
ENABLE_MQTT_WORKER = os.getenv("ENABLE_MQTT_WORKER", "false").lower() == "true"
ENABLE_ESCALATION_SCHEDULER = os.getenv("ENABLE_ESCALATION_SCHEDULER", "false").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리
    
    시작 시:
    - 로깅 설정
    - 데이터베이스 연결 초기화
    - MQTT 워커 시작 (옵션)
    - 에스컬레이션 스케줄러 시작 (옵션)
    
    종료 시:
    - 워커/스케줄러 중지
    - 데이터베이스 연결 종료
    """
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # 개발 환경에서만 테이블 자동 생성 (프로덕션은 Alembic 사용)
    if settings.ENVIRONMENT == "development":
        try:
            await init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Database initialization skipped: {type(e).__name__}")
    
    # Background tasks
    tasks = []
    
    # MQTT 워커 시작 (백그라운드 태스크)
    if ENABLE_MQTT_WORKER:
        from app.workers.mqtt_worker import mqtt_worker
        mqtt_task = asyncio.create_task(mqtt_worker.start())
        tasks.append(("mqtt", mqtt_task))
        logger.info("MQTT worker started as background task")
    
    # 에스컬레이션 스케줄러 시작 (백그라운드 태스크)
    if ENABLE_ESCALATION_SCHEDULER:
        from app.workers.escalation_scheduler import escalation_scheduler
        scheduler_task = asyncio.create_task(escalation_scheduler.start())
        tasks.append(("escalation", scheduler_task))
        logger.info("Escalation scheduler started as background task")
    
    yield
    
    # Shutdown
    if ENABLE_MQTT_WORKER:
        from app.workers.mqtt_worker import mqtt_worker
        await mqtt_worker.stop()
    
    if ENABLE_ESCALATION_SCHEDULER:
        from app.workers.escalation_scheduler import escalation_scheduler
        await escalation_scheduler.stop()
    
    # 모든 백그라운드 태스크 취소
    for name, task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info(f"{name} task stopped")
    
    await close_db()
    logger.info("Application shutdown complete")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="독거노인 돌봄 AI 어시스턴트 백엔드 API",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if settings.DEBUG else None,
    docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 전역 예외 핸들러
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러
    
    사용자에게는 일반적인 메시지만 제공하고,
    상세 스택트레이스는 내부 로그에만 기록합니다.
    """
    # 내부 로그에만 상세 정보 기록 (민감 정보 제외)
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={"path": request.url.path, "method": request.method},
        exc_info=True,
    )
    
    # 사용자에게는 일반적인 메시지만 반환
    return JSONResponse(
        status_code=500,
        content={
            "detail": "요청을 처리하는 중 오류가 발생했습니다. 다시 시도해 주세요.",
            "error_code": "INTERNAL_ERROR",
        },
    )


# API 라우터 등록
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# 루트 엔드포인트
@app.get("/", tags=["Root"])
async def root():
    """API 루트 엔드포인트"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
    }


# 상태 확인 엔드포인트 (상세)
@app.get("/status", tags=["Root"])
async def status():
    """서비스 상태 확인 (상세)"""
    mqtt_status = "disabled"
    scheduler_status = "disabled"
    
    if ENABLE_MQTT_WORKER:
        from app.workers.mqtt_worker import mqtt_worker
        mqtt_status = "running" if mqtt_worker.running else "stopped"
    
    if ENABLE_ESCALATION_SCHEDULER:
        from app.workers.escalation_scheduler import escalation_scheduler
        scheduler_status = "running" if escalation_scheduler.running else "stopped"
    
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "workers": {
            "mqtt": mqtt_status,
            "escalation_scheduler": scheduler_status,
        },
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
