"""
정책 룰 엔진 모델

- PolicyBundle: 정책 버전 관리 패키지
- PolicyThreshold: 센서 임계치 설정
- EscalationPlan: 콜 트리 단계별 설정
- PolicyRule: 복합 조건 룰 (JSON Schema 기반)

참고: PRD 섹션 4 - Policy Engine 설계
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class BundleStatus(str, enum.Enum):
    """정책 번들 상태"""
    DRAFT = "draft"           # 초안
    ACTIVE = "active"         # 활성 (적용 중)
    DEPRECATED = "deprecated" # 구버전
    ARCHIVED = "archived"     # 보관됨


class RuleConditionType(str, enum.Enum):
    """룰 조건 종류"""
    THRESHOLD = "threshold"       # 임계치 기반
    PATTERN = "pattern"           # 패턴 기반
    KEYWORD = "keyword"           # 키워드 기반
    COMPOSITE = "composite"       # 복합 조건


class PolicyBundle(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """정책 번들 테이블
    
    정책 설정을 버전 관리하는 패키지 단위입니다.
    """
    
    __tablename__ = "policy_bundle"
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="정책 번들 이름",
    )
    
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="버전 (예: 1.0.0)",
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    status: Mapped[BundleStatus] = mapped_column(
        Enum(BundleStatus),
        default=BundleStatus.DRAFT,
        nullable=False,
    )
    
    # 활성화 기간
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 생성자
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # 관계
    thresholds: Mapped[list["PolicyThreshold"]] = relationship(
        "PolicyThreshold",
        back_populates="bundle",
    )
    escalation_plans: Mapped[list["EscalationPlan"]] = relationship(
        "EscalationPlan",
        back_populates="bundle",
    )
    rules: Mapped[list["PolicyRule"]] = relationship(
        "PolicyRule",
        back_populates="bundle",
    )
    
    __table_args__ = (
        Index("ix_policy_bundle_status", "status"),
        Index("ix_policy_bundle_version", "name", "version", unique=True),
    )


class PolicyThreshold(Base, UUIDMixin, TimestampMixin):
    """센서 임계치 설정 테이블
    
    각 센서 타입별 경고/위험 임계값을 정의합니다.
    """
    
    __tablename__ = "policy_threshold"
    
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_bundle.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # 측정 타입 (MeasurementType과 매핑)
    measurement_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="측정 종류 (예: spo2, blood_pressure)",
    )
    
    # 임계값 설정
    warning_min: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="경고 하한값",
    )
    warning_max: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="경고 상한값",
    )
    critical_min: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="위험 하한값 (예: SpO2 < 90%)",
    )
    critical_max: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="위험 상한값",
    )
    
    # 지속 시간 조건 (초)
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="지속 시간 조건 (예: 90% 미만 60초 지속)",
    )
    
    # 단위
    unit: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
    )
    
    # 활성화 여부
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # 관계
    bundle: Mapped["PolicyBundle"] = relationship(
        "PolicyBundle",
        back_populates="thresholds",
    )
    
    __table_args__ = (
        Index("ix_policy_threshold_bundle_type", "bundle_id", "measurement_type"),
    )


class EscalationPlan(Base, UUIDMixin, TimestampMixin):
    """콜 트리 에스컬레이션 설정 테이블
    
    단계별 타임아웃 및 대상 설정
    
    참고: PRD 섹션 5 - 콜 트리 구조
    Stage 1: 보호자 1 (60초)
    Stage 2: 보호자 2 (90초)
    Stage 3: 요양보호사/기관 (120초)
    Stage 4: 관제센터/운영자 (60초)
    """
    
    __tablename__ = "escalation_plan"
    
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_bundle.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # 단계 번호 (1부터 시작)
    stage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    # 단계 이름
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="단계 이름 (예: '보호자 1차')",
    )
    
    # 대상 유형
    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="대상 유형 (guardian, caregiver, operator, emergency)",
    )
    
    # 타임아웃 (초)
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=60,
    )
    
    # 알림 채널 (JSON 배열)
    notification_channels: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=["push", "sms"],
        comment="사용할 알림 채널 목록",
    )
    
    # 다음 단계로 자동 에스컬레이션 여부
    auto_escalate: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # 활성화 여부
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # 관계
    bundle: Mapped["PolicyBundle"] = relationship(
        "PolicyBundle",
        back_populates="escalation_plans",
    )
    
    __table_args__ = (
        Index("ix_escalation_plan_bundle_stage", "bundle_id", "stage", unique=True),
    )


class PolicyRule(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """복합 조건 룰 테이블
    
    JSON Schema 기반으로 복잡한 조건과 액션을 정의합니다.
    
    예: 즉시 119 에스컬레이션 룰
    - 응급 키워드 발화
    - SpO2 < 90% 지속 + 호흡곤란
    - 낙상 후 60초 무동작
    """
    
    __tablename__ = "policy_rule"
    
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_bundle.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 룰 조건 종류
    condition_type: Mapped[RuleConditionType] = mapped_column(
        Enum(RuleConditionType),
        nullable=False,
    )
    
    # 조건 정의 (JSON Schema)
    rule_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="""조건 JSON 예시:
        {
            "type": "composite",
            "operator": "AND",
            "conditions": [
                {"type": "threshold", "measurement": "spo2", "operator": "<", "value": 90},
                {"type": "duration", "seconds": 60}
            ]
        }
        """,
    )
    
    # 액션 정의 (JSON)
    action_json: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="""액션 JSON 예시:
        {
            "type": "immediate_escalation",
            "target": "119",
            "skip_stages": true,
            "notify_all_guardians": true
        }
        """,
    )
    
    # 우선순위 (낮을수록 먼저 평가)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )
    
    # 활성화 여부
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # 즉시 119 에스컬레이션 여부 (Short-circuit)
    is_emergency_rule: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True면 중간 단계 생략하고 즉시 119 연계",
    )
    
    # 관계
    bundle: Mapped["PolicyBundle"] = relationship(
        "PolicyBundle",
        back_populates="rules",
    )
    
    __table_args__ = (
        Index("ix_policy_rule_bundle_priority", "bundle_id", "priority"),
        Index("ix_policy_rule_active", "is_active"),
        Index("ix_policy_rule_emergency", "is_emergency_rule"),
    )
