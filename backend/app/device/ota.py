"""
OTA (Over-The-Air) 업데이트 서비스

디바이스 펌웨어를 원격으로 업데이트합니다.

플로우:
1. 새 펌웨어 버전 업로드
2. 디바이스에 업데이트 알림
3. 디바이스가 펌웨어 다운로드 및 설치
4. 설치 결과 보고

보안 규칙:
- 펌웨어 파일은 MD5 해시로 무결성 검증
- 디바이스 모델별 호환성 확인
"""

import hashlib
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.device import CareDevice, DeviceModel


class OTAStatus(str, Enum):
    """OTA 업데이트 상태"""
    PENDING = "pending"           # 대기 중
    DOWNLOADING = "downloading"   # 다운로드 중
    INSTALLING = "installing"     # 설치 중
    COMPLETED = "completed"       # 완료
    FAILED = "failed"             # 실패
    ROLLED_BACK = "rolled_back"   # 롤백됨


class FirmwareRelease:
    """펌웨어 릴리스 정보"""
    
    def __init__(
        self,
        version: str,
        device_model: str,
        download_url: str,
        md5_hash: str,
        size_bytes: int,
        release_notes: str = "",
        is_critical: bool = False,
        min_battery_level: int = 30,
    ):
        self.version = version
        self.device_model = device_model
        self.download_url = download_url
        self.md5_hash = md5_hash
        self.size_bytes = size_bytes
        self.release_notes = release_notes
        self.is_critical = is_critical
        self.min_battery_level = min_battery_level
        self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "device_model": self.device_model,
            "download_url": self.download_url,
            "md5_hash": self.md5_hash,
            "size_bytes": self.size_bytes,
            "release_notes": self.release_notes,
            "is_critical": self.is_critical,
            "min_battery_level": self.min_battery_level,
            "created_at": self.created_at.isoformat(),
        }


