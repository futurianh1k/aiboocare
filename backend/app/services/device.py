"""
기기 관리 서비스

- 기기 CRUD
- Heartbeat 처리
- 상태 관리
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import audit_logger, logger
from app.models.device import CareDevice, DeviceStatus
from app.schemas.device import DeviceCreate, DeviceStatusUpdate, DeviceUpdate


class DeviceService:
    """기기 관리 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, device_id: uuid.UUID) -> Optional[CareDevice]:
        """ID로 기기 조회"""
        result = await self.db.execute(
            select(CareDevice).where(
                CareDevice.id == device_id,
                CareDevice.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_serial(self, serial_number: str) -> Optional[CareDevice]:
        """일련번호로 기기 조회"""
        result = await self.db.execute(
            select(CareDevice).where(
                CareDevice.serial_number == serial_number,
                CareDevice.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        care_user_id: Optional[uuid.UUID] = None,
    ) -> List[CareDevice]:
        """기기 목록 조회"""
        query = select(CareDevice).where(CareDevice.deleted_at.is_(None))
        
        if status:
            query = query.where(CareDevice.status == DeviceStatus(status))
        
        if care_user_id:
            query = query.where(CareDevice.user_id == care_user_id)
        
        query = query.offset(skip).limit(limit).order_by(CareDevice.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(
        self,
        data: DeviceCreate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> CareDevice:
        """기기 등록"""
        # 일련번호 중복 검사
        existing = await self.get_by_serial(data.serial_number)
        if existing:
            raise ValueError("이미 등록된 일련번호입니다.")
        
        device = CareDevice(
            id=uuid.uuid4(),
            serial_number=data.serial_number,
            model=data.model,
            firmware_version=data.firmware_version,
            user_id=data.care_user_id,
            status=DeviceStatus.OFFLINE,
        )
        
        if data.care_user_id:
            device.installed_at = datetime.now(timezone.utc)
        
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="device_created",
            resource_type="care_device",
            resource_id=str(device.id),
            ip_address=ip_address,
            details={"serial_number": data.serial_number},
        )
        
        return device
    
    async def update(
        self,
        device_id: uuid.UUID,
        data: DeviceUpdate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareDevice]:
        """기기 정보 수정"""
        device = await self.get_by_id(device_id)
        if not device:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "status":
                setattr(device, field, DeviceStatus(value))
            elif field == "care_user_id":
                device.user_id = value
                if value and not device.installed_at:
                    device.installed_at = datetime.now(timezone.utc)
            else:
                setattr(device, field, value)
        
        await self.db.commit()
        await self.db.refresh(device)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="device_updated",
            resource_type="care_device",
            resource_id=str(device.id),
            ip_address=ip_address,
        )
        
        return device
    
    async def delete(
        self,
        device_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> bool:
        """기기 삭제 (소프트 삭제)"""
        device = await self.get_by_id(device_id)
        if not device:
            return False
        
        device.soft_delete()
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="device_deleted",
            resource_type="care_device",
            resource_id=str(device.id),
            ip_address=ip_address,
        )
        
        return True
    
    async def process_heartbeat(
        self,
        serial_number: str,
        status_data: DeviceStatusUpdate,
    ) -> Optional[CareDevice]:
        """Heartbeat 처리
        
        기기에서 주기적으로 전송하는 상태 정보를 업데이트합니다.
        """
        device = await self.get_by_serial(serial_number)
        if not device:
            logger.warning(f"Heartbeat from unknown device: serial={serial_number}")
            return None
        
        # 상태 업데이트
        device.status = DeviceStatus.ONLINE
        device.last_heartbeat_at = datetime.now(timezone.utc)
        
        # 추가 상태 정보 (메타데이터로 저장 가능)
        # TODO: 별도 테이블 또는 JSONB 컬럼으로 관리
        
        await self.db.commit()
        await self.db.refresh(device)
        
        return device
    
    async def check_offline_devices(
        self,
        timeout_minutes: int = 5,
    ) -> List[CareDevice]:
        """오프라인 기기 확인
        
        마지막 Heartbeat가 timeout_minutes 이상 지난 기기를 오프라인으로 표시합니다.
        """
        from datetime import timedelta
        
        threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        
        result = await self.db.execute(
            select(CareDevice).where(
                CareDevice.deleted_at.is_(None),
                CareDevice.status == DeviceStatus.ONLINE,
                CareDevice.last_heartbeat_at < threshold,
            )
        )
        
        offline_devices = list(result.scalars().all())
        
        for device in offline_devices:
            device.status = DeviceStatus.OFFLINE
            
            audit_logger.log_action(
                user_id="system",
                action="device_offline_detected",
                resource_type="care_device",
                resource_id=str(device.id),
                details={"last_heartbeat": str(device.last_heartbeat_at)},
            )
        
        await self.db.commit()
        
        return offline_devices
    
    async def assign_to_user(
        self,
        device_id: uuid.UUID,
        care_user_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareDevice]:
        """기기를 대상자에게 할당"""
        device = await self.get_by_id(device_id)
        if not device:
            return None
        
        device.user_id = care_user_id
        device.installed_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(device)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="device_assigned",
            resource_type="care_device",
            resource_id=str(device.id),
            ip_address=ip_address,
            details={"care_user_id": str(care_user_id)},
        )
        
        return device
    
    async def unassign_from_user(
        self,
        device_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareDevice]:
        """기기 할당 해제"""
        device = await self.get_by_id(device_id)
        if not device:
            return None
        
        old_user_id = device.user_id
        device.user_id = None
        
        await self.db.commit()
        await self.db.refresh(device)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="device_unassigned",
            resource_type="care_device",
            resource_id=str(device.id),
            ip_address=ip_address,
            details={"previous_care_user_id": str(old_user_id) if old_user_id else None},
        )
        
        return device
