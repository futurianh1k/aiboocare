"""
이벤트 및 케이스 관련 Pydantic 스키마

- Measurement: 생체 데이터
- CareEvent: 감지된 이벤트
- CareCase: 케이스(티켓)
- CaseAction: 케이스 액션 이력
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============== Measurement 스키마 ==============

class MeasurementBase(BaseModel):
    """측정 데이터 기본 스키마"""
    measurement_type: str = Field(..., description="측정 타입 (blood_pressure, spo2 등)")
    recorded_at: datetime = Field(..., description="측정 시간")
    value: Optional[float] = Field(None, description="단일 수치값")
    value_json: Optional[Dict[str, Any]] = Field(None, description="복합 데이터")
    unit: Optional[str] = Field(None, description="단위")


class MeasurementCreate(MeasurementBase):
    """측정 데이터 생성 스키마"""
    user_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None


class MeasurementResponse(MeasurementBase):
    """측정 데이터 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: Optional[uuid.UUID]
    
    class Config:
        from_attributes = True


# ============== CareEvent 스키마 ==============

class EventBase(BaseModel):
    """이벤트 기본 스키마"""
    event_type: str = Field(..., description="이벤트 타입 (fall, inactivity 등)")
    severity: str = Field(default="warning", description="심각도")
    occurred_at: datetime = Field(..., description="발생 시간")
    event_data: Optional[Dict[str, Any]] = Field(None, description="이벤트 상세 데이터")
    description: Optional[str] = Field(None, description="설명")


class EventCreate(EventBase):
    """이벤트 생성 스키마 (디바이스에서 전송)"""
    user_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None


class EventCreateFromDevice(BaseModel):
    """디바이스에서 전송하는 이벤트 스키마"""
    serial_number: str = Field(..., description="기기 일련번호")
    event_type: str = Field(..., description="이벤트 타입")
    severity: Optional[str] = Field("warning", description="심각도")
    occurred_at: Optional[datetime] = Field(None, description="발생 시간 (없으면 현재)")
    event_data: Optional[Dict[str, Any]] = Field(None, description="이벤트 상세 데이터")
    description: Optional[str] = Field(None, description="설명")


class EventResponse(EventBase):
    """이벤트 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    device_id: Optional[uuid.UUID]
    case_id: Optional[uuid.UUID]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EventStatusUpdate(BaseModel):
    """이벤트 상태 업데이트 스키마"""
    status: str = Field(..., pattern="^(open|acknowledged|in_progress|resolved|false_alarm)$")
    note: Optional[str] = None


# ============== CareCase 스키마 ==============

class CaseBase(BaseModel):
    """케이스 기본 스키마"""
    case_number: str
    status: str
    max_severity: str
    current_escalation_stage: int


class CaseResponse(CaseBase):
    """케이스 응답 스키마"""
    id: uuid.UUID
    user_id: uuid.UUID
    assigned_operator_id: Optional[uuid.UUID]
    opened_at: datetime
    resolved_at: Optional[datetime]
    resolution_summary: Optional[str]
    created_at: datetime
    updated_at: datetime
    event_count: int = Field(0, description="연결된 이벤트 수")
    
    class Config:
        from_attributes = True


class CaseDetailResponse(CaseResponse):
    """케이스 상세 응답 스키마"""
    events: List[EventResponse] = []
    actions: List["CaseActionResponse"] = []
    
    class Config:
        from_attributes = True


class CaseStatusUpdate(BaseModel):
    """케이스 상태 업데이트 스키마"""
    status: str = Field(
        ...,
        pattern="^(open|escalating|pending_ack|acknowledged|resolved|closed|escalated_119)$",
    )
    note: Optional[str] = None
    resolution_summary: Optional[str] = None


class CaseAssign(BaseModel):
    """케이스 담당자 지정 스키마"""
    operator_id: uuid.UUID


# ============== CaseAction 스키마 ==============

class CaseActionBase(BaseModel):
    """케이스 액션 기본 스키마"""
    action_type: str
    note: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None


class CaseActionCreate(CaseActionBase):
    """케이스 액션 생성 스키마"""
    case_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    from_stage: Optional[int] = None
    to_stage: Optional[int] = None


class CaseActionResponse(CaseActionBase):
    """케이스 액션 응답 스키마"""
    id: uuid.UUID
    case_id: uuid.UUID
    actor_id: Optional[uuid.UUID]
    from_status: Optional[str]
    to_status: Optional[str]
    from_stage: Optional[int]
    to_stage: Optional[int]
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============== MQTT 이벤트 스키마 ==============

class MQTTEventPayload(BaseModel):
    """MQTT로 수신하는 이벤트 페이로드"""
    serial_number: str = Field(..., description="기기 일련번호")
    event_type: str = Field(..., description="이벤트 타입")
    severity: Optional[str] = Field("warning", description="심각도")
    timestamp: Optional[int] = Field(None, description="Unix timestamp (ms)")
    data: Optional[Dict[str, Any]] = Field(None, description="이벤트 데이터")
    
    class Config:
        extra = "allow"


class MQTTMeasurementPayload(BaseModel):
    """MQTT로 수신하는 측정 데이터 페이로드"""
    serial_number: str = Field(..., description="기기 일련번호")
    measurement_type: str = Field(..., description="측정 타입")
    timestamp: Optional[int] = Field(None, description="Unix timestamp (ms)")
    value: Optional[float] = Field(None, description="단일 수치값")
    data: Optional[Dict[str, Any]] = Field(None, description="복합 데이터")
    unit: Optional[str] = Field(None, description="단위")
    
    class Config:
        extra = "allow"


# Forward reference 해결
CaseDetailResponse.model_rebuild()