class OTAService:
    """OTA 업데이트 서비스"""
    
    # 펌웨어 저장 경로
    FIRMWARE_STORAGE_PATH = "/var/aiboo/firmware"
    
    # 버전별 펌웨어 정보 (실제로는 DB에 저장)
    _releases: Dict[str, Dict[str, FirmwareRelease]] = {}
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def check_update(
        self,
        serial_number: str,
        current_version: str,
    ) -> Optional[Dict[str, Any]]:
        """업데이트 확인
        
        Args:
            serial_number: 디바이스 시리얼 번호
            current_version: 현재 펌웨어 버전
            
        Returns:
            업데이트 정보 또는 None (최신 버전인 경우)
        """
        # 디바이스 조회
        result = await self.db.execute(
            select(CareDevice).where(CareDevice.serial_number == serial_number)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return None
        
        device_model = device.device_model.value
        
        # 해당 모델의 최신 릴리스 조회
        latest = self._get_latest_release(device_model)
        
        if not latest:
            return None
        
        # 버전 비교
        if self._compare_versions(current_version, latest.version) >= 0:
            # 이미 최신 버전
            return None
        
        logger.info(
            f"OTA update available: device={serial_number}, "
            f"current={current_version}, latest={latest.version}"
        )
        
        return {
            "update_available": True,
            "current_version": current_version,
            "new_version": latest.version,
            "download_url": latest.download_url,
            "md5_hash": latest.md5_hash,
            "size_bytes": latest.size_bytes,
            "release_notes": latest.release_notes,
            "is_critical": latest.is_critical,
            "min_battery_level": latest.min_battery_level,
        }
    
    async def register_firmware(
        self,
        version: str,
        device_model: str,
        file_path: str,
        release_notes: str = "",
        is_critical: bool = False,
    ) -> FirmwareRelease:
        """펌웨어 등록
        
        Args:
            version: 펌웨어 버전
            device_model: 대상 디바이스 모델
            file_path: 펌웨어 파일 경로
            release_notes: 릴리스 노트
            is_critical: 중요 업데이트 여부
            
        Returns:
            등록된 펌웨어 릴리스 정보
        """
        # MD5 해시 계산
        md5_hash = self._calculate_md5(file_path)
        
        # 파일 크기
        size_bytes = os.path.getsize(file_path)
        
        # 다운로드 URL 생성
        filename = os.path.basename(file_path)
        download_url = f"/api/v1/devices/firmware/{device_model}/{version}/{filename}"
        
        release = FirmwareRelease(
            version=version,
            device_model=device_model,
            download_url=download_url,
            md5_hash=md5_hash,
            size_bytes=size_bytes,
            release_notes=release_notes,
            is_critical=is_critical,
        )
        
        # 캐시에 저장
        if device_model not in self._releases:
            self._releases[device_model] = {}
        self._releases[device_model][version] = release
        
        logger.info(f"Firmware registered: model={device_model}, version={version}")
        
        return release
    
    async def report_update_status(
        self,
        serial_number: str,
        status: OTAStatus,
        new_version: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """업데이트 상태 보고
        
        디바이스가 업데이트 진행 상황을 보고합니다.
        """
        result = await self.db.execute(
            select(CareDevice).where(CareDevice.serial_number == serial_number)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return False
        
        if status == OTAStatus.COMPLETED and new_version:
            device.firmware_version = new_version
            logger.info(
                f"OTA completed: device={serial_number}, version={new_version}"
            )
        elif status == OTAStatus.FAILED:
            logger.error(
                f"OTA failed: device={serial_number}, error={error_message}"
            )
        
        await self.db.commit()
        return True
    
    async def get_firmware_list(
        self,
        device_model: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """펌웨어 목록 조회"""
        result = []
        
        for model, releases in self._releases.items():
            if device_model and model != device_model:
                continue
            
            for version, release in releases.items():
                result.append(release.to_dict())
        
        # 버전 내림차순 정렬
        result.sort(key=lambda x: x["version"], reverse=True)
        return result
    
    async def trigger_batch_update(
        self,
        device_model: str,
        target_version: str,
        force: bool = False,
    ) -> Dict[str, Any]:
        """일괄 업데이트 트리거
        
        특정 모델의 모든 디바이스에 업데이트 명령을 전송합니다.
        
        Args:
            device_model: 대상 디바이스 모델
            target_version: 대상 버전
            force: 강제 업데이트 여부
            
        Returns:
            트리거 결과
        """
        # 대상 디바이스 조회
        try:
            model_enum = DeviceModel(device_model)
        except ValueError:
            return {"success": False, "error": "Invalid device model"}
        
        result = await self.db.execute(
            select(CareDevice).where(
                CareDevice.device_model == model_enum,
                CareDevice.deleted_at.is_(None),
            )
        )
        devices = result.scalars().all()
        
        # 업데이트 대상 필터링
        targets = []
        for device in devices:
            if force or self._compare_versions(
                device.firmware_version or "0.0.0",
                target_version,
            ) < 0:
                targets.append(device.serial_number)
        
        logger.info(
            f"Batch OTA triggered: model={device_model}, "
            f"version={target_version}, targets={len(targets)}"
        )
        
        # TODO: 실제로 MQTT 명령 전송
        
        return {
            "success": True,
            "target_version": target_version,
            "total_devices": len(devices),
            "update_targets": len(targets),
            "target_serials": targets,
        }
    
    def _get_latest_release(self, device_model: str) -> Optional[FirmwareRelease]:
        """최신 릴리스 조회"""
        if device_model not in self._releases:
            return None
        
        releases = self._releases[device_model]
        if not releases:
            return None
        
        # 버전 내림차순 정렬하여 최신 반환
        latest_version = max(releases.keys(), key=self._version_key)
        return releases[latest_version]
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """버전 비교
        
        Returns:
            -1: v1 < v2
             0: v1 == v2
             1: v1 > v2
        """
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        # 길이 맞추기
        while len(v1_parts) < 3:
            v1_parts.append(0)
        while len(v2_parts) < 3:
            v2_parts.append(0)
        
        for i in range(3):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        return 0
    
    def _version_key(self, version: str) -> tuple:
        """버전 정렬 키"""
        parts = version.split('.')
        return tuple(int(x) for x in parts)
    
    def _calculate_md5(self, file_path: str) -> str:
        """파일 MD5 해시 계산"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
        return md5.hexdigest()
