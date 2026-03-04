"""
사용자 관련 Pydantic 스키마

- AdminUser: 관리자/운영자 계정
- CareUser: 대상자(독거노인)
- Guardian: 보호자
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ============== AdminUser 스키마 ==============

class AdminUserBase(BaseModel):
    """관리자 기본 스키마"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(default="operator", pattern="^(admin|operator|guardian|caregiver)$")


class AdminUserCreate(AdminUserBase):
    """관리자 생성 스키마"""
    password: str = Field(..., min_length=8)


class AdminUserUpdate(BaseModel):
    """관리자 수정 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, pattern="^(admin|operator|guardian|caregiver)$")
    is_active: Optional[bool] = None


class AdminUserResponse(AdminUserBase):
    """관리자 응답 스키마"""
    id: uuid.UUID
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============== CareUser 스키마 ==============

class CareUserBase(BaseModel):
    """대상자 기본 스키마"""
    code: str = Field(..., min_length=1, max_length=20, description="내부 식별 코드")
    consent_status: str = Field(default="pending", pattern="^(pending|consented|withdrawn)$")
    is_active: bool = True
    notes: Optional[str] = None


class CareUserCreate(CareUserBase):
    """대상자 생성 스키마 (PII 포함)"""
    # PII 필드 (암호화 저장)
    name: str = Field(..., min_length=1, max_length=100, description="실명")
    phone: Optional[str] = Field(None, description="전화번호")
    address: Optional[str] = Field(None, description="주소")
    birth_date: Optional[date] = Field(None, description="생년월일")
    emergency_contact: Optional[str] = Field(None, description="응급 연락처")


class CareUserUpdate(BaseModel):
    """대상자 수정 스키마"""
    consent_status: Optional[str] = Field(None, pattern="^(pending|consented|withdrawn)$")
    consent_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    # PII 필드 (선택적 수정)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    emergency_contact: Optional[str] = None


class CareUserResponse(CareUserBase):
    """대상자 응답 스키마 (PII 제외)"""
    id: uuid.UUID
    consent_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CareUserDetailResponse(CareUserResponse):
    """대상자 상세 응답 스키마 (PII 포함, 권한 필요)"""
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[date] = None
    emergency_contact: Optional[str] = None


# ============== Guardian 스키마 ==============

class GuardianBase(BaseModel):
    """보호자 기본 스키마"""
    relationship_type: str = Field(..., description="보호자 관계 (예: 자녀, 배우자)")
    priority: int = Field(default=1, ge=1, le=10, description="콜 트리 우선순위 (1=최우선)")
    receive_notifications: bool = True


class GuardianCreate(GuardianBase):
    """보호자 생성 스키마"""
    care_user_id: uuid.UUID
    # PII 필드 (암호화 저장)
    name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., description="연락처 (필수)")
    email: Optional[EmailStr] = None


class GuardianUpdate(BaseModel):
    """보호자 수정 스키마"""
    relationship_type: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    receive_notifications: Optional[bool] = None
    # PII 필드
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class GuardianResponse(GuardianBase):
    """보호자 응답 스키마 (PII 마스킹)"""
    id: uuid.UUID
    care_user_id: uuid.UUID
    name_masked: str = Field(description="마스킹된 이름 (예: 홍*동)")
    phone_masked: str = Field(description="마스킹된 전화번호 (예: 010-****-1234)")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class GuardianDetailResponse(GuardianBase):
    """보호자 상세 응답 스키마 (PII 포함, 권한 필요)"""
    id: uuid.UUID
    care_user_id: uuid.UUID
    name: str
    phone: str
    email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
