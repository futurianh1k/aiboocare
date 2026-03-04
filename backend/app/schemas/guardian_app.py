"""
보호자 앱 관련 Pydantic 스키마

- 보호자 인증 (로그인/토큰)
- 케이스/알림 조회
- FCM 토큰 등록
- 케이스 ACK
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============== 보호자 인증 ==============

class GuardianLoginRequest(BaseModel):
    """보호자 로그인 요청"""
    phone: str = Field(..., description="전화번호")
    password: str = Field(..., min_length=4)


class GuardianLoginResponse(BaseModel):
    """보호자 로그인 응답"""
    success: bool
    guardian_id: uuid.UUID
    name: str
    care_user_name: str
    care_user_id: uuid.UUID
    message: str = "로그인 성공"


class GuardianRegisterRequest(BaseModel):
    """보호자 앱 등록 요청 (초기 비밀번호 설정)"""
    phone: str = Field(..., description="전화번호")
    verification_code: str = Field(..., min_length=6, max_length=6, description="인증 코드")
    password: str = Field(..., min_length=4, max_length=20)
    password_confirm: str = Field(..., min_length=4, max_length=20)


class GuardianTokenRefreshRequest(BaseModel):
    """토큰 갱신 요청"""
    refresh_token: str


class GuardianPasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str
    new_password: str = Field(..., min_length=4, max_length=20)
    new_password_confirm: str


# ============== FCM 토큰 ==============

class FCMTokenRegisterRequest(BaseModel):
    """FCM 토큰 등록 요청"""
    fcm_token: str = Field(..., min_length=10)
    device_type: str = Field("android", pattern="^(android|ios|web)$")


class FCMTokenResponse(BaseModel):
    """FCM 토큰 등록 응답"""
    success: bool
    message: str


# ============== 케이스 조회 ==============

class GuardianCaseResponse(BaseModel):
    """보호자용 케이스 응답"""
    id: uuid.UUID
    case_number: str
    status: str
    max_severity: str
    current_escalation_stage: int
    opened_at: datetime
    resolved_at: Optional[datetime]
    care_user_name: str
    event_summary: str
    is_acknowledged: bool
    acknowledged_at: Optional[datetime]


class GuardianCaseDetailResponse(GuardianCaseResponse):
    """보호자용 케이스 상세 응답"""
    events: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    resolution_summary: Optional[str]


class CaseAckRequest(BaseModel):
    """케이스 ACK 요청"""
    note: Optional[str] = Field(None, max_length=500, description="확인 메모")
    action: str = Field(
        "acknowledged",
        pattern="^(acknowledged|on_the_way|will_call|delegate)$",
        description="확인 액션",
    )


class CaseAckResponse(BaseModel):
    """케이스 ACK 응답"""
    success: bool
    case_id: uuid.UUID
    case_number: str
    acknowledged_at: datetime
    message: str


# ============== 알림 조회 ==============

class GuardianAlertResponse(BaseModel):
    """보호자용 알림 응답"""
    id: uuid.UUID
    case_number: str
    escalation_stage: int
    status: str
    title: str
    message: str
    created_at: datetime
    is_read: bool
    read_at: Optional[datetime]
    care_user_name: str
    severity: str


class AlertReadRequest(BaseModel):
    """알림 읽음 처리 요청"""
    alert_ids: List[uuid.UUID]


# ============== 돌봄 대상자 상태 ==============

class CareUserStatusResponse(BaseModel):
    """돌봄 대상자 상태 응답"""
    care_user_id: uuid.UUID
    name: str
    is_active: bool
    last_event_at: Optional[datetime]
    last_vital: Optional[Dict[str, Any]]
    open_cases_count: int
    device_status: str  # online, offline, unknown


class GuardianDashboardResponse(BaseModel):
    """보호자 대시보드 응답"""
    guardian_id: uuid.UUID
    guardian_name: str
    care_user: CareUserStatusResponse
    recent_alerts: List[GuardianAlertResponse]
    open_cases: List[GuardianCaseResponse]
    unread_alerts_count: int
