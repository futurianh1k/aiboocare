"""
알림 관련 모델

- Alert: 알림 발송 로직/트리거
- NotificationDelivery: 채널별 전송 상태

참고: PRD 섹션 4 - 알림 테이블 설계
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.event import CareCase


class AlertStatus(str, enum.Enum):
    """알림 상태"""
    PENDING = "pending"       # 대기 중
    SENT = "sent"             # 발송됨
    DELIVERED = "delivered"   # 전달됨
    ACKNOWLEDGED = "acknowledged"  # 확인됨
    TIMEOUT = "timeout"       # 타임아웃
    FAILED = "failed"         # 실패
    CANCELLED = "cancelled"   # 취소됨


class NotificationChannel(str, enum.Enum):
    """알림 채널"""
    PUSH = "push"             # 앱 푸시
    SMS = "sms"               # SMS
    VOICE_CALL = "voice_call" # 음성 통화
    EMAIL = "email"           # 이메일
    KAKAO = "kakao"           # 카카오톡


class Alert(Base, UUIDMixin, TimestampMixin):
    """알림 트리거 테이블
    
    케이스 발생 시 콜 트리에 따라 생성되는 알림 단위입니다.
    """
    
    __tablename__ = "alert"
    
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_case.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # 콜 트리 단계
    escalation_stage: Mapped[int] = mapped_column(
        nullable=False,
        comment="에스컬레이션 단계 (1=보호자1, 2=보호자2, ...)",
    )
    
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus),
        default=AlertStatus.PENDING,
        nullable=False,
    )
    
    # 대상자 정보 (Guardian ID 또는 운영자 ID)
    target_guardian_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guardian.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # 타임아웃 설정
    timeout_seconds: Mapped[int] = mapped_column(
        nullable=False,
        default=60,
        comment="응답 대기 시간(초)",
    )
    
    # 시간 기록
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    timeout_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # ACK 데이터
    ack_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="확인 응답 데이터",
    )
    
    # 관계
    case: Mapped["CareCase"] = relationship("CareCase")
    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        "NotificationDelivery",
        back_populates="alert",
    )
    
    __table_args__ = (
        Index("ix_alert_case_stage", "case_id", "escalation_stage"),
        Index("ix_alert_status", "status"),
    )


class NotificationDelivery(Base, UUIDMixin, TimestampMixin):
    """알림 전송 상태 테이블
    
    각 채널별 전송 시도 및 결과를 기록합니다.
    """
    
    __tablename__ = "notification_delivery"
    
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alert.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel),
        nullable=False,
    )
    
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus),
        default=AlertStatus.PENDING,
        nullable=False,
    )
    
    # 수신자 정보 (마스킹된 형태로만 저장)
    recipient_masked: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="마스킹된 수신자 정보 (예: 010-****-1234)",
    )
    
    # 전송 시도 횟수
    attempt_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    
    # 시간 기록
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 외부 서비스 응답
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="외부 서비스 메시지 ID",
    )
    
    response_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="외부 서비스 응답 데이터",
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 관계
    alert: Mapped["Alert"] = relationship(
        "Alert",
        back_populates="deliveries",
    )
    
    __table_args__ = (
        Index("ix_notification_delivery_alert", "alert_id"),
        Index("ix_notification_delivery_channel_status", "channel", "status"),
    )
