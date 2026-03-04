"""
이벤트 및 시계열 데이터 모델

- Measurement: 생체/센서 시계열 데이터 (TimescaleDB 하이퍼테이블)
- CareEvent: 감지된 이벤트 (낙상, 무활동, 응급버튼 등)
- CareCase: 이벤트를 묶은 케이스(티켓)
- CaseAction: 케이스 상태 변경 이력 (Audit Log)

참고: PRD 섹션 4 & 5 - 이벤트 및 워크플로우 설계
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.device import CareDevice
    from app.models.user import AdminUser, CareUser


class MeasurementType(str, enum.Enum):
    """측정 데이터 종류"""
    BLOOD_PRESSURE = "blood_pressure"
    SPO2 = "spo2"
    HEART_RATE = "heart_rate"
    BODY_TEMPERATURE = "body_temperature"
    ACTIVITY = "activity"
    SLEEP = "sleep"
    RESPIRATION = "respiration"


class EventType(str, enum.Enum):
    """이벤트 종류"""
    FALL = "fall"                     # 낙상 감지
    INACTIVITY = "inactivity"         # 무활동 감지
    EMERGENCY_BUTTON = "emergency_button"  # 응급 버튼 누름
    EMERGENCY_VOICE = "emergency_voice"    # 응급 키워드 발화
    ABNORMAL_VITAL = "abnormal_vital"      # 비정상 생체 징후
    LOW_SPO2 = "low_spo2"             # 저산소증
    OUT_OF_RANGE = "out_of_range"     # 센서 범위 이탈


class EventSeverity(str, enum.Enum):
    """이벤트 심각도"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EventStatus(str, enum.Enum):
    """이벤트 상태"""
    OPEN = "open"           # 새로 생성됨
    ACKNOWLEDGED = "acknowledged"  # 확인됨
    IN_PROGRESS = "in_progress"    # 처리 중
    RESOLVED = "resolved"   # 해결됨
    FALSE_ALARM = "false_alarm"    # 오탐


class CaseStatus(str, enum.Enum):
    """케이스 상태"""
    OPEN = "open"
    ESCALATING = "escalating"  # 콜 트리 진행 중
    PENDING_ACK = "pending_ack"  # ACK 대기 중
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED_119 = "escalated_119"  # 119 연계됨


class ActionType(str, enum.Enum):
    """케이스 액션 종류"""
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    ESCALATED = "escalated"
    NOTIFICATION_SENT = "notification_sent"
    GUARDIAN_ACK = "guardian_ack"
    OPERATOR_ACK = "operator_ack"
    RESOLVED = "resolved"
    NOTE_ADDED = "note_added"
    ESCALATED_119 = "escalated_119"


class Measurement(Base, UUIDMixin):
    """생체/센서 시계열 데이터 테이블
    
    TimescaleDB 하이퍼테이블로 설정하여 시계열 쿼리 최적화
    
    Note: Alembic 마이그레이션에서 별도로 하이퍼테이블 변환 필요
    SELECT create_hypertable('measurement', 'recorded_at');
    """
    
    __tablename__ = "measurement"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_device.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    measurement_type: Mapped[MeasurementType] = mapped_column(
        Enum(MeasurementType),
        nullable=False,
    )
    
    # 기록 시간 (TimescaleDB 파티셔닝 키)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    
    # 측정값 (단일 값 또는 JSON)
    value: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        comment="단일 수치값 (예: SpO2 95.0)",
    )
    
    value_json: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="복합 데이터 (예: 혈압 {systolic: 120, diastolic: 80})",
    )
    
    # 단위
    unit: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="측정 단위 (%, mmHg, bpm 등)",
    )
    
    # 관계
    user: Mapped["CareUser"] = relationship("CareUser")
    device: Mapped[Optional["CareDevice"]] = relationship(
        "CareDevice",
        back_populates="measurements",
    )
    
    __table_args__ = (
        Index("ix_measurement_user_time", "user_id", "recorded_at"),
        Index("ix_measurement_type_time", "measurement_type", "recorded_at"),
    )


