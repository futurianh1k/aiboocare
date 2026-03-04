"""
보호자 앱 API 엔드포인트

- 보호자 인증 (로그인/로그아웃/토큰갱신)
- 케이스 조회 및 ACK
- 알림 조회
- FCM 토큰 등록
- 대시보드

보안 규칙:
- HttpOnly 쿠키로 JWT 토큰 관리
- 보호자는 자신의 돌봄 대상자 케이스만 조회 가능
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.core.logging import logger
from app.core.security import decode_token
from app.schemas.guardian_app import (
    AlertReadRequest,
    CaseAckRequest,
    CaseAckResponse,
    FCMTokenRegisterRequest,
    FCMTokenResponse,
    GuardianAlertResponse,
    GuardianCaseDetailResponse,
    GuardianCaseResponse,
    GuardianDashboardResponse,
    GuardianLoginRequest,
    GuardianLoginResponse,
    GuardianPasswordChangeRequest,
    GuardianTokenRefreshRequest,
)
from app.services.guardian_app import (
    GuardianAlertService,
    GuardianAuthService,
    GuardianCaseService,
    GuardianDashboardService,
)

router = APIRouter()


# ============== 헬퍼 함수 ==============

async def get_current_guardian(
    access_token: Optional[str] = Cookie(None, alias="guardian_token"),
) -> dict:
    """현재 보호자 정보 반환"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
        )
    
    payload = decode_token(access_token)
    if not payload or payload.get("type") != "guardian":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다.",
        )
    
    return payload


