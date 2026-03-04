"""
API v1 라우터 통합 모듈
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    auth,
    device_provision,
    devices,
    events,
    guardian_app,
    guardians,
    policies,
    telemedicine,
    users,
    websocket,
)

api_router = APIRouter()

# 헬스체크 엔드포인트
@api_router.get("/health", tags=["Health"])
async def health_check():
    """서비스 상태 확인
    
    Returns:
        상태 정보
    """
    return {"status": "healthy", "version": "0.1.0"}


# 라우터 등록
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(guardians.router, prefix="", tags=["Guardians"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(events.router, prefix="", tags=["Events & Cases"])
api_router.include_router(policies.router, prefix="/policies", tags=["Policies"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI Services"])
api_router.include_router(guardian_app.router, prefix="/guardian-app", tags=["Guardian App"])
api_router.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])
api_router.include_router(device_provision.router, prefix="/device-mgmt", tags=["Device Management"])
api_router.include_router(telemedicine.router, prefix="/telemedicine", tags=["Telemedicine"])