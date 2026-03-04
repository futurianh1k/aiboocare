"""
기기 관리 API 엔드포인트

- 기기 CRUD
- Heartbeat 처리
- 기기 할당/해제

보안 규칙:
- 기기 등록/수정/삭제는 Operator 이상
- Heartbeat는 기기 인증 필요 (향후 구현)
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_operator
from app.schemas.device import (
    DeviceCreate,
    DeviceHeartbeatResponse,
    DeviceResponse,
    DeviceStatusUpdate,
    DeviceUpdate,
)
from app.services.device import DeviceService

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, pattern="^(online|offline|maintenance)$"),
    care_user_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """기기 목록 조회 (Operator 이상)"""
    service = DeviceService(db)
    devices = await service.list_all(
        skip=skip,
        limit=limit,
        status=status,
        care_user_id=care_user_id,
    )
    
    return [
        DeviceResponse(
            id=d.id,
            serial_number=d.serial_number,
            model=d.model,
            firmware_version=d.firmware_version,
            care_user_id=d.user_id,
            status=d.status.value,
            last_heartbeat_at=d.last_heartbeat_at,
            installed_at=d.installed_at,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in devices
    ]


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """기기 상세 조회 (Operator 이상)"""
    service = DeviceService(db)
    device = await service.get_by_id(device_id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기기를 찾을 수 없습니다.",
        )
    
    return DeviceResponse(
        id=device.id,
        serial_number=device.serial_number,
        model=device.model,
        firmware_version=device.firmware_version,
        care_user_id=device.user_id,
        status=device.status.value,
        last_heartbeat_at=device.last_heartbeat_at,
        installed_at=device.installed_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    request: Request,
    data: DeviceCreate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """기기 등록 (Operator 이상)"""
    service = DeviceService(db)
    
    try:
        device = await service.create(
            data=data,
            current_user_id=current_user["user_id"],
            ip_address=get_client_ip(request),
        )
        
        return DeviceResponse(
            id=device.id,
            serial_number=device.serial_number,
            model=device.model,
            firmware_version=device.firmware_version,
            care_user_id=device.user_id,
            status=device.status.value,
            last_heartbeat_at=device.last_heartbeat_at,
            installed_at=device.installed_at,
            created_at=device.created_at,
            updated_at=device.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    request: Request,
    device_id: UUID,
    data: DeviceUpdate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """기기 정보 수정 (Operator 이상)"""
    service = DeviceService(db)
    
    device = await service.update(
        device_id=device_id,
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기기를 찾을 수 없습니다.",
        )
    
    return DeviceResponse(
        id=device.id,
        serial_number=device.serial_number,
        model=device.model,
        firmware_version=device.firmware_version,
        care_user_id=device.user_id,
        status=device.status.value,
        last_heartbeat_at=device.last_heartbeat_at,
        installed_at=device.installed_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    request: Request,
    device_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """기기 삭제 (Operator 이상)"""
    service = DeviceService(db)
    
    success = await service.delete(
        device_id=device_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기기를 찾을 수 없습니다.",
        )


@router.post("/{device_id}/assign/{care_user_id}", response_model=DeviceResponse)
async def assign_device_to_user(
    request: Request,
    device_id: UUID,
    care_user_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """기기를 대상자에게 할당 (Operator 이상)"""
    service = DeviceService(db)
    
    device = await service.assign_to_user(
        device_id=device_id,
        care_user_id=care_user_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기기를 찾을 수 없습니다.",
        )
    
    return DeviceResponse(
        id=device.id,
        serial_number=device.serial_number,
        model=device.model,
        firmware_version=device.firmware_version,
        care_user_id=device.user_id,
        status=device.status.value,
        last_heartbeat_at=device.last_heartbeat_at,
        installed_at=device.installed_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


@router.post("/{device_id}/unassign", response_model=DeviceResponse)
async def unassign_device(
    request: Request,
    device_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """기기 할당 해제 (Operator 이상)"""
    service = DeviceService(db)
    
    device = await service.unassign_from_user(
        device_id=device_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="기기를 찾을 수 없습니다.",
        )
    
    return DeviceResponse(
        id=device.id,
        serial_number=device.serial_number,
        model=device.model,
        firmware_version=device.firmware_version,
        care_user_id=device.user_id,
        status=device.status.value,
        last_heartbeat_at=device.last_heartbeat_at,
        installed_at=device.installed_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


# ============== Device API (기기에서 호출) ==============

@router.post("/heartbeat/{serial_number}", response_model=DeviceHeartbeatResponse)
async def device_heartbeat(
    serial_number: str,
    data: DeviceStatusUpdate,
    x_device_token: Optional[str] = Header(None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
):
    """기기 Heartbeat
    
    기기에서 주기적으로 호출하여 상태를 전송합니다.
    
    Note: 향후 X-Device-Token을 통한 기기 인증이 추가될 예정입니다.
    """
    # TODO: X-Device-Token 검증 로직 추가
    
    service = DeviceService(db)
    device = await service.process_heartbeat(serial_number, data)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="등록되지 않은 기기입니다.",
        )
    
    return DeviceHeartbeatResponse(
        ack=True,
        server_time=datetime.now(timezone.utc),
        config_version=None,  # TODO: 설정 버전 관리
        ota_available=False,  # TODO: OTA 업데이트 확인
    )
