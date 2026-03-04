"""
사용자 관리 서비스

- AdminUser CRUD
- CareUser CRUD (PII 암호화/복호화 포함)
- Guardian CRUD

참고: 모든 PII 필드는 AES-256-GCM으로 암호화하여 저장
"""

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import audit_logger, logger
from app.core.security import decrypt_pii, encrypt_pii, hash_password
from app.models.user import (
    AdminUser,
    CareUser,
    CareUserPII,
    ConsentStatus,
    Guardian,
    UserRole,
)
from app.schemas.user import (
    AdminUserCreate,
    AdminUserUpdate,
    CareUserCreate,
    CareUserUpdate,
    GuardianCreate,
    GuardianUpdate,
)


class AdminUserService:
    """관리자 사용자 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[AdminUser]:
        """ID로 관리자 조회"""
        result = await self.db.execute(
            select(AdminUser).where(
                AdminUser.id == user_id,
                AdminUser.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[AdminUser]:
        """이메일로 관리자 조회"""
        result = await self.db.execute(
            select(AdminUser).where(
                AdminUser.email == email,
                AdminUser.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AdminUser]:
        """관리자 목록 조회"""
        result = await self.db.execute(
            select(AdminUser)
            .where(AdminUser.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(AdminUser.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        data: AdminUserCreate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> AdminUser:
        """관리자 생성"""
        # 이메일 중복 검사
        existing = await self.get_by_email(data.email)
        if existing:
            raise ValueError("이미 사용 중인 이메일입니다.")
        
        user = AdminUser(
            id=uuid.uuid4(),
            email=data.email,
            password_hash=hash_password(data.password),
            name=data.name,
            role=UserRole(data.role),
            is_active=True,
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="admin_user_created",
            resource_type="admin_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return user
    
    async def update(
        self,
        user_id: uuid.UUID,
        data: AdminUserUpdate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[AdminUser]:
        """관리자 정보 수정"""
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "role":
                setattr(user, field, UserRole(value))
            else:
                setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="admin_user_updated",
            resource_type="admin_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return user
    
    async def delete(
        self,
        user_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> bool:
        """관리자 삭제 (소프트 삭제)"""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.soft_delete()
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="admin_user_deleted",
            resource_type="admin_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return True


class CareUserService:
    """대상자(독거노인) 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(
        self,
        user_id: uuid.UUID,
        include_pii: bool = False,
    ) -> Optional[CareUser]:
        """ID로 대상자 조회"""
        query = select(CareUser).where(
            CareUser.id == user_id,
            CareUser.deleted_at.is_(None),
        )
        
        if include_pii:
            query = query.options(selectinload(CareUser.pii))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[CareUser]:
        """코드로 대상자 조회"""
        result = await self.db.execute(
            select(CareUser).where(
                CareUser.code == code,
                CareUser.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
    ) -> List[CareUser]:
        """대상자 목록 조회"""
        query = select(CareUser).where(CareUser.deleted_at.is_(None))
        
        if is_active is not None:
            query = query.where(CareUser.is_active == is_active)
        
        query = query.offset(skip).limit(limit).order_by(CareUser.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(
        self,
        data: CareUserCreate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> CareUser:
        """대상자 생성 (PII 암호화 포함)"""
        # 코드 중복 검사
        existing = await self.get_by_code(data.code)
        if existing:
            raise ValueError("이미 사용 중인 코드입니다.")
        
        # 대상자 기본 정보 생성
        user = CareUser(
            id=uuid.uuid4(),
            code=data.code,
            consent_status=ConsentStatus(data.consent_status),
            is_active=data.is_active,
            notes=data.notes,
        )
        
        # PII 정보 암호화하여 생성
        pii = CareUserPII(
            id=uuid.uuid4(),
            user_id=user.id,
            name_encrypted=encrypt_pii(data.name),
            phone_encrypted=encrypt_pii(data.phone) if data.phone else None,
            address_encrypted=encrypt_pii(data.address) if data.address else None,
            birth_date_encrypted=encrypt_pii(str(data.birth_date)) if data.birth_date else None,
            emergency_contact_encrypted=encrypt_pii(data.emergency_contact) if data.emergency_contact else None,
        )
        
        self.db.add(user)
        self.db.add(pii)
        await self.db.commit()
        await self.db.refresh(user)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="care_user_created",
            resource_type="care_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return user
    
    async def update(
        self,
        user_id: uuid.UUID,
        data: CareUserUpdate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[CareUser]:
        """대상자 정보 수정"""
        user = await self.get_by_id(user_id, include_pii=True)
        if not user:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 기본 정보 업데이트
        basic_fields = ["consent_status", "consent_date", "is_active", "notes"]
        for field in basic_fields:
            if field in update_data:
                value = update_data[field]
                if field == "consent_status":
                    setattr(user, field, ConsentStatus(value))
                else:
                    setattr(user, field, value)
        
        # PII 정보 업데이트 (암호화)
        pii_fields = {
            "name": "name_encrypted",
            "phone": "phone_encrypted",
            "address": "address_encrypted",
            "birth_date": "birth_date_encrypted",
            "emergency_contact": "emergency_contact_encrypted",
        }
        
        if user.pii:
            for src_field, dst_field in pii_fields.items():
                if src_field in update_data:
                    value = update_data[src_field]
                    if value is not None:
                        if src_field == "birth_date":
                            encrypted = encrypt_pii(str(value))
                        else:
                            encrypted = encrypt_pii(value)
                        setattr(user.pii, dst_field, encrypted)
        
        await self.db.commit()
        await self.db.refresh(user)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="care_user_updated",
            resource_type="care_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return user
    
    async def delete(
        self,
        user_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> bool:
        """대상자 삭제 (소프트 삭제)"""
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        user.soft_delete()
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="care_user_deleted",
            resource_type="care_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return True
    
    def decrypt_user_pii(self, user: CareUser) -> dict:
        """대상자 PII 복호화
        
        Note: 권한 검증은 호출자가 수행해야 합니다.
        """
        if not user.pii:
            return {}
        
        pii = user.pii
        result = {
            "name": decrypt_pii(pii.name_encrypted) if pii.name_encrypted else None,
            "phone": decrypt_pii(pii.phone_encrypted) if pii.phone_encrypted else None,
            "address": decrypt_pii(pii.address_encrypted) if pii.address_encrypted else None,
            "birth_date": decrypt_pii(pii.birth_date_encrypted) if pii.birth_date_encrypted else None,
            "emergency_contact": decrypt_pii(pii.emergency_contact_encrypted) if pii.emergency_contact_encrypted else None,
        }
        return result


class GuardianService:
    """보호자 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, guardian_id: uuid.UUID) -> Optional[Guardian]:
        """ID로 보호자 조회"""
        result = await self.db.execute(
            select(Guardian).where(
                Guardian.id == guardian_id,
                Guardian.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def list_by_care_user(
        self,
        care_user_id: uuid.UUID,
    ) -> List[Guardian]:
        """대상자의 보호자 목록 조회 (우선순위 순)"""
        result = await self.db.execute(
            select(Guardian)
            .where(
                Guardian.care_user_id == care_user_id,
                Guardian.deleted_at.is_(None),
            )
            .order_by(Guardian.priority)
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        data: GuardianCreate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Guardian:
        """보호자 생성"""
        guardian = Guardian(
            id=uuid.uuid4(),
            care_user_id=data.care_user_id,
            relationship_type=data.relationship_type,
            priority=data.priority,
            receive_notifications=data.receive_notifications,
            # PII 암호화
            name_encrypted=encrypt_pii(data.name),
            phone_encrypted=encrypt_pii(data.phone),
            email_encrypted=encrypt_pii(data.email) if data.email else None,
        )
        
        self.db.add(guardian)
        await self.db.commit()
        await self.db.refresh(guardian)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="guardian_created",
            resource_type="guardian",
            resource_id=str(guardian.id),
            ip_address=ip_address,
            details={"care_user_id": str(data.care_user_id)},
        )
        
        return guardian
    
    async def update(
        self,
        guardian_id: uuid.UUID,
        data: GuardianUpdate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[Guardian]:
        """보호자 정보 수정"""
        guardian = await self.get_by_id(guardian_id)
        if not guardian:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 기본 필드 업데이트
        basic_fields = ["relationship_type", "priority", "receive_notifications"]
        for field in basic_fields:
            if field in update_data:
                setattr(guardian, field, update_data[field])
        
        # PII 필드 업데이트 (암호화)
        pii_map = {
            "name": "name_encrypted",
            "phone": "phone_encrypted",
            "email": "email_encrypted",
        }
        for src, dst in pii_map.items():
            if src in update_data and update_data[src] is not None:
                setattr(guardian, dst, encrypt_pii(update_data[src]))
        
        await self.db.commit()
        await self.db.refresh(guardian)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="guardian_updated",
            resource_type="guardian",
            resource_id=str(guardian.id),
            ip_address=ip_address,
        )
        
        return guardian
    
    async def delete(
        self,
        guardian_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> bool:
        """보호자 삭제 (소프트 삭제)"""
        guardian = await self.get_by_id(guardian_id)
        if not guardian:
            return False
        
        guardian.soft_delete()
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="guardian_deleted",
            resource_type="guardian",
            resource_id=str(guardian.id),
            ip_address=ip_address,
        )
        
        return True
    
    def decrypt_guardian_pii(self, guardian: Guardian) -> dict:
        """보호자 PII 복호화"""
        return {
            "name": decrypt_pii(guardian.name_encrypted),
            "phone": decrypt_pii(guardian.phone_encrypted),
            "email": decrypt_pii(guardian.email_encrypted) if guardian.email_encrypted else None,
        }
    
    @staticmethod
    def mask_name(name: str) -> str:
        """이름 마스킹 (예: 홍길동 → 홍*동)"""
        if not name or len(name) < 2:
            return "*"
        return name[0] + "*" * (len(name) - 2) + name[-1]
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """전화번호 마스킹 (예: 010-1234-5678 → 010-****-5678)"""
        if not phone:
            return ""
        # 숫자만 추출
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) < 7:
            return "***-****-****"
        return f"{digits[:3]}-****-{digits[-4:]}"
