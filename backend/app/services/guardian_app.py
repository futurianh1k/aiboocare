"""
보호자 앱 서비스

- 보호자 인증 (로그인/토큰)
- FCM 토큰 관리
- 케이스/알림 조회
- 케이스 ACK
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import audit_logger, logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
    get_password_hash,
)
from app.models.event import ActionType, CareCase, CaseAction, CaseStatus
from app.models.notification import Alert, AlertStatus
from app.models.user import CareUser, Guardian
from app.services.encryption import PIIEncryption


class GuardianAuthService:
    """보호자 인증 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pii_encryption = PIIEncryption()
    
    async def login(
        self,
        phone: str,
        password: str,
        ip_address: str = "",
    ) -> Optional[Dict[str, Any]]:
        """보호자 로그인
        
        전화번호와 비밀번호로 인증합니다.
        
        Args:
            phone: 전화번호
            password: 비밀번호
            ip_address: 클라이언트 IP
            
        Returns:
            로그인 결과 또는 None
        """
        # 전화번호로 보호자 찾기 (암호화된 전화번호와 비교)
        guardian = await self._find_guardian_by_phone(phone)
        
        if not guardian:
            logger.warning(f"Guardian login failed: phone not found")
            return None
        
        if not guardian.password_hash:
            logger.warning(f"Guardian login failed: password not set")
            return None
        
        if not guardian.app_enabled:
            logger.warning(f"Guardian login failed: app not enabled")
            return None
        
        if not verify_password(password, guardian.password_hash):
            logger.warning(f"Guardian login failed: invalid password")
            return None
        
        # 토큰 생성
        access_token = create_access_token(
            data={
                "sub": str(guardian.id),
                "type": "guardian",
                "care_user_id": str(guardian.care_user_id),
            }
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(guardian.id), "type": "guardian"}
        )
        
        # Refresh Token 해시 저장
        guardian.refresh_token_hash = hash_refresh_token(refresh_token)
        guardian.last_login_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        # 돌봄 대상자 이름 조회
        care_user_name = await self._get_care_user_name(guardian.care_user_id)
        guardian_name = self.pii_encryption.decrypt(guardian.name_encrypted)
        
        audit_logger.log_action(
            user_id=str(guardian.id),
            action="guardian_login",
            resource_type="guardian",
            resource_id=str(guardian.id),
            ip_address=ip_address,
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "guardian_id": guardian.id,
            "guardian_name": guardian_name,
            "care_user_id": guardian.care_user_id,
            "care_user_name": care_user_name,
        }
    
    async def refresh_token(
        self,
        refresh_token: str,
    ) -> Optional[Dict[str, str]]:
        """토큰 갱신"""
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "guardian":
            return None
        
        guardian_id = payload.get("sub")
        if not guardian_id:
            return None
        
        # 보호자 조회
        result = await self.db.execute(
            select(Guardian).where(
                Guardian.id == uuid.UUID(guardian_id),
                Guardian.deleted_at.is_(None),
            )
        )
        guardian = result.scalar_one_or_none()
        
        if not guardian or not guardian.app_enabled:
            return None
        
        # Refresh Token 해시 확인
        if guardian.refresh_token_hash != hash_refresh_token(refresh_token):
            return None
        
        # 새 토큰 생성
        new_access_token = create_access_token(
            data={
                "sub": str(guardian.id),
                "type": "guardian",
                "care_user_id": str(guardian.care_user_id),
            }
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": str(guardian.id), "type": "guardian"}
        )
        
        # 새 Refresh Token 해시 저장
        guardian.refresh_token_hash = hash_refresh_token(new_refresh_token)
        await self.db.commit()
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
        }
    
    async def logout(self, guardian_id: uuid.UUID) -> bool:
        """로그아웃 (Refresh Token 무효화)"""
        result = await self.db.execute(
            select(Guardian).where(Guardian.id == guardian_id)
        )
        guardian = result.scalar_one_or_none()
        
        if not guardian:
            return False
        
        guardian.refresh_token_hash = None
        await self.db.commit()
        
        return True
    
    async def register_app(
        self,
        guardian_id: uuid.UUID,
        password: str,
    ) -> bool:
        """보호자 앱 등록 (비밀번호 설정)"""
        result = await self.db.execute(
            select(Guardian).where(
                Guardian.id == guardian_id,
                Guardian.deleted_at.is_(None),
            )
        )
        guardian = result.scalar_one_or_none()
        
        if not guardian:
            return False
        
        guardian.password_hash = get_password_hash(password)
        guardian.app_enabled = True
        
        await self.db.commit()
        
        logger.info(f"Guardian app registered: id={guardian_id}")
        
        return True
    
    async def change_password(
        self,
        guardian_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> bool:
        """비밀번호 변경"""
        result = await self.db.execute(
            select(Guardian).where(Guardian.id == guardian_id)
        )
        guardian = result.scalar_one_or_none()
        
        if not guardian or not guardian.password_hash:
            return False
        
        if not verify_password(current_password, guardian.password_hash):
            return False
        
        guardian.password_hash = get_password_hash(new_password)
        guardian.refresh_token_hash = None  # 기존 토큰 무효화
        
        await self.db.commit()
        
        return True
    
    async def register_fcm_token(
        self,
        guardian_id: uuid.UUID,
        fcm_token: str,
    ) -> bool:
        """FCM 토큰 등록"""
        result = await self.db.execute(
            select(Guardian).where(Guardian.id == guardian_id)
        )
        guardian = result.scalar_one_or_none()
        
        if not guardian:
            return False
        
        guardian.fcm_token = fcm_token
        await self.db.commit()
        
        logger.info(f"FCM token registered: guardian_id={guardian_id}")
        
        return True
    
    async def _find_guardian_by_phone(self, phone: str) -> Optional[Guardian]:
        """전화번호로 보호자 찾기"""
        # 모든 활성 보호자 조회 후 전화번호 비교
        result = await self.db.execute(
            select(Guardian).where(
                Guardian.deleted_at.is_(None),
                Guardian.app_enabled == True,
            )
        )
        guardians = result.scalars().all()
        
        for guardian in guardians:
            decrypted_phone = self.pii_encryption.decrypt(guardian.phone_encrypted)
            # 전화번호 정규화 후 비교
            if self._normalize_phone(decrypted_phone) == self._normalize_phone(phone):
                return guardian
        
        return None
    
    def _normalize_phone(self, phone: str) -> str:
        """전화번호 정규화 (숫자만)"""
        return "".join(filter(str.isdigit, phone))
    
    async def _get_care_user_name(self, care_user_id: uuid.UUID) -> str:
        """돌봄 대상자 이름 조회"""
        result = await self.db.execute(
            select(CareUser).where(CareUser.id == care_user_id)
            .options(selectinload(CareUser.pii))
        )
        care_user = result.scalar_one_or_none()
        
        if care_user and care_user.pii:
            return self.pii_encryption.decrypt(care_user.pii.name_encrypted)
        
        return "알 수 없음"


class GuardianCaseService:
    """보호자용 케이스 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pii_encryption = PIIEncryption()
    
    async def get_open_cases(
        self,
        care_user_id: uuid.UUID,
    ) -> List[CareCase]:
        """열린 케이스 목록 조회"""
        result = await self.db.execute(
            select(CareCase).where(
                CareCase.user_id == care_user_id,
                CareCase.status.in_([
                    CaseStatus.OPEN,
                    CaseStatus.ESCALATING,
                    CaseStatus.PENDING_ACK,
                ]),
            ).order_by(CareCase.opened_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_recent_cases(
        self,
        care_user_id: uuid.UUID,
        days: int = 7,
        limit: int = 20,
    ) -> List[CareCase]:
        """최근 케이스 목록 조회"""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = await self.db.execute(
            select(CareCase).where(
                CareCase.user_id == care_user_id,
                CareCase.opened_at >= since,
            ).order_by(CareCase.opened_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_case_detail(
        self,
        case_id: uuid.UUID,
        care_user_id: uuid.UUID,
    ) -> Optional[CareCase]:
        """케이스 상세 조회 (권한 확인)"""
        result = await self.db.execute(
            select(CareCase).where(
                CareCase.id == case_id,
                CareCase.user_id == care_user_id,
            ).options(
                selectinload(CareCase.events),
                selectinload(CareCase.actions),
            )
        )
        return result.scalar_one_or_none()
    
    async def acknowledge_case(
        self,
        case_id: uuid.UUID,
        guardian_id: uuid.UUID,
        care_user_id: uuid.UUID,
        note: Optional[str] = None,
        action: str = "acknowledged",
        ip_address: str = "",
    ) -> Optional[CareCase]:
        """케이스 ACK 처리"""
        # 케이스 조회 (권한 확인)
        result = await self.db.execute(
            select(CareCase).where(
                CareCase.id == case_id,
                CareCase.user_id == care_user_id,
            )
        )
        case = result.scalar_one_or_none()
        
        if not case:
            return None
        
        # 이미 해결된 케이스는 ACK 불가
        if case.status in [CaseStatus.RESOLVED, CaseStatus.CLOSED]:
            return case
        
        # 상태 업데이트
        case.status = CaseStatus.ACKNOWLEDGED
        
        # 액션 기록
        case_action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action_type=ActionType.GUARDIAN_ACK,
            from_status=case.status.value,
            to_status=CaseStatus.ACKNOWLEDGED.value,
            note=note,
            action_data={
                "guardian_id": str(guardian_id),
                "action": action,
            },
            ip_address=ip_address,
        )
        
        self.db.add(case_action)
        await self.db.commit()
        await self.db.refresh(case)
        
        logger.info(
            f"Case acknowledged by guardian: "
            f"case={case.case_number}, guardian={guardian_id}"
        )
        
        audit_logger.log_action(
            user_id=str(guardian_id),
            action="case_acknowledged",
            resource_type="care_case",
            resource_id=str(case_id),
            ip_address=ip_address,
            details={"action": action, "note": note},
        )
        
        return case


class GuardianAlertService:
    """보호자용 알림 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_alerts(
        self,
        guardian_id: uuid.UUID,
        limit: int = 50,
        include_read: bool = False,
    ) -> List[Alert]:
        """알림 목록 조회"""
        query = select(Alert).where(
            Alert.target_guardian_id == guardian_id,
        )
        
        if not include_read:
            query = query.where(
                Alert.status.in_([AlertStatus.PENDING, AlertStatus.SENT, AlertStatus.DELIVERED])
            )
        
        query = query.order_by(Alert.scheduled_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_unread_count(self, guardian_id: uuid.UUID) -> int:
        """읽지 않은 알림 수"""
        result = await self.db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.target_guardian_id == guardian_id,
                Alert.status.in_([AlertStatus.PENDING, AlertStatus.SENT, AlertStatus.DELIVERED]),
            )
        )
        return result.scalar() or 0
    
    async def mark_as_read(
        self,
        alert_ids: List[uuid.UUID],
        guardian_id: uuid.UUID,
    ) -> int:
        """알림 읽음 처리"""
        count = 0
        for alert_id in alert_ids:
            result = await self.db.execute(
                select(Alert).where(
                    Alert.id == alert_id,
                    Alert.target_guardian_id == guardian_id,
                )
            )
            alert = result.scalar_one_or_none()
            
            if alert and alert.status != AlertStatus.ACKNOWLEDGED:
                alert.status = AlertStatus.DELIVERED
                count += 1
        
        if count > 0:
            await self.db.commit()
        
        return count


