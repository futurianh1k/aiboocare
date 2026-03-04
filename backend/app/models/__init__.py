"""
SQLAlchemy ORM 모델

모든 모델을 여기서 임포트하여 Alembic이 자동 감지할 수 있도록 합니다.
"""

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.models.device import CareDevice, DeviceModel, DeviceStatus
from app.models.event import (
    ActionType,
    CareCase,
    CaseAction,
    CaseStatus,
    CareEvent,
    EventSeverity,
    EventStatus,
    EventType,
    Measurement,
    MeasurementType,
)
from app.models.notification import (
    Alert,
    AlertStatus,
    NotificationChannel,
    NotificationDelivery,
)
from app.models.policy import (
    BundleStatus,
    EscalationPlan,
    PolicyBundle,
    PolicyRule,
    PolicyThreshold,
    RuleConditionType,
)
from app.models.user import (
    AdminUser,
    CareUser,
    CareUserPII,
    ConsentStatus,
    Guardian,
    UserRole,
)
from app.models.telemedicine import (
    MedicalRecordSync,
    PreTriage,
    SessionStatus,
    TelemedicineSession,
    TriageStatus,
    TriageUrgency,
)

__all__ = [
    # Base
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "SoftDeleteMixin",
    # User
    "CareUser",
    "CareUserPII",
    "Guardian",
    "AdminUser",
    "ConsentStatus",
    "UserRole",
    # Device
    "CareDevice",
    "DeviceStatus",
    "DeviceModel",
    # Event
    "Measurement",
    "MeasurementType",
    "CareEvent",
    "EventType",
    "EventSeverity",
    "EventStatus",
    "CareCase",
    "CaseStatus",
    "CaseAction",
    "ActionType",
    # Notification
    "Alert",
    "AlertStatus",
    "NotificationDelivery",
    "NotificationChannel",
    # Policy
    "PolicyBundle",
    "BundleStatus",
    "PolicyThreshold",
    "EscalationPlan",
    "PolicyRule",
    "RuleConditionType",
    # Telemedicine
    "PreTriage",
    "TriageUrgency",
    "TriageStatus",
    "TelemedicineSession",
    "SessionStatus",
    "MedicalRecordSync",
]
