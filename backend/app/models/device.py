"""
기기(디바이스) 관련 모델

- CareDevice: IoT 디바이스 정보 (ESP32, Raspberry Pi 등)
- DeviceStatus: 기기 상태 열거형

참고: PRD 섹션 4 - 기기 테이블 설계
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
    from app.models.event import CareEvent, Measurement
    from app.models.user import CareUser


class DeviceStatus(str, enum.Enum):
    """기기 상태"""
    ACTIVE = "active"           # 정상 동작
    INACTIVE = "inactive"       # 비활성
    MAINTENANCE = "maintenance" # 유지보수 중
    ERROR = "error"             # 오류 상태
    OFFLINE = "offline"         # 오프라인


class DeviceModel(str, enum.Enum):
    """기기 모델 종류"""
    ESP32_S3 = "esp32_s3"
    RASPBERRY_PI_4 = "raspberry_pi_4"
    RASPBERRY_PI_5 = "raspberry_pi_5"
    CUSTOM = "custom"


class CareDevice(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """돌봄 기기 정보 테이블
    
    독거노인 가정에 설치되는 IoT 디바이스 정보를 관리합니다.
    """
    
    __tablename__ = "care_device"
    
    # 사용자 연결
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("care_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="연결된 대상자 ID",
    )
    
    # 기기 식별 정보
    serial_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="시리얼 번호",
    )
    
    device_model: Mapped[DeviceModel] = mapped_column(
        Enum(DeviceModel),
        nullable=False,
        comment="기기 모델",
    )
    
    firmware_version: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="펌웨어 버전",
    )
    
    # 상태 정보
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus),
        default=DeviceStatus.INACTIVE,
        nullable=False,
    )
    
    last_heartbeat_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="마지막 Heartbeat 시간",
    )
    
    # 하드웨어 스펙 (JSON)
    hardware_spec: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="하드웨어 사양 (센서 구성 등)",
    )
    
    # 설치 위치 정보 (암호화 불필요 - 개인정보 아님)
    installation_location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="설치 위치 설명",
    )
    
    # 메모
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    
    # 관계
    user: Mapped[Optional["CareUser"]] = relationship(
        "CareUser",
        back_populates="devices",
    )
    events: Mapped[list["CareEvent"]] = relationship(
        "CareEvent",
        back_populates="device",
    )
    measurements: Mapped[list["Measurement"]] = relationship(
        "Measurement",
        back_populates="device",
    )
    
    __table_args__ = (
        Index("ix_care_device_serial", "serial_number"),
        Index("ix_care_device_status", "status"),
        Index("ix_care_device_user", "user_id"),
    )