class GuardianDashboardService:
    """보호자 대시보드 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pii_encryption = PIIEncryption()
        self.case_service = GuardianCaseService(db)
        self.alert_service = GuardianAlertService(db)
    
    async def get_dashboard(
        self,
        guardian_id: uuid.UUID,
        care_user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """대시보드 데이터 조회"""
        # 보호자 정보
        result = await self.db.execute(
            select(Guardian).where(Guardian.id == guardian_id)
        )
        guardian = result.scalar_one_or_none()
        
        if not guardian:
            return None
        
        guardian_name = self.pii_encryption.decrypt(guardian.name_encrypted)
        
        # 돌봄 대상자 정보
        care_user_result = await self.db.execute(
            select(CareUser).where(CareUser.id == care_user_id)
            .options(selectinload(CareUser.pii))
        )
        care_user = care_user_result.scalar_one_or_none()
        
        care_user_name = "알 수 없음"
        if care_user and care_user.pii:
            care_user_name = self.pii_encryption.decrypt(care_user.pii.name_encrypted)
        
        # 열린 케이스
        open_cases = await self.case_service.get_open_cases(care_user_id)
        
        # 최근 알림
        recent_alerts = await self.alert_service.get_alerts(guardian_id, limit=10)
        
        # 읽지 않은 알림 수
        unread_count = await self.alert_service.get_unread_count(guardian_id)
        
        return {
            "guardian_id": guardian_id,
            "guardian_name": guardian_name,
            "care_user": {
                "id": care_user_id,
                "name": care_user_name,
                "is_active": care_user.is_active if care_user else False,
            },
            "open_cases_count": len(open_cases),
            "open_cases": open_cases,
            "recent_alerts": recent_alerts,
            "unread_alerts_count": unread_count,
        }