def set_guardian_cookies(response: JSONResponse, access_token: str, refresh_token: str):
    """보호자 토큰 쿠키 설정"""
    response.set_cookie(
        key="guardian_token",
        value=access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="guardian_refresh_token",
        value=refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def clear_guardian_cookies(response: JSONResponse):
    """보호자 토큰 쿠키 삭제"""
    response.delete_cookie(key="guardian_token")
    response.delete_cookie(key="guardian_refresh_token")


# ============== 인증 API ==============

@router.post("/login", response_model=GuardianLoginResponse)
async def guardian_login(
    request: Request,
    login_data: GuardianLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """보호자 로그인
    
    전화번호와 비밀번호로 로그인합니다.
    성공 시 HttpOnly 쿠키로 토큰을 설정합니다.
    """
    service = GuardianAuthService(db)
    
    ip_address = request.client.host if request.client else ""
    result = await service.login(
        phone=login_data.phone,
        password=login_data.password,
        ip_address=ip_address,
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="전화번호 또는 비밀번호가 올바르지 않습니다.",
        )
    
    response_data = GuardianLoginResponse(
        success=True,
        guardian_id=result["guardian_id"],
        name=result["guardian_name"],
        care_user_name=result["care_user_name"],
        care_user_id=result["care_user_id"],
    )
    
    response = JSONResponse(content=response_data.model_dump(mode="json"))
    set_guardian_cookies(response, result["access_token"], result["refresh_token"])
    
    return response


@router.post("/logout")
async def guardian_logout(
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """보호자 로그아웃"""
    service = GuardianAuthService(db)
    
    guardian_id = uuid.UUID(guardian["sub"])
    await service.logout(guardian_id)
    
    response = JSONResponse(content={"success": True, "message": "로그아웃되었습니다."})
    clear_guardian_cookies(response)
    
    return response


@router.post("/refresh-token")
async def guardian_refresh_token(
    guardian_refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    """토큰 갱신"""
    if not guardian_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="갱신 토큰이 필요합니다.",
        )
    
    service = GuardianAuthService(db)
    result = await service.refresh_token(guardian_refresh_token)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 갱신 토큰입니다.",
        )
    
    response = JSONResponse(content={"success": True})
    set_guardian_cookies(response, result["access_token"], result["refresh_token"])
    
    return response


@router.post("/change-password")
async def guardian_change_password(
    data: GuardianPasswordChangeRequest,
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """비밀번호 변경"""
    if data.new_password != data.new_password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="새 비밀번호가 일치하지 않습니다.",
        )
    
    service = GuardianAuthService(db)
    guardian_id = uuid.UUID(guardian["sub"])
    
    success = await service.change_password(
        guardian_id=guardian_id,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )
    
    # 토큰 쿠키 삭제 (재로그인 필요)
    response = JSONResponse(content={"success": True, "message": "비밀번호가 변경되었습니다. 다시 로그인해주세요."})
    clear_guardian_cookies(response)
    
    return response


# ============== FCM 토큰 API ==============

@router.post("/fcm-token", response_model=FCMTokenResponse)
async def register_fcm_token(
    data: FCMTokenRegisterRequest,
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """FCM 푸시 토큰 등록"""
    service = GuardianAuthService(db)
    guardian_id = uuid.UUID(guardian["sub"])
    
    success = await service.register_fcm_token(
        guardian_id=guardian_id,
        fcm_token=data.fcm_token,
    )
    
    return FCMTokenResponse(
        success=success,
        message="푸시 토큰이 등록되었습니다." if success else "토큰 등록에 실패했습니다.",
    )


# ============== 케이스 API ==============

@router.get("/cases", response_model=List[GuardianCaseResponse])
async def get_cases(
    status_filter: Optional[str] = Query(None, description="상태 필터 (open, all)"),
    days: int = Query(7, ge=1, le=90, description="조회 기간 (일)"),
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """케이스 목록 조회"""
    service = GuardianCaseService(db)
    care_user_id = uuid.UUID(guardian["care_user_id"])
    
    if status_filter == "open":
        cases = await service.get_open_cases(care_user_id)
    else:
        cases = await service.get_recent_cases(care_user_id, days=days)
    
    return [
        GuardianCaseResponse(
            id=case.id,
            case_number=case.case_number,
            status=case.status.value,
            max_severity=case.max_severity.value,
            current_escalation_stage=case.current_escalation_stage,
            opened_at=case.opened_at,
            resolved_at=case.resolved_at,
            care_user_name="",  # 프론트에서 대시보드에서 받은 이름 사용
            event_summary=f"케이스 #{case.case_number}",
            is_acknowledged=case.status.value == "acknowledged",
            acknowledged_at=None,
        )
        for case in cases
    ]


@router.get("/cases/{case_id}", response_model=GuardianCaseDetailResponse)
async def get_case_detail(
    case_id: uuid.UUID,
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """케이스 상세 조회"""
    service = GuardianCaseService(db)
    care_user_id = uuid.UUID(guardian["care_user_id"])
    
    case = await service.get_case_detail(case_id, care_user_id)
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    # 이벤트 정보
    events = [
        {
            "id": str(e.id),
            "event_type": e.event_type.value,
            "severity": e.severity.value,
            "occurred_at": e.occurred_at.isoformat(),
            "description": e.description,
        }
        for e in case.events
    ]
    
    # 액션 이력
    actions = [
        {
            "id": str(a.id),
            "action_type": a.action_type.value,
            "from_status": a.from_status,
            "to_status": a.to_status,
            "created_at": a.created_at.isoformat(),
            "note": a.note,
        }
        for a in case.actions
    ]
    
    return GuardianCaseDetailResponse(
        id=case.id,
        case_number=case.case_number,
        status=case.status.value,
        max_severity=case.max_severity.value,
        current_escalation_stage=case.current_escalation_stage,
        opened_at=case.opened_at,
        resolved_at=case.resolved_at,
        care_user_name="",
        event_summary=f"케이스 #{case.case_number}",
        is_acknowledged=case.status.value == "acknowledged",
        acknowledged_at=None,
        events=events,
        actions=actions,
        resolution_summary=case.resolution_summary,
    )


@router.post("/cases/{case_id}/ack", response_model=CaseAckResponse)
async def acknowledge_case(
    request: Request,
    case_id: uuid.UUID,
    data: CaseAckRequest,
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """케이스 ACK (확인) 처리
    
    보호자가 알림을 확인하고 대응 액션을 선택합니다.
    - acknowledged: 확인함
    - on_the_way: 가는 중
    - will_call: 전화할 예정
    - delegate: 다른 보호자에게 위임
    """
    service = GuardianCaseService(db)
    guardian_id = uuid.UUID(guardian["sub"])
    care_user_id = uuid.UUID(guardian["care_user_id"])
    ip_address = request.client.host if request.client else ""
    
    case = await service.acknowledge_case(
        case_id=case_id,
        guardian_id=guardian_id,
        care_user_id=care_user_id,
        note=data.note,
        action=data.action,
        ip_address=ip_address,
    )
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return CaseAckResponse(
        success=True,
        case_id=case.id,
        case_number=case.case_number,
        acknowledged_at=datetime.now(timezone.utc),
        message="케이스가 확인되었습니다.",
    )


# ============== 알림 API ==============

@router.get("/alerts", response_model=List[GuardianAlertResponse])
async def get_alerts(
    include_read: bool = Query(False, description="읽은 알림 포함 여부"),
    limit: int = Query(50, ge=1, le=100),
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """알림 목록 조회"""
    service = GuardianAlertService(db)
    guardian_id = uuid.UUID(guardian["sub"])
    
    alerts = await service.get_alerts(
        guardian_id=guardian_id,
        limit=limit,
        include_read=include_read,
    )
    
    return [
        GuardianAlertResponse(
            id=alert.id,
            case_number=f"CASE-{alert.case_id}",  # TODO: 실제 케이스 번호
            escalation_stage=alert.escalation_stage,
            status=alert.status.value,
            title=f"케이스 알림 (단계 {alert.escalation_stage})",
            message="돌봄 대상자에게 이벤트가 발생했습니다.",
            created_at=alert.created_at,
            is_read=alert.status.value in ["delivered", "acknowledged"],
            read_at=alert.acknowledged_at,
            care_user_name="",
            severity="warning",
        )
        for alert in alerts
    ]


@router.post("/alerts/read")
async def mark_alerts_read(
    data: AlertReadRequest,
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """알림 읽음 처리"""
    service = GuardianAlertService(db)
    guardian_id = uuid.UUID(guardian["sub"])
    
    count = await service.mark_as_read(data.alert_ids, guardian_id)
    
    return {"success": True, "read_count": count}


@router.get("/alerts/unread-count")
async def get_unread_count(
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """읽지 않은 알림 수 조회"""
    service = GuardianAlertService(db)
    guardian_id = uuid.UUID(guardian["sub"])
    
    count = await service.get_unread_count(guardian_id)
    
    return {"unread_count": count}


# ============== 대시보드 API ==============

@router.get("/dashboard")
async def get_dashboard(
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """보호자 대시보드
    
    돌봄 대상자 상태, 열린 케이스, 최근 알림을 한 번에 조회합니다.
    """
    service = GuardianDashboardService(db)
    guardian_id = uuid.UUID(guardian["sub"])
    care_user_id = uuid.UUID(guardian["care_user_id"])
    
    dashboard = await service.get_dashboard(guardian_id, care_user_id)
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="보호자 정보를 찾을 수 없습니다.",
        )
    
    # 케이스를 직렬화 가능한 형태로 변환
    open_cases = [
        {
            "id": str(case.id),
            "case_number": case.case_number,
            "status": case.status.value,
            "max_severity": case.max_severity.value,
            "current_escalation_stage": case.current_escalation_stage,
            "opened_at": case.opened_at.isoformat() if case.opened_at else None,
        }
        for case in dashboard["open_cases"]
    ]
    
    # 알림을 직렬화 가능한 형태로 변환
    recent_alerts = [
        {
            "id": str(alert.id),
            "escalation_stage": alert.escalation_stage,
            "status": alert.status.value,
            "scheduled_at": alert.scheduled_at.isoformat() if alert.scheduled_at else None,
        }
        for alert in dashboard["recent_alerts"]
    ]
    
    return {
        "guardian_id": str(dashboard["guardian_id"]),
        "guardian_name": dashboard["guardian_name"],
        "care_user": {
            "id": str(dashboard["care_user"]["id"]),
            "name": dashboard["care_user"]["name"],
            "is_active": dashboard["care_user"]["is_active"],
        },
        "open_cases_count": dashboard["open_cases_count"],
        "open_cases": open_cases,
        "recent_alerts": recent_alerts,
        "unread_alerts_count": dashboard["unread_alerts_count"],
    }


# ============== 프로필 API ==============

@router.get("/profile")
async def get_guardian_profile(
    guardian: dict = Depends(get_current_guardian),
    db: AsyncSession = Depends(get_db),
):
    """보호자 프로필 조회"""
    from app.models.user import Guardian
    from sqlalchemy import select
    from app.services.encryption import PIIEncryption
    
    guardian_id = uuid.UUID(guardian["sub"])
    
    result = await db.execute(
        select(Guardian).where(Guardian.id == guardian_id)
    )
    guardian_model = result.scalar_one_or_none()
    
    if not guardian_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="보호자 정보를 찾을 수 없습니다.",
        )
    
    pii = PIIEncryption()
    
    return {
        "id": str(guardian_model.id),
        "name": pii.decrypt(guardian_model.name_encrypted),
        "phone": pii.decrypt(guardian_model.phone_encrypted),
        "relationship_type": guardian_model.relationship_type,
        "priority": guardian_model.priority,
        "receive_notifications": guardian_model.receive_notifications,
        "app_enabled": guardian_model.app_enabled,
        "last_login_at": guardian_model.last_login_at.isoformat() if guardian_model.last_login_at else None,
    }
