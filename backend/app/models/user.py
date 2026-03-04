"""
사용자 관련 모델

- CareUser: 대상자(독거노인) 기본 정보
- CareUserPII: 개인식별정보 (암호화 저장, 분리 테이블)
- Guardian: 보호자 정보
- AdminUser: 관리자/운영자 계정

참고: ISMS-P 가이드에 따라 PII는 별도 테이블에 암호화 저장
"""

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.device import CareDevice
    from app.models.event import CareCase, CareEvent


class ConsentStatus(str, enum.Enum):
    """개인정보 동의 상태"""
    PENDING = "pending"       # 동의 대기
    CONSENTED = "consented"   # 동의함
    WITHDRAWN = "withdrawn"   # 동의 철회


class UserRole(str, enum.Enum):
    """사용자 역할"""
    ADMIN = "admin"           # 시스템 관리자
    OPERATOR = "operator"     # 관제센터 운영자
    GUARDIAN = "guardian"     # 보호자
    CAREGIVER = "caregiver"   # 요양보호사


class CareUser(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """대상자(독거노인) 기본 정보 테이블
    
    PII(개인식별정보)는 care_user_pii 테이블에 암호화 저장됩니다.
    """
    
    __tablename__ = "care_user"
    
    # 고유 식별 코드 (내부용)
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        comment="내부 식별 코드",
    )
    
    # 동의 상태
    consent_status: Mapped[ConsentStatus] = mapped_column(
        Enum(ConsentStatus),
        default=ConsentStatus.PENDING,
        nullable=False,
    )
    consent_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # 서비스 상태
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # 메모 (민감정보 제외)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # 관계
    pii: Mapped["CareUserPII"] = relationship(
        "CareUserPII",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    devices: Mapped[list["CareDevice"]] = relationship(
        "CareDevice",
        back_populates="user",
    )
    events: Mapped[list["CareEvent"]] = relationship(
        "CareEvent",
        back_populates="user",
    )
    cases: Mapped[list["CareCase"]] = relationship(
        "CareCase",
        back_populates="user",
    )
    guardians: Mapped[list["Guardian"]] = relationship(
        "Guardian",
        back_populates="care_user",
    )
    
    __table_args__ = (
        Index("ix_care_user_code", "code"),
        Index("ix_care_user_active", "is_active"),
    )


class CareUserPII(Base, UUIDMixin, TimestampMixin):
    """대상자 개인식별정보 테이블 (암호화 저장)
    
    모든 PII 필드는 AES-256-GCM으로 암호화됩니다.
    복호화는 서비스 계층에서 필요할 때만 수행합니다.
    
    참고: ISMS-P 4.1 개인정보 암호화
    """
    
    __tablename__ = "care_user_pii"
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    
    # 암호화된 PII 필드들
    name_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="암호화된 이름",
    )
    
    phone_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="암호화된 전화번호",
    )
    
    address_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="암호화된 주소",
    )
    
    birth_date_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="암호화된 생년월일",
    )
    
    emergency_contact_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="암호화된 응급연락처",
    )
    
    # 관계
    user: Mapped["CareUser"] = relationship(
        "CareUser",
        back_populates="pii",
    )


class Guardian(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """보호자 정보 테이블
    
    보호자도 PII를 포함하므로 민감 필드는 암호화합니다.
    """
    
    __tablename__ = "guardian"
    
    care_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # 보호자 관계 (예: 자녀, 배우자, 친척)
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    # 콜 트리 우선순위 (1이 가장 높음)
    priority: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
    )
    
    # 암호화된 연락처 정보
    name_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    phone_encrypted: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    email_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 알림 수신 여부
    receive_notifications: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # 관계
    care_user: Mapped["CareUser"] = relationship(
        "CareUser",
        back_populates="guardians",
    )
    
    __table_args__ = (
        Index("ix_guardian_user_priority", "care_user_id", "priority"),
    )


class AdminUser(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """관리자/운영자 계정 테이블
    
    JWT 인증용 사용자 계정
    """
    
    __tablename__ = "admin_user"
    
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    
    # BCrypt 해싱된 비밀번호
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.OPERATOR,
        nullable=False,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    
    # Refresh Token 해시 (원본은 클라이언트만 보유)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )
    
    __table_args__ = (
        Index("ix_admin_user_email", "email"),
        Index("ix_admin_user_role", "role"),
    )
