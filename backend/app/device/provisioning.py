"""
디바이스 프로비저닝 서비스

새 디바이스의 등록, 인증, 설정 배포를 관리합니다.

프로비저닝 플로우:
1. 디바이스가 시리얼 번호로 등록 요청
2. 서버가 디바이스 토큰 발급
3. 디바이스가 토큰으로 MQTT 연결
4. 서버가 초기 설정 전송

보안 규칙:
- 디바이스 토큰은 시리얼 번호 + 시크릿 해시로 생성
- 토큰은 주기적으로 갱신 (기본 30일)
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.device import CareDevice, DeviceModel, DeviceStatus


class DeviceProvisioningService:
    """디바이스 프로비저닝 서비스"""
    
    # 토큰 유효 기간 (일)
    TOKEN_VALIDITY_DAYS = 30
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_device(
        self,
        serial_number: str,
        device_model: str,
        firmware_version: str,
        hardware_spec: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """디바이스 등록
        
        새 디바이스를 시스템에 등록하고 인증 토큰을 발급합니다.
        
        Args:
            serial_number: 디바이스 시리얼 번호
            device_model: 디바이스 모델 (esp32_s3, raspberry_pi_4 등)
            firmware_version: 현재 펌웨어 버전
            hardware_spec: 하드웨어 사양 (센서 구성 등)
            
        Returns:
            등록 결과 (토큰, 설정 등) 또는 None
        """
        # 기존 디바이스 확인
        result = await self.db.execute(
            select(CareDevice).where(CareDevice.serial_number == serial_number)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 기존 디바이스 업데이트
            existing.firmware_version = firmware_version
            existing.status = DeviceStatus.ACTIVE
            existing.last_heartbeat_at = datetime.now(timezone.utc)
            if hardware_spec:
                existing.hardware_spec = hardware_spec
            
            await self.db.commit()
            await self.db.refresh(existing)
            
            device = existing
            logger.info(f"Device reconnected: {serial_number}")
        else:
            # 새 디바이스 등록
            try:
                model_enum = DeviceModel(device_model)
            except ValueError:
                model_enum = DeviceModel.CUSTOM
            
            device = CareDevice(
                id=uuid.uuid4(),
                serial_number=serial_number,
                device_model=model_enum,
                firmware_version=firmware_version,
                status=DeviceStatus.ACTIVE,
                hardware_spec=hardware_spec or {},
                last_heartbeat_at=datetime.now(timezone.utc),
            )
            
            self.db.add(device)
            await self.db.commit()
            await self.db.refresh(device)
            
            logger.info(f"New device registered: {serial_number}")
        
        # 토큰 생성
        token = self._generate_device_token(serial_number)
        
        # 초기 설정 생성
        config = self._get_default_config(device_model)
        
        return {
            "device_id": str(device.id),
            "serial_number": serial_number,
            "token": token,
            "token_expires_at": (
                datetime.now(timezone.utc) + timedelta(days=self.TOKEN_VALIDITY_DAYS)
            ).isoformat(),
            "mqtt_config": {
                "broker_host": settings.MQTT_BROKER_HOST,
                "broker_port": settings.MQTT_BROKER_PORT,
                "username": serial_number,
                "client_id": f"aiboo_{serial_number}",
            },
            "config": config,
        }
    
    async def verify_device_token(
        self,
        serial_number: str,
        token: str,
    ) -> bool:
        """디바이스 토큰 검증"""
        expected_token = self._generate_device_token(serial_number)
        return hmac.compare_digest(token, expected_token)
    
    async def refresh_device_token(
        self,
        serial_number: str,
    ) -> Optional[Dict[str, str]]:
        """디바이스 토큰 갱신"""
        result = await self.db.execute(
            select(CareDevice).where(
                CareDevice.serial_number == serial_number,
                CareDevice.deleted_at.is_(None),
            )
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return None
        
        token = self._generate_device_token(serial_number)
        
        return {
            "token": token,
            "expires_at": (
                datetime.now(timezone.utc) + timedelta(days=self.TOKEN_VALIDITY_DAYS)
            ).isoformat(),
        }
    
    async def assign_to_user(
        self,
        device_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """디바이스를 사용자에게 할당"""
        result = await self.db.execute(
            select(CareDevice).where(CareDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return False
        
        device.user_id = user_id
        await self.db.commit()
        
        logger.info(f"Device {device.serial_number} assigned to user {user_id}")
        return True
    
    async def unassign_device(self, device_id: uuid.UUID) -> bool:
        """디바이스 할당 해제"""
        result = await self.db.execute(
            select(CareDevice).where(CareDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return False
        
        device.user_id = None
        await self.db.commit()
        
        logger.info(f"Device {device.serial_number} unassigned")
        return True
    
    async def update_device_status(
        self,
        serial_number: str,
        status: DeviceStatus,
        firmware_version: Optional[str] = None,
    ) -> bool:
        """디바이스 상태 업데이트"""
        result = await self.db.execute(
            select(CareDevice).where(CareDevice.serial_number == serial_number)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return False
        
        device.status = status
        device.last_heartbeat_at = datetime.now(timezone.utc)
        
        if firmware_version:
            device.firmware_version = firmware_version
        
        await self.db.commit()
        return True
    
    async def get_device_config(
        self,
        serial_number: str,
    ) -> Optional[Dict[str, Any]]:
        """디바이스 설정 조회"""
        result = await self.db.execute(
            select(CareDevice).where(CareDevice.serial_number == serial_number)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return None
        
        config = self._get_default_config(device.device_model.value)
        
        # 디바이스별 커스텀 설정이 있으면 병합
        if device.hardware_spec and "config" in device.hardware_spec:
            config.update(device.hardware_spec["config"])
        
        return config
    
    def _generate_device_token(self, serial_number: str) -> str:
        """디바이스 토큰 생성
        
        시리얼 번호와 시크릿 키를 사용하여 HMAC 토큰 생성
        """
        message = f"{serial_number}:{settings.SECRET_KEY}"
        return hashlib.sha256(message.encode()).hexdigest()
    
    def _get_default_config(self, device_model: str) -> Dict[str, Any]:
        """기본 디바이스 설정"""
        base_config = {
            # 텔레메트리 설정
            "telemetry_interval_seconds": 30,  # 텔레메트리 전송 주기
            "heartbeat_interval_seconds": 60,  # 하트비트 주기
            
            # 이벤트 감지 설정
            "fall_detection_enabled": True,
            "fall_sensitivity": "medium",  # low, medium, high
            "inactivity_threshold_minutes": 30,
            "emergency_button_enabled": True,
            "emergency_voice_enabled": True,
            
            # 생체 모니터링 설정
            "vital_monitoring_enabled": True,
            "vital_interval_seconds": 60,
            "spo2_warning_threshold": 94,
            "spo2_critical_threshold": 90,
            
            # 오디오 설정
            "audio_enabled": True,
            "wake_word": "아이부",
            "tts_volume": 80,  # 0-100
            "stt_language": "ko-KR",
            
            # OTA 설정
            "ota_check_interval_hours": 24,
            "ota_auto_update": False,
            
            # 네트워크 설정
            "wifi_reconnect_interval_seconds": 30,
            "mqtt_keepalive_seconds": 60,
        }
        
        # 모델별 추가 설정
        if device_model in ["esp32_s3"]:
            base_config.update({
                "deep_sleep_enabled": True,
                "deep_sleep_idle_minutes": 5,
            })
        elif device_model in ["raspberry_pi_4", "raspberry_pi_5"]:
            base_config.update({
                "camera_enabled": True,
                "camera_resolution": "720p",
                "local_ai_enabled": True,
            })
        
        return base_config


class DeviceTokenManager:
    """디바이스 토큰 관리자
    
    MQTT 인증용 토큰 생성 및 검증을 관리합니다.
    """
    
    @staticmethod
    def generate_mqtt_password(serial_number: str, timestamp: int) -> str:
        """MQTT 인증용 비밀번호 생성
        
        디바이스가 MQTT 브로커에 연결할 때 사용합니다.
        """
        message = f"{serial_number}:{timestamp}:{settings.SECRET_KEY}"
        return hashlib.sha256(message.encode()).hexdigest()[:32]
    
    @staticmethod
    def verify_mqtt_password(
        serial_number: str,
        password: str,
        timestamp: int,
        max_age_seconds: int = 300,
    ) -> bool:
        """MQTT 비밀번호 검증
        
        Args:
            serial_number: 디바이스 시리얼 번호
            password: 제출된 비밀번호
            timestamp: 비밀번호 생성 시 타임스탬프
            max_age_seconds: 최대 유효 시간 (기본 5분)
        """
        # 타임스탬프 확인
        now = int(datetime.now(timezone.utc).timestamp())
        if abs(now - timestamp) > max_age_seconds:
            return False
        
        expected = DeviceTokenManager.generate_mqtt_password(serial_number, timestamp)
        return hmac.compare_digest(password, expected)
    
    @staticmethod
    def generate_provision_token() -> str:
        """프로비저닝 토큰 생성 (일회용)"""
        return secrets.token_urlsafe(32)
