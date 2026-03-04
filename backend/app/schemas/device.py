"""
기기 관련 Pydantic 스키마

- CareDevice: 돌봄 디바이스
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DeviceStatus:
    """기기 상태 상수"""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class DeviceBase(BaseModel):
    """기기 기본 스키마"""
    serial_number: str = Field(..., min_length=1, max_length=50, description="일련번호")
    model: str = Field(default="v1", description="기기 모델")
    firmware_version: Optional[str] = Field(None, description="펌웨어 버전")


class DeviceCreate(DeviceBase):
    """기기 등록 스키마"""
    care_user_id: Optional[uuid.UUID] = Field(None, description="연결할 대상자 ID")


class DeviceUpdate(BaseModel):
    """기기 수정 스키마"""
    care_user_id: Optional[uuid.UUID] = None
    firmware_version: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(online|offline|maintenance)$")


class DeviceResponse(DeviceBase):
    """기기 응답 스키마"""
    id: uuid.UUID
    care_user_id: Optional[uuid.UUID]
    status: str
    last_heartbeat_at: Optional[datetime]
    installed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeviceStatusUpdate(BaseModel):
    """기기 상태 업데이트 스키마 (Heartbeat)"""
    battery_level: Optional[int] = Field(None, ge=0, le=100)
    wifi_rssi: Optional[int] = Field(None, description="WiFi 신호 강도 (dBm)")
    cpu_temp: Optional[float] = Field(None, description="CPU 온도 (°C)")


class DeviceHeartbeatResponse(BaseModel):
    """Heartbeat 응답 스키마"""
    ack: bool = True
    server_time: datetime
    config_version: Optional[str] = None
    ota_available: bool = False
