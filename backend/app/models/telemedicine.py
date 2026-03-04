"""
원격진료 연계 모델

- PreTriage: 사전분류 정보 (의료기관 전달용)
- TelemedicineSession: 원격진료 세션
- MedicalRecord: 의료 기록 동기화

참고: FHIR R4 표준을 기반으로 설계
https://www.hl7.org/fhir/
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.event import CareCase
    from app.models.user import AdminUser, CareUser


class TriageUrgency(str, enum.Enum):
    """응급도 분류 (KTAS 기반)"""
    LEVEL_1 = "level_1"  # 즉시 (소생)
    LEVEL_2 = "level_2"  # 긴급 (응급)
    LEVEL_3 = "level_3"  # 준긴급 (긴급)
    LEVEL_4 = "level_4"  # 비긴급 (준긴급)
    LEVEL_5 = "level_5"  # 비응급 (비긴급)


class TriageStatus(str, enum.Enum):
    """Pre-triage 상태"""
    DRAFT = "draft"            # 작성 중
    PENDING = "pending"        # 전송 대기
    SENT = "sent"              # 의료기관 전송됨
    RECEIVED = "received"      # 의료기관 확인
    SCHEDULED = "scheduled"    # 진료 예약됨
    COMPLETED = "completed"    # 진료 완료
    CANCELLED = "cancelled"    # 취소됨


class SessionStatus(str, enum.Enum):
    """원격진료 세션 상태"""
    WAITING = "waiting"        # 대기 중
    IN_PROGRESS = "in_progress"  # 진행 중
    COMPLETED = "completed"    # 완료
    CANCELLED = "cancelled"    # 취소
    NO_SHOW = "no_show"        # 불참


class PreTriage(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """사전분류(Pre-triage) 정보 테이블
    
    이벤트 발생 시 AI가 자동으로 생성하는 사전분류 정보입니다.
    의료기관에 전달하여 원격진료 또는 방문진료의 기초 자료로 활용됩니다.
    
    FHIR 리소스:
    - Patient: 환자 정보
    - Observation: 생체 데이터
    - Condition: 증상/상태
    """
    
    __tablename__ = "pre_triage"
    
    care_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_case.id", ondelete="SET NULL"),
        nullable=True,
        comment="연관 케이스 ID",
    )
    
    # 생성자 (AI 또는 운영자)
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # ============== 분류 정보 ==============
    urgency: Mapped[TriageUrgency] = mapped_column(
        Enum(TriageUrgency),
        default=TriageUrgency.LEVEL_4,
        nullable=False,
        comment="응급도 (KTAS 기반)",
    )
    
    status: Mapped[TriageStatus] = mapped_column(
        Enum(TriageStatus),
        default=TriageStatus.DRAFT,
        nullable=False,
    )
    
    # ============== 주호소 (Chief Complaint) ==============
    chief_complaint: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="주호소 (환자가 호소하는 주된 증상)",
    )
    
    chief_complaint_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="ICD-10 코드",
    )
    
    # ============== 현재 병력 (History of Present Illness) ==============
    history_present_illness: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="현재 병력 (발생 시점, 경과, 동반 증상 등)",
    )
    
    # ============== 생체 징후 (Vital Signs) ==============
    vital_signs: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="""생체 징후 예시:
        {
            "blood_pressure": {"systolic": 120, "diastolic": 80},
            "heart_rate": 72,
            "respiratory_rate": 16,
            "body_temperature": 36.5,
            "spo2": 97,
            "measured_at": "2026-03-04T12:00:00Z"
        }
        """,
    )
    
    # ============== 증상 (Symptoms) ==============
    symptoms: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="""증상 목록 예시:
        [
            {"code": "R06.0", "display": "호흡곤란", "severity": "moderate"},
            {"code": "R00.0", "display": "빈맥", "severity": "mild"}
        ]
        """,
    )
    
    # ============== 과거력 (Past Medical History) ==============
    past_medical_history: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="과거 병력, 수술력, 복용 약물 등",
    )
    
    # ============== AI 분석 결과 ==============
    ai_assessment: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="""AI 분석 결과 예시:
        {
            "risk_level": "high",
            "confidence": 0.85,
            "suggested_actions": ["vital_check", "call_guardian"],
            "differential_diagnosis": ["respiratory_infection", "cardiac_issue"]
        }
        """,
    )
    
    # ============== 의료기관 전송 정보 ==============
    sent_to_clinic_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="전송된 의료기관 ID",
    )
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # FHIR Bundle ID (의료기관 연동용)
    fhir_bundle_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="FHIR Bundle ID",
    )
    
    # 관계
    care_user: Mapped["CareUser"] = relationship("CareUser")
    case: Mapped[Optional["CareCase"]] = relationship("CareCase")
    created_by: Mapped[Optional["AdminUser"]] = relationship("AdminUser")
    
    __table_args__ = (
        Index("ix_pre_triage_user_status", "care_user_id", "status"),
        Index("ix_pre_triage_urgency", "urgency"),
        Index("ix_pre_triage_case", "case_id"),
    )


class TelemedicineSession(Base, UUIDMixin, TimestampMixin):
    """원격진료 세션 테이블
    
    화상 진료, 전화 진료 등의 세션 정보를 관리합니다.
    """
    
    __tablename__ = "telemedicine_session"
    
    care_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    pre_triage_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pre_triage.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # 의료기관 정보
    clinic_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="의료기관 ID",
    )
    
    clinic_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    
    doctor_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    
    # 세션 정보
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus),
        default=SessionStatus.WAITING,
        nullable=False,
    )
    
    session_type: Mapped[str] = mapped_column(
        String(50),
        default="video",
        nullable=False,
        comment="세션 종류 (video, phone, chat)",
    )
    
    # 예약 시간
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    
    # 실제 진행 시간
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # 세션 URL/정보
    session_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="화상 진료 URL",
    )
    
    session_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="세션 관련 추가 정보",
    )
    
    # 진료 결과
    diagnosis: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    prescription: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="처방 정보",
    )
    
    follow_up_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 관계
    care_user: Mapped["CareUser"] = relationship("CareUser")
    pre_triage: Mapped[Optional["PreTriage"]] = relationship("PreTriage")
    
    __table_args__ = (
        Index("ix_telemedicine_session_user", "care_user_id"),
        Index("ix_telemedicine_session_status", "status"),
        Index("ix_telemedicine_session_scheduled", "scheduled_at"),
    )


class MedicalRecordSync(Base, UUIDMixin, TimestampMixin):
    """의료 기록 동기화 테이블
    
    외부 EMR 시스템과의 동기화 기록을 관리합니다.
    """
    
    __tablename__ = "medical_record_sync"
    
    care_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # 외부 시스템 정보
    external_system: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="외부 시스템 ID (emr_hospital_a, fhir_server 등)",
    )
    
    external_patient_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="외부 시스템의 환자 ID",
    )
    
    # 동기화 정보
    sync_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="동기화 종류 (push, pull, bidirectional)",
    )
    
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    sync_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        comment="동기화 상태 (pending, syncing, completed, failed)",
    )
    
    # 동기화된 데이터 요약
    synced_resources: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="""동기화된 리소스 예시:
        {
            "Patient": "2026-03-04T12:00:00Z",
            "Observation": "2026-03-04T12:00:00Z",
            "Condition": "2026-03-04T11:00:00Z"
        }
        """,
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 관계
    care_user: Mapped["CareUser"] = relationship("CareUser")
    
    __table_args__ = (
        Index("ix_medical_record_sync_user", "care_user_id"),
        Index("ix_medical_record_sync_system", "external_system"),
    )
