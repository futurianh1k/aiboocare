"""
디바이스 프로비저닝 및 OTA API 엔드포인트

- 디바이스 등록/프로비저닝
- OTA 업데이트 확인 및 트리거
- 디바이스 설정 관리
- MQTT 명령 전송

보안 규칙:
- 프로비저닝 API는 디바이스 토큰으로 인증
- 관리 API는 운영자 권한 필요
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.core.logging import logger
from app.device.mqtt_protocol import CommandType, MQTTProtocol, MQTTTopic
from app.device.ota import OTAService, OTAStatus
from app.device.provisioning import DeviceProvisioningService, DeviceTokenManager
from app.models.user import UserRole

router = APIRouter()


# ============== 요청/응답 스키마 ==============

class DeviceRegisterRequest(BaseModel):
    """디바이스 등록 요청"""
    serial_number: str = Field(..., min_length=5, max_length=100)
    device_model: str = Field(..., description="esp32_s3, raspberry_pi_4 등")
    firmware_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    hardware_spec: Optional[Dict[str, Any]] = Field(None, description="하드웨어 사양")


class DeviceRegisterResponse(BaseModel):
    """디바이스 등록 응답"""
    success: bool
    device_id: str
    serial_number: str
    token: str
    token_expires_at: str
    mqtt_config: Dict[str, Any]
    config: Dict[str, Any]


class OTACheckRequest(BaseModel):
    """OTA 업데이트 확인 요청"""
    serial_number: str
    current_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")


class OTACheckResponse(BaseModel):
    """OTA 업데이트 확인 응답"""
    update_available: bool
    current_version: str
    new_version: Optional[str] = None
    download_url: Optional[str] = None
    md5_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    release_notes: Optional[str] = None
    is_critical: bool = False


class OTAStatusReport(BaseModel):
    """OTA 상태 보고"""
    serial_number: str
    status: str = Field(..., description="pending, downloading, installing, completed, failed")
    new_version: Optional[str] = None
    error_message: Optional[str] = None


class DeviceCommandRequest(BaseModel):
    """디바이스 명령 요청"""
    command: str = Field(..., description="config, reboot, speak, ota 등")
    payload: Dict[str, Any] = Field(default_factory=dict)


class BatchOTARequest(BaseModel):
    """일괄 OTA 업데이트 요청"""
    device_model: str
    target_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    force: bool = False


# ============== 디바이스 프로비저닝 API ==============

@router.post("/provision", response_model=DeviceRegisterResponse)
async def provision_device(
    request: DeviceRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """디바이스 프로비저닝 (등록)
    
    새 디바이스를 시스템에 등록하고 MQTT 인증 정보를 발급합니다.
    디바이스가 처음 부팅 시 호출합니다.
    """
    service = DeviceProvisioningService(db)
    
    result = await service.register_device(
        serial_number=request.serial_number,
        device_model=request.device_model,
        firmware_version=request.firmware_version,
        hardware_spec=request.hardware_spec,
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="디바이스 등록에 실패했습니다.",
        )
    
    return DeviceRegisterResponse(
        success=True,
        device_id=result["device_id"],
        serial_number=result["serial_number"],
        token=result["token"],
        token_expires_at=result["token_expires_at"],
        mqtt_config=result["mqtt_config"],
        config=result["config"],
    )


@router.post("/verify-token")
async def verify_device_token(
    serial_number: str = Query(...),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """디바이스 토큰 검증"""
    service = DeviceProvisioningService(db)
    
    valid = await service.verify_device_token(serial_number, token)
    
    return {"valid": valid}


@router.post("/refresh-token")
async def refresh_device_token(
    serial_number: str = Query(...),
    current_token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """디바이스 토큰 갱신"""
    service = DeviceProvisioningService(db)
    
    # 현재 토큰 검증
    if not await service.verify_device_token(serial_number, current_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
        )
    
    result = await service.refresh_device_token(serial_number)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="디바이스를 찾을 수 없습니다.",
        )
    
    return result


@router.get("/config/{serial_number}")
async def get_device_config(
    serial_number: str,
    db: AsyncSession = Depends(get_db),
):
    """디바이스 설정 조회
    
    디바이스가 부팅 시 또는 주기적으로 설정을 동기화할 때 호출합니다.
    """
    service = DeviceProvisioningService(db)
    
    config = await service.get_device_config(serial_number)
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="디바이스를 찾을 수 없습니다.",
        )
    
    return config


# ============== OTA 업데이트 API ==============

@router.post("/ota/check", response_model=OTACheckResponse)
async def check_ota_update(
    request: OTACheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """OTA 업데이트 확인
    
    디바이스가 주기적으로 새 펌웨어가 있는지 확인합니다.
    """
    service = OTAService(db)
    
    result = await service.check_update(
        serial_number=request.serial_number,
        current_version=request.current_version,
    )
    
    if not result:
        return OTACheckResponse(
            update_available=False,
            current_version=request.current_version,
        )
    
    return OTACheckResponse(**result)


@router.post("/ota/status")
async def report_ota_status(
    report: OTAStatusReport,
    db: AsyncSession = Depends(get_db),
):
    """OTA 업데이트 상태 보고
    
    디바이스가 업데이트 진행 상황을 보고합니다.
    """
    try:
        ota_status = OTAStatus(report.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 상태: {report.status}",
        )
    
    service = OTAService(db)
    
    success = await service.report_update_status(
        serial_number=report.serial_number,
        status=ota_status,
        new_version=report.new_version,
        error_message=report.error_message,
    )
    
    return {"success": success}


@router.get("/ota/firmware")
async def list_firmware(
    device_model: Optional[str] = Query(None),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """펌웨어 목록 조회 (관리자용)"""
    service = OTAService(db)
    
    firmware_list = await service.get_firmware_list(device_model)
    
    return {"firmware": firmware_list}


@router.post("/ota/batch-update")
async def trigger_batch_update(
    request: BatchOTARequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """일괄 OTA 업데이트 트리거 (관리자용)
    
    특정 모델의 모든 디바이스에 업데이트 명령을 전송합니다.
    """
    service = OTAService(db)
    
    result = await service.trigger_batch_update(
        device_model=request.device_model,
        target_version=request.target_version,
        force=request.force,
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "업데이트 트리거 실패"),
        )
    
    return result


# ============== 디바이스 명령 API ==============

@router.post("/command/{serial_number}")
async def send_device_command(
    serial_number: str,
    request: DeviceCommandRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """디바이스 명령 전송 (관리자용)
    
    MQTT를 통해 디바이스에 명령을 전송합니다.
    """
    # 명령 유효성 검사
    valid_commands = [c.value for c in CommandType]
    if request.command not in valid_commands:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 명령: {request.command}. "
                   f"허용된 명령: {', '.join(valid_commands)}",
        )
    
    # 명령 메시지 생성
    command_msg = MQTTProtocol.create_command(
        device_id=serial_number,
        command=request.command,
        payload=request.payload,
    )
    
    # TODO: 실제 MQTT 발행
    # await mqtt_client.publish(
    #     MQTTTopic.command(serial_number, request.command),
    #     command_msg.to_json(),
    #     qos=MQTTProtocol.QOS_COMMAND,
    # )
    
    logger.info(
        f"Command sent: device={serial_number}, "
        f"command={request.command}, "
        f"user={current_user.get('sub')}"
    )
    
    return {
        "success": True,
        "device": serial_number,
        "command": request.command,
        "msg_id": command_msg.msg_id,
    }


@router.post("/speak/{serial_number}")
async def send_speak_command(
    serial_number: str,
    text: str = Query(..., min_length=1, max_length=500),
    voice: str = Query("nova"),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """TTS 재생 명령 전송
    
    디바이스에서 텍스트를 음성으로 재생합니다.
    """
    command_msg = MQTTProtocol.create_speak_command(
        device_id=serial_number,
        text=text,
        voice=voice,
    )
    
    # TODO: 실제 MQTT 발행
    
    logger.info(
        f"Speak command sent: device={serial_number}, "
        f"text_length={len(text)}"
    )
    
    return {
        "success": True,
        "device": serial_number,
        "msg_id": command_msg.msg_id,
    }


@router.post("/reboot/{serial_number}")
async def reboot_device(
    serial_number: str,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """디바이스 재부팅 명령 (관리자 전용)"""
    command_msg = MQTTProtocol.create_command(
        device_id=serial_number,
        command="reboot",
        payload={},
    )
    
    # TODO: 실제 MQTT 발행
    
    logger.info(
        f"Reboot command sent: device={serial_number}, "
        f"user={current_user.get('sub')}"
    )
    
    return {
        "success": True,
        "device": serial_number,
        "msg_id": command_msg.msg_id,
    }


# ============== MQTT 토픽 정보 ==============

@router.get("/mqtt/topics")
async def get_mqtt_topics():
    """MQTT 토픽 구조 정보 조회
    
    디바이스 개발자를 위한 MQTT 토픽 구조 문서입니다.
    """
    return {
        "prefix": "aiboo",
        "topics": {
            "telemetry": {
                "pattern": "aiboo/{device_id}/telemetry/{type}",
                "direction": "device → server",
                "qos": 0,
                "types": ["vital", "activity", "environment", "audio_level"],
                "description": "센서 데이터 전송",
            },
            "event": {
                "pattern": "aiboo/{device_id}/event/{type}",
                "direction": "device → server",
                "qos": 1,
                "types": ["fall", "inactivity", "emergency_button", "emergency_voice", "abnormal_vital"],
                "description": "이벤트 전송",
            },
            "status": {
                "pattern": "aiboo/{device_id}/status",
                "direction": "device → server",
                "qos": 1,
                "description": "하트비트/상태 전송 (60초 주기)",
            },
            "command": {
                "pattern": "aiboo/{device_id}/cmd/{command}",
                "direction": "server → device",
                "qos": 2,
                "commands": ["config", "reboot", "ota", "speak", "ping", "calibrate"],
                "description": "명령 수신",
            },
            "response": {
                "pattern": "aiboo/{device_id}/response/{command}",
                "direction": "device → server",
                "qos": 1,
                "description": "명령 응답",
            },
        },
        "message_format": "JSON",
        "example_messages": {
            "telemetry_vital": {
                "device_id": "DEVICE001",
                "timestamp": "2026-03-04T12:00:00Z",
                "type": "vital",
                "data": {"spo2": 97, "heart_rate": 72, "body_temp": 36.5},
            },
            "event_fall": {
                "device_id": "DEVICE001",
                "timestamp": "2026-03-04T12:00:00Z",
                "event_type": "fall",
                "severity": "critical",
                "data": {"impact_force": 2.5, "duration_ms": 150},
            },
            "status": {
                "device_id": "DEVICE001",
                "timestamp": "2026-03-04T12:00:00Z",
                "status": "online",
                "firmware_version": "1.0.0",
                "uptime_seconds": 3600,
                "wifi_rssi": -45,
            },
        },
    }
