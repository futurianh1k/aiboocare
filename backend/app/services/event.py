"""
이벤트 및 케이스 서비스

- 이벤트 생성/조회
- 케이스 생성/병합/상태 관리
- Rule Evaluator 연동
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import audit_logger, logger
from app.models.device import CareDevice
from app.models.event import (
    ActionType,
    CareCase,
    CareEvent,
    CaseAction,
    CaseStatus,
    EventSeverity,
    EventStatus,
    EventType,
    Measurement,
    MeasurementType,
)
from app.schemas.event import (
    CaseStatusUpdate,
    EventCreate,
    EventCreateFromDevice,
    EventStatusUpdate,
    MeasurementCreate,
)


class MeasurementService:
    """측정 데이터 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, data: MeasurementCreate) -> Measurement:
        """측정 데이터 저장"""
        measurement = Measurement(
            id=uuid.uuid4(),
            user_id=data.user_id,
            device_id=data.device_id,
            measurement_type=MeasurementType(data.measurement_type),
            recorded_at=data.recorded_at,
            value=data.value,
            value_json=data.value_json,
            unit=data.unit,
        )
        
        self.db.add(measurement)
        await self.db.commit()
        await self.db.refresh(measurement)
        
        return measurement
    
    async def get_recent(
        self,
        user_id: uuid.UUID,
        measurement_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[Measurement]:
        """최근 측정 데이터 조회"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = select(Measurement).where(
            Measurement.user_id == user_id,
            Measurement.recorded_at >= since,
        )
        
        if measurement_type:
            query = query.where(
                Measurement.measurement_type == MeasurementType(measurement_type)
            )
        
        query = query.order_by(Measurement.recorded_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class EventService:
    """이벤트 서비스"""
    
    # 케이스 병합 시간 윈도우 (분)
    CASE_MERGE_WINDOW_MINUTES = 30
    
    # 이벤트 그룹 (같은 그룹은 병합 대상)
    EVENT_GROUPS = {
        "safety": [EventType.FALL, EventType.INACTIVITY, EventType.EMERGENCY_BUTTON],
        "vital": [EventType.ABNORMAL_VITAL, EventType.LOW_SPO2],
        "emergency": [EventType.EMERGENCY_VOICE],
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_event(
        self,
        data: EventCreate,
        auto_create_case: bool = True,
    ) -> Tuple[CareEvent, Optional[CareCase]]:
        """이벤트 생성 및 케이스 연결/생성
        
        Args:
            data: 이벤트 데이터
            auto_create_case: 자동으로 케이스 생성/연결 여부
            
        Returns:
            (event, case) 튜플
        """
        event = CareEvent(
            id=uuid.uuid4(),
            user_id=data.user_id,
            device_id=data.device_id,
            event_type=EventType(data.event_type),
            severity=EventSeverity(data.severity),
            status=EventStatus.OPEN,
            occurred_at=data.occurred_at,
            event_data=data.event_data,
            description=data.description,
        )
        
        case = None
        if auto_create_case:
            case = await self._find_or_create_case(event)
            event.case_id = case.id
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        
        if case:
            await self.db.refresh(case)
        
        logger.info(
            f"Event created: type={event.event_type.value}, "
            f"severity={event.severity.value}, "
            f"user_id={event.user_id}, "
            f"case_id={event.case_id}"
        )
        
        return event, case
    
    async def create_event_from_device(
        self,
        data: EventCreateFromDevice,
    ) -> Tuple[Optional[CareEvent], Optional[CareCase]]:
        """디바이스에서 전송한 이벤트 생성
        
        일련번호로 기기를 찾고, 연결된 사용자에게 이벤트 생성
        """
        # 기기 조회
        result = await self.db.execute(
            select(CareDevice).where(
                CareDevice.serial_number == data.serial_number,
                CareDevice.deleted_at.is_(None),
            )
        )
        device = result.scalar_one_or_none()
        
        if not device:
            logger.warning(f"Event from unknown device: serial={data.serial_number}")
            return None, None
        
        if not device.user_id:
            logger.warning(f"Event from unassigned device: serial={data.serial_number}")
            return None, None
        
        event_create = EventCreate(
            user_id=device.user_id,
            device_id=device.id,
            event_type=data.event_type,
            severity=data.severity or "warning",
            occurred_at=data.occurred_at or datetime.now(timezone.utc),
            event_data=data.event_data,
            description=data.description,
        )
        
        return await self.create_event(event_create)
    
    async def _find_or_create_case(self, event: CareEvent) -> CareCase:
        """이벤트에 연결할 케이스 찾기 또는 생성
        
        케이스 병합 로직:
        1. 같은 사용자
        2. 같은 이벤트 그룹
        3. 30분 이내
        """
        # 이벤트 그룹 찾기
        event_group = self._get_event_group(event.event_type)
        group_event_types = self.EVENT_GROUPS.get(event_group, [event.event_type])
        
        # 병합 윈도우 계산
        window_start = event.occurred_at - timedelta(minutes=self.CASE_MERGE_WINDOW_MINUTES)
        
        # 기존 열린 케이스 찾기
        result = await self.db.execute(
            select(CareCase)
            .where(
                CareCase.user_id == event.user_id,
                CareCase.status.in_([CaseStatus.OPEN, CaseStatus.ESCALATING, CaseStatus.PENDING_ACK]),
                CareCase.opened_at >= window_start,
            )
            .order_by(CareCase.opened_at.desc())
            .limit(1)
        )
        existing_case = result.scalar_one_or_none()
        
        if existing_case:
            # 기존 케이스에 이벤트 연결
            # 최고 심각도 업데이트
            if self._severity_order(event.severity) > self._severity_order(existing_case.max_severity):
                existing_case.max_severity = event.severity
            
            await self.db.commit()
            
            logger.info(f"Event merged into existing case: {existing_case.case_number}")
            return existing_case
        
        # 새 케이스 생성
        case_number = await self._generate_case_number()
        
        new_case = CareCase(
            id=uuid.uuid4(),
            user_id=event.user_id,
            case_number=case_number,
            status=CaseStatus.OPEN,
            max_severity=event.severity,
            current_escalation_stage=0,
            opened_at=event.occurred_at,
        )
        
        self.db.add(new_case)
        
        # 케이스 생성 액션 기록
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=new_case.id,
            action_type=ActionType.CREATED,
            to_status=CaseStatus.OPEN.value,
            action_data={
                "trigger_event_type": event.event_type.value,
                "trigger_event_severity": event.severity.value,
            },
        )
        self.db.add(action)
        
        await self.db.commit()
        
        logger.info(f"New case created: {case_number}")
        return new_case
    
    def _get_event_group(self, event_type: EventType) -> str:
        """이벤트 타입의 그룹 반환"""
        for group, types in self.EVENT_GROUPS.items():
            if event_type in types:
                return group
        return "other"
    
    @staticmethod
    def _severity_order(severity: EventSeverity) -> int:
        """심각도 순서 반환 (높을수록 심각)"""
        order = {
            EventSeverity.INFO: 0,
            EventSeverity.WARNING: 1,
            EventSeverity.CRITICAL: 2,
            EventSeverity.EMERGENCY: 3,
        }
        return order.get(severity, 0)
    
    async def _generate_case_number(self) -> str:
        """케이스 번호 생성 (CASE-YYYYMMDD-NNNN)"""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"CASE-{today}-"
        
        # 오늘 생성된 케이스 수 조회
        result = await self.db.execute(
            select(func.count()).where(
                CareCase.case_number.like(f"{prefix}%")
            )
        )
        count = result.scalar() or 0
        
        return f"{prefix}{count + 1:04d}"
    
    async def get_event_by_id(self, event_id: uuid.UUID) -> Optional[CareEvent]:
        """이벤트 조회"""
        result = await self.db.execute(
            select(CareEvent).where(CareEvent.id == event_id)
        )
        return result.scalar_one_or_none()
    
    async def list_events(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CareEvent]:
        """이벤트 목록 조회"""
        query = select(CareEvent)
        
        if user_id:
            query = query.where(CareEvent.user_id == user_id)
        
        if status:
            query = query.where(CareEvent.status == EventStatus(status))
        
        if event_type:
            query = query.where(CareEvent.event_type == EventType(event_type))
        
        if since:
            query = query.where(CareEvent.occurred_at >= since)
        
        query = query.order_by(CareEvent.occurred_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_event_status(
        self,
        event_id: uuid.UUID,
        data: EventStatusUpdate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareEvent]:
        """이벤트 상태 업데이트"""
        event = await self.get_event_by_id(event_id)
        if not event:
            return None
        
        old_status = event.status
        event.status = EventStatus(data.status)
        
        await self.db.commit()
        await self.db.refresh(event)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="event_status_updated",
            resource_type="care_event",
            resource_id=str(event_id),
            ip_address=ip_address,
            details={
                "from_status": old_status.value,
                "to_status": data.status,
                "note": data.note,
            },
        )
        
        return event


class CaseService:
    """케이스 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_case_by_id(
        self,
        case_id: uuid.UUID,
        include_events: bool = False,
        include_actions: bool = False,
    ) -> Optional[CareCase]:
        """케이스 조회"""
        query = select(CareCase).where(CareCase.id == case_id)
        
        if include_events:
            query = query.options(selectinload(CareCase.events))
        
        if include_actions:
            query = query.options(selectinload(CareCase.actions))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_case_by_number(self, case_number: str) -> Optional[CareCase]:
        """케이스 번호로 조회"""
        result = await self.db.execute(
            select(CareCase).where(CareCase.case_number == case_number)
        )
        return result.scalar_one_or_none()
    
    async def list_cases(
        self,
        user_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        assigned_operator_id: Optional[uuid.UUID] = None,
        since: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CareCase]:
        """케이스 목록 조회"""
        query = select(CareCase)
        
        if user_id:
            query = query.where(CareCase.user_id == user_id)
        
        if status:
            query = query.where(CareCase.status == CaseStatus(status))
        
        if assigned_operator_id:
            query = query.where(CareCase.assigned_operator_id == assigned_operator_id)
        
        if since:
            query = query.where(CareCase.opened_at >= since)
        
        query = query.order_by(CareCase.opened_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_open_cases_count(self, user_id: Optional[uuid.UUID] = None) -> int:
        """열린 케이스 수 조회"""
        query = select(func.count()).select_from(CareCase).where(
            CareCase.status.in_([
                CaseStatus.OPEN,
                CaseStatus.ESCALATING,
                CaseStatus.PENDING_ACK,
            ])
        )
        
        if user_id:
            query = query.where(CareCase.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def update_case_status(
        self,
        case_id: uuid.UUID,
        data: CaseStatusUpdate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareCase]:
        """케이스 상태 업데이트"""
        case = await self.get_case_by_id(case_id)
        if not case:
            return None
        
        old_status = case.status
        new_status = CaseStatus(data.status)
        
        case.status = new_status
        
        if data.resolution_summary:
            case.resolution_summary = data.resolution_summary
        
        if new_status in [CaseStatus.RESOLVED, CaseStatus.CLOSED]:
            case.resolved_at = datetime.now(timezone.utc)
        
        # 액션 기록
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            actor_id=uuid.UUID(current_user_id) if current_user_id else None,
            action_type=ActionType.STATUS_CHANGED,
            from_status=old_status.value,
            to_status=new_status.value,
            note=data.note,
            ip_address=ip_address,
        )
        
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(
            f"Case status updated: {case.case_number} "
            f"{old_status.value} -> {new_status.value}"
        )
        
        return case
    
    async def assign_operator(
        self,
        case_id: uuid.UUID,
        operator_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareCase]:
        """케이스에 담당자 지정"""
        case = await self.get_case_by_id(case_id)
        if not case:
            return None
        
        old_operator_id = case.assigned_operator_id
        case.assigned_operator_id = operator_id
        
        # 액션 기록
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            actor_id=uuid.UUID(current_user_id) if current_user_id else None,
            action_type=ActionType.STATUS_CHANGED,
            action_data={
                "assigned_from": str(old_operator_id) if old_operator_id else None,
                "assigned_to": str(operator_id),
            },
            ip_address=ip_address,
        )
        
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(case)
        
        return case
    
    async def add_note(
        self,
        case_id: uuid.UUID,
        note: str,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CaseAction]:
        """케이스에 노트 추가"""
        case = await self.get_case_by_id(case_id)
        if not case:
            return None
        
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            actor_id=uuid.UUID(current_user_id) if current_user_id else None,
            action_type=ActionType.NOTE_ADDED,
            note=note,
            ip_address=ip_address,
        )
        
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        
        return action
    
    async def escalate(
        self,
        case_id: uuid.UUID,
        to_stage: int,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareCase]:
        """케이스 에스컬레이션 단계 변경"""
        case = await self.get_case_by_id(case_id)
        if not case:
            return None
        
        old_stage = case.current_escalation_stage
        case.current_escalation_stage = to_stage
        case.status = CaseStatus.ESCALATING
        
        # 액션 기록
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            actor_id=uuid.UUID(current_user_id) if current_user_id else None,
            action_type=ActionType.ESCALATED,
            from_stage=old_stage,
            to_stage=to_stage,
            ip_address=ip_address,
        )
        
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(
            f"Case escalated: {case.case_number} "
            f"stage {old_stage} -> {to_stage}"
        )
        
        return case
    
    async def acknowledge(
        self,
        case_id: uuid.UUID,
        acknowledger_type: str,  # "guardian" or "operator"
        acknowledger_id: str,
        note: Optional[str] = None,
        ip_address: str = "",
    ) -> Optional[CareCase]:
        """케이스 ACK 처리"""
        case = await self.get_case_by_id(case_id)
        if not case:
            return None
        
        case.status = CaseStatus.ACKNOWLEDGED
        
        action_type = ActionType.GUARDIAN_ACK if acknowledger_type == "guardian" else ActionType.OPERATOR_ACK
        
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            actor_id=uuid.UUID(acknowledger_id) if acknowledger_type == "operator" else None,
            action_type=action_type,
            from_status=case.status.value,
            to_status=CaseStatus.ACKNOWLEDGED.value,
            note=note,
            action_data={
                "acknowledger_type": acknowledger_type,
                "acknowledger_id": acknowledger_id,
            },
            ip_address=ip_address,
        )
        
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(
            f"Case acknowledged: {case.case_number} by {acknowledger_type}"
        )
        
        return case