class CareEvent(Base, UUIDMixin, TimestampMixin):
    """감지된 이벤트 테이블
    
    낙상, 무활동, 응급버튼 등 감지된 사건을 기록합니다.
    """
    
    __tablename__ = "care_event"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_device.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_case.id", ondelete="SET NULL"),
        nullable=True,
        comment="연결된 케이스 ID (케이스 병합 시)",
    )
    
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType),
        nullable=False,
    )
    
    severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity),
        default=EventSeverity.WARNING,
        nullable=False,
    )
    
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus),
        default=EventStatus.OPEN,
        nullable=False,
    )
    
    # 이벤트 발생 시간
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    # 이벤트 상세 데이터
    event_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="이벤트 상세 정보 (센서값, 컨텍스트 등)",
    )
    
    # 설명
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 관계
    user: Mapped["CareUser"] = relationship(
        "CareUser",
        back_populates="events",
    )
    device: Mapped[Optional["CareDevice"]] = relationship(
        "CareDevice",
        back_populates="events",
    )
    case: Mapped[Optional["CareCase"]] = relationship(
        "CareCase",
        back_populates="events",
    )
    
    __table_args__ = (
        Index("ix_care_event_user_time", "user_id", "occurred_at"),
        Index("ix_care_event_status", "status"),
        Index("ix_care_event_type", "event_type"),
        Index("ix_care_event_case", "case_id"),
    )


class CareCase(Base, UUIDMixin, TimestampMixin):
    """케이스(티켓) 테이블
    
    이벤트를 처리 관점으로 묶은 단위입니다.
    30분 내 동일 사용자의 연속된 이벤트는 병합 처리됩니다.
    """
    
    __tablename__ = "care_case"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # 담당 운영자
    assigned_operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # 케이스 번호 (표시용)
    case_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="케이스 번호 (예: CASE-20260304-0001)",
    )
    
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus),
        default=CaseStatus.OPEN,
        nullable=False,
    )
    
    # 최고 심각도 (포함된 이벤트 중)
    max_severity: Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity),
        default=EventSeverity.WARNING,
        nullable=False,
    )
    
    # 콜 트리 현재 단계
    current_escalation_stage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="현재 에스컬레이션 단계 (0=시작 전)",
    )
    
    # 시간 정보
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 해결 요약
    resolution_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 관계
    user: Mapped["CareUser"] = relationship(
        "CareUser",
        back_populates="cases",
    )
    assigned_operator: Mapped[Optional["AdminUser"]] = relationship(
        "AdminUser",
        foreign_keys=[assigned_operator_id],
    )
    events: Mapped[list["CareEvent"]] = relationship(
        "CareEvent",
        back_populates="case",
    )
    actions: Mapped[list["CaseAction"]] = relationship(
        "CaseAction",
        back_populates="case",
        order_by="CaseAction.created_at",
    )
    
    __table_args__ = (
        Index("ix_care_case_user_status", "user_id", "status"),
        Index("ix_care_case_status", "status"),
        Index("ix_care_case_number", "case_number"),
    )


class CaseAction(Base, UUIDMixin, TimestampMixin):
    """케이스 액션 이력 테이블 (Audit Log)
    
    케이스의 모든 상태 변경, 알림 발송, ACK 등을 기록합니다.
    """
    
    __tablename__ = "case_action"
    
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_case.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # 액션 수행자 (운영자/시스템)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="수행자 ID (시스템 액션은 NULL)",
    )
    
    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType),
        nullable=False,
    )
    
    # 상태 변경 기록
    from_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    to_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    
    # 에스컬레이션 단계 변경
    from_stage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    to_stage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    
    # 액션 상세 데이터
    action_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="액션 상세 정보",
    )
    
    # 노트
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # IP 주소 (감사 로그용)
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    
    # 관계
    case: Mapped["CareCase"] = relationship(
        "CareCase",
        back_populates="actions",
    )
    actor: Mapped[Optional["AdminUser"]] = relationship("AdminUser")
    
    __table_args__ = (
        Index("ix_case_action_case_time", "case_id", "created_at"),
        Index("ix_case_action_type", "action_type"),
    )
