"""
이벤트 및 케이스 API 엔드포인트

- 이벤트 조회/생성/상태 변경
- 케이스 조회/상태 변경/에스컬레이션/ACK

보안 규칙:
- 모든 액션은 Audit Log에 기록
- 케이스 상태 변경은 Operator 이상
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_operator
from app.schemas.event import (
    CaseActionResponse,
    CaseAssign,
    CaseDetailResponse,
    CaseResponse,
    CaseStatusUpdate,
    EventCreateFromDevice,
    EventResponse,
    EventStatusUpdate,
)
from app.services.event import CaseService, EventService

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


# ============== Event API ==============

@router.get("/events", response_model=List[EventResponse])
async def list_events(
    user_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None, pattern="^(open|acknowledged|in_progress|resolved|false_alarm)$"),
    event_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720, description="조회 기간 (시간)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """이벤트 목록 조회 (Operator 이상)"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    service = EventService(db)
    events = await service.list_events(
        user_id=user_id,
        status=status,
        event_type=event_type,
        since=since,
        skip=skip,
        limit=limit,
    )
    
    return [
        EventResponse(
            id=e.id,
            user_id=e.user_id,
            device_id=e.device_id,
            case_id=e.case_id,
            event_type=e.event_type.value,
            severity=e.severity.value,
            status=e.status.value,
            occurred_at=e.occurred_at,
            event_data=e.event_data,
            description=e.description,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )
        for e in events
    ]


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """이벤트 상세 조회 (Operator 이상)"""
    service = EventService(db)
    event = await service.get_event_by_id(event_id)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이벤트를 찾을 수 없습니다.",
        )
    
    return EventResponse(
        id=event.id,
        user_id=event.user_id,
        device_id=event.device_id,
        case_id=event.case_id,
        event_type=event.event_type.value,
        severity=event.severity.value,
        status=event.status.value,
        occurred_at=event.occurred_at,
        event_data=event.event_data,
        description=event.description,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.patch("/events/{event_id}/status", response_model=EventResponse)
async def update_event_status(
    request: Request,
    event_id: UUID,
    data: EventStatusUpdate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """이벤트 상태 변경 (Operator 이상)"""
    service = EventService(db)
    
    event = await service.update_event_status(
        event_id=event_id,
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이벤트를 찾을 수 없습니다.",
        )
    
    return EventResponse(
        id=event.id,
        user_id=event.user_id,
        device_id=event.device_id,
        case_id=event.case_id,
        event_type=event.event_type.value,
        severity=event.severity.value,
        status=event.status.value,
        occurred_at=event.occurred_at,
        event_data=event.event_data,
        description=event.description,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.post("/events/device", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event_from_device(
    data: EventCreateFromDevice,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
):
    """디바이스에서 이벤트 전송
    
    기기 일련번호로 기기를 찾고, 연결된 사용자에게 이벤트 생성.
    케이스 자동 생성/병합 수행.
    
    Note: 향후 X-Device-Token을 통한 기기 인증이 추가될 예정입니다.
    """
    # TODO: X-Device-Token 검증 로직 추가
    
    service = EventService(db)
    event, case = await service.create_event_from_device(data)
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이벤트를 생성할 수 없습니다. 기기가 등록되지 않았거나 사용자에게 할당되지 않았습니다.",
        )
    
    return EventResponse(
        id=event.id,
        user_id=event.user_id,
        device_id=event.device_id,
        case_id=event.case_id,
        event_type=event.event_type.value,
        severity=event.severity.value,
        status=event.status.value,
        occurred_at=event.occurred_at,
        event_data=event.event_data,
        description=event.description,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


# ============== Case API ==============

@router.get("/cases", response_model=List[CaseResponse])
async def list_cases(
    user_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(
        None,
        pattern="^(open|escalating|pending_ack|acknowledged|resolved|closed|escalated_119)$",
    ),
    assigned_operator_id: Optional[UUID] = Query(None),
    hours: int = Query(72, ge=1, le=720, description="조회 기간 (시간)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """케이스 목록 조회 (Operator 이상)"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    service = CaseService(db)
    cases = await service.list_cases(
        user_id=user_id,
        status=status,
        assigned_operator_id=assigned_operator_id,
        since=since,
        skip=skip,
        limit=limit,
    )
    
    return [
        CaseResponse(
            id=c.id,
            user_id=c.user_id,
            assigned_operator_id=c.assigned_operator_id,
            case_number=c.case_number,
            status=c.status.value,
            max_severity=c.max_severity.value,
            current_escalation_stage=c.current_escalation_stage,
            opened_at=c.opened_at,
            resolved_at=c.resolved_at,
            resolution_summary=c.resolution_summary,
            created_at=c.created_at,
            updated_at=c.updated_at,
            event_count=len(c.events) if hasattr(c, "events") and c.events else 0,
        )
        for c in cases
    ]


@router.get("/cases/open/count")
async def get_open_cases_count(
    user_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """열린 케이스 수 조회 (Operator 이상)"""
    service = CaseService(db)
    count = await service.get_open_cases_count(user_id)
    return {"count": count}


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case_detail(
    case_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """케이스 상세 조회 (이벤트/액션 포함, Operator 이상)"""
    service = CaseService(db)
    case = await service.get_case_by_id(
        case_id,
        include_events=True,
        include_actions=True,
    )
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return CaseDetailResponse(
        id=case.id,
        user_id=case.user_id,
        assigned_operator_id=case.assigned_operator_id,
        case_number=case.case_number,
        status=case.status.value,
        max_severity=case.max_severity.value,
        current_escalation_stage=case.current_escalation_stage,
        opened_at=case.opened_at,
        resolved_at=case.resolved_at,
        resolution_summary=case.resolution_summary,
        created_at=case.created_at,
        updated_at=case.updated_at,
        event_count=len(case.events),
        events=[
            EventResponse(
                id=e.id,
                user_id=e.user_id,
                device_id=e.device_id,
                case_id=e.case_id,
                event_type=e.event_type.value,
                severity=e.severity.value,
                status=e.status.value,
                occurred_at=e.occurred_at,
                event_data=e.event_data,
                description=e.description,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in case.events
        ],
        actions=[
            CaseActionResponse(
                id=a.id,
                case_id=a.case_id,
                actor_id=a.actor_id,
                action_type=a.action_type.value,
                from_status=a.from_status,
                to_status=a.to_status,
                from_stage=a.from_stage,
                to_stage=a.to_stage,
                note=a.note,
                action_data=a.action_data,
                ip_address=a.ip_address,
                created_at=a.created_at,
            )
            for a in case.actions
        ],
    )


@router.patch("/cases/{case_id}/status", response_model=CaseResponse)
async def update_case_status(
    request: Request,
    case_id: UUID,
    data: CaseStatusUpdate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """케이스 상태 변경 (Operator 이상)"""
    service = CaseService(db)
    
    case = await service.update_case_status(
        case_id=case_id,
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        assigned_operator_id=case.assigned_operator_id,
        case_number=case.case_number,
        status=case.status.value,
        max_severity=case.max_severity.value,
        current_escalation_stage=case.current_escalation_stage,
        opened_at=case.opened_at,
        resolved_at=case.resolved_at,
        resolution_summary=case.resolution_summary,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.post("/cases/{case_id}/assign", response_model=CaseResponse)
async def assign_case(
    request: Request,
    case_id: UUID,
    data: CaseAssign,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """케이스 담당자 지정 (Operator 이상)"""
    service = CaseService(db)
    
    case = await service.assign_operator(
        case_id=case_id,
        operator_id=data.operator_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        assigned_operator_id=case.assigned_operator_id,
        case_number=case.case_number,
        status=case.status.value,
        max_severity=case.max_severity.value,
        current_escalation_stage=case.current_escalation_stage,
        opened_at=case.opened_at,
        resolved_at=case.resolved_at,
        resolution_summary=case.resolution_summary,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.post("/cases/{case_id}/note", response_model=CaseActionResponse)
async def add_case_note(
    request: Request,
    case_id: UUID,
    note: str,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """케이스에 노트 추가 (Operator 이상)"""
    service = CaseService(db)
    
    action = await service.add_note(
        case_id=case_id,
        note=note,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return CaseActionResponse(
        id=action.id,
        case_id=action.case_id,
        actor_id=action.actor_id,
        action_type=action.action_type.value,
        from_status=action.from_status,
        to_status=action.to_status,
        from_stage=action.from_stage,
        to_stage=action.to_stage,
        note=action.note,
        action_data=action.action_data,
        ip_address=action.ip_address,
        created_at=action.created_at,
    )


@router.post("/cases/{case_id}/escalate", response_model=CaseResponse)
async def escalate_case(
    request: Request,
    case_id: UUID,
    to_stage: int,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """케이스 에스컬레이션 단계 변경 (Operator 이상)
    
    Args:
        to_stage: 에스컬레이션 단계 (1-5)
    """
    if to_stage < 1 or to_stage > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="에스컬레이션 단계는 1-5 사이여야 합니다.",
        )
    
    service = CaseService(db)
    
    case = await service.escalate(
        case_id=case_id,
        to_stage=to_stage,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        assigned_operator_id=case.assigned_operator_id,
        case_number=case.case_number,
        status=case.status.value,
        max_severity=case.max_severity.value,
        current_escalation_stage=case.current_escalation_stage,
        opened_at=case.opened_at,
        resolved_at=case.resolved_at,
        resolution_summary=case.resolution_summary,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.post("/cases/{case_id}/ack", response_model=CaseResponse)
async def acknowledge_case(
    request: Request,
    case_id: UUID,
    note: Optional[str] = None,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """케이스 ACK 처리 (Operator 이상)"""
    service = CaseService(db)
    
    case = await service.acknowledge(
        case_id=case_id,
        acknowledger_type="operator",
        acknowledger_id=current_user["user_id"],
        note=note,
        ip_address=get_client_ip(request),
    )
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return CaseResponse(
        id=case.id,
        user_id=case.user_id,
        assigned_operator_id=case.assigned_operator_id,
        case_number=case.case_number,
        status=case.status.value,
        max_severity=case.max_severity.value,
        current_escalation_stage=case.current_escalation_stage,
        opened_at=case.opened_at,
        resolved_at=case.resolved_at,
        resolution_summary=case.resolution_summary,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )
