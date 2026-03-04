"""
Pydantic 스키마 모듈

API 요청/응답 검증용 스키마
"""

from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordChangeRequest,
    TokenRefreshResponse,
)
from app.schemas.device import (
    DeviceCreate,
    DeviceHeartbeatResponse,
    DeviceResponse,
    DeviceStatusUpdate,
    DeviceUpdate,
)
from app.schemas.event import (
    CaseActionResponse,
    CaseAssign,
    CaseDetailResponse,
    CaseResponse,
    CaseStatusUpdate,
    EventCreate,
    EventCreateFromDevice,
    EventResponse,
    EventStatusUpdate,
    MeasurementCreate,
    MeasurementResponse,
    MQTTEventPayload,
    MQTTMeasurementPayload,
)
from app.schemas.policy import (
    EscalationPlanCreate,
    EscalationPlanResponse,
    EscalationPlanUpdate,
    PolicyBundleCreate,
    PolicyBundleDetailResponse,
    PolicyBundleResponse,
    PolicyBundleUpdate,
    PolicyRuleCreate,
    PolicyRuleResponse,
    PolicyRuleUpdate,
    PolicyThresholdCreate,
    PolicyThresholdResponse,
    PolicyThresholdUpdate,
)
from app.schemas.user import (
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    CareUserCreate,
    CareUserDetailResponse,
    CareUserResponse,
    CareUserUpdate,
    GuardianCreate,
    GuardianDetailResponse,
    GuardianResponse,
    GuardianUpdate,
)

__all__ = [
    # Auth
    "LoginRequest",
    "LoginResponse",
    "TokenRefreshResponse",
    "CurrentUserResponse",
    "LogoutResponse",
    "PasswordChangeRequest",
    # AdminUser
    "AdminUserCreate",
    "AdminUserUpdate",
    "AdminUserResponse",
    # CareUser
    "CareUserCreate",
    "CareUserUpdate",
    "CareUserResponse",
    "CareUserDetailResponse",
    # Guardian
    "GuardianCreate",
    "GuardianUpdate",
    "GuardianResponse",
    "GuardianDetailResponse",
    # Device
    "DeviceCreate",
    "DeviceUpdate",
    "DeviceResponse",
    "DeviceStatusUpdate",
    "DeviceHeartbeatResponse",
    # Event
    "EventCreate",
    "EventCreateFromDevice",
    "EventResponse",
    "EventStatusUpdate",
    "MeasurementCreate",
    "MeasurementResponse",
    # Case
    "CaseResponse",
    "CaseDetailResponse",
    "CaseStatusUpdate",
    "CaseAssign",
    "CaseActionResponse",
    # MQTT
    "MQTTEventPayload",
    "MQTTMeasurementPayload",
    # Policy
    "PolicyBundleCreate",
    "PolicyBundleUpdate",
    "PolicyBundleResponse",
    "PolicyBundleDetailResponse",
    "PolicyThresholdCreate",
    "PolicyThresholdUpdate",
    "PolicyThresholdResponse",
    "EscalationPlanCreate",
    "EscalationPlanUpdate",
    "EscalationPlanResponse",
    "PolicyRuleCreate",
    "PolicyRuleUpdate",
    "PolicyRuleResponse",
]
