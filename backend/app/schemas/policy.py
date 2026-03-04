"""
정책 관련 Pydantic 스키마

- PolicyBundle: 정책 번들 (버전 관리)
- PolicyThreshold: 센서 임계치
- EscalationPlan: 콜 트리 설정
- PolicyRule: 복합 조건 룰
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============== PolicyBundle 스키마 ==============

class PolicyBundleBase(BaseModel):
    """정책 번들 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$", description="버전 (예: 1.0.0)")
    description: Optional[str] = None


class PolicyBundleCreate(PolicyBundleBase):
    """정책 번들 생성 스키마"""
    pass


class PolicyBundleUpdate(BaseModel):
    """정책 번들 수정 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|deprecated|archived)$")


class PolicyBundleResponse(PolicyBundleBase):
    """정책 번들 응답 스키마"""
    id: uuid.UUID
    status: str
    activated_at: Optional[datetime]
    deactivated_at: Optional[datetime]
    created_by_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PolicyBundleDetailResponse(PolicyBundleResponse):
    """정책 번들 상세 응답 스키마"""
    thresholds: List["PolicyThresholdResponse"] = []
    escalation_plans: List["EscalationPlanResponse"] = []
    rules: List["PolicyRuleResponse"] = []


# ============== PolicyThreshold 스키마 ==============

class PolicyThresholdBase(BaseModel):
    """센서 임계치 기본 스키마"""
    measurement_type: str = Field(..., description="측정 종류 (spo2, heart_rate 등)")
    warning_min: Optional[float] = Field(None, description="경고 하한값")
    warning_max: Optional[float] = Field(None, description="경고 상한값")
    critical_min: Optional[float] = Field(None, description="위험 하한값")
    critical_max: Optional[float] = Field(None, description="위험 상한값")
    duration_seconds: Optional[int] = Field(None, ge=0, description="지속 시간 조건")
    unit: Optional[str] = Field(None, max_length=20)
    is_active: bool = True


class PolicyThresholdCreate(PolicyThresholdBase):
    """센서 임계치 생성 스키마"""
    bundle_id: uuid.UUID


class PolicyThresholdUpdate(BaseModel):
    """센서 임계치 수정 스키마"""
    warning_min: Optional[float] = None
    warning_max: Optional[float] = None
    critical_min: Optional[float] = None
    critical_max: Optional[float] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class PolicyThresholdResponse(PolicyThresholdBase):
    """센서 임계치 응답 스키마"""
    id: uuid.UUID
    bundle_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============== EscalationPlan 스키마 ==============

class EscalationPlanBase(BaseModel):
    """콜 트리 설정 기본 스키마"""
    stage: int = Field(..., ge=1, le=10, description="단계 번호")
    name: str = Field(..., min_length=1, max_length=100, description="단계 이름")
    target_type: str = Field(
        ...,
        pattern="^(guardian|caregiver|operator|emergency)$",
        description="대상 유형",
    )
    timeout_seconds: int = Field(60, ge=10, le=600, description="타임아웃 (초)")
    notification_channels: List[str] = Field(
        default=["push", "sms"],
        description="알림 채널",
    )
    auto_escalate: bool = True
    is_active: bool = True


class EscalationPlanCreate(EscalationPlanBase):
    """콜 트리 설정 생성 스키마"""
    bundle_id: uuid.UUID


class EscalationPlanUpdate(BaseModel):
    """콜 트리 설정 수정 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    target_type: Optional[str] = Field(None, pattern="^(guardian|caregiver|operator|emergency)$")
    timeout_seconds: Optional[int] = Field(None, ge=10, le=600)
    notification_channels: Optional[List[str]] = None
    auto_escalate: Optional[bool] = None
    is_active: Optional[bool] = None


class EscalationPlanResponse(EscalationPlanBase):
    """콜 트리 설정 응답 스키마"""
    id: uuid.UUID
    bundle_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============== PolicyRule 스키마 ==============

class PolicyRuleBase(BaseModel):
    """복합 조건 룰 기본 스키마"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    condition_type: str = Field(
        ...,
        pattern="^(threshold|pattern|keyword|composite)$",
    )
    rule_json: Dict[str, Any] = Field(..., description="조건 정의 (JSON)")
    action_json: Dict[str, Any] = Field(..., description="액션 정의 (JSON)")
    priority: int = Field(100, ge=1, le=1000, description="우선순위")
    is_active: bool = True
    is_emergency_rule: bool = False


class PolicyRuleCreate(PolicyRuleBase):
    """복합 조건 룰 생성 스키마"""
    bundle_id: uuid.UUID


class PolicyRuleUpdate(BaseModel):
    """복합 조건 룰 수정 스키마"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rule_json: Optional[Dict[str, Any]] = None
    action_json: Optional[Dict[str, Any]] = None
    priority: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None
    is_emergency_rule: Optional[bool] = None


class PolicyRuleResponse(PolicyRuleBase):
    """복합 조건 룰 응답 스키마"""
    id: uuid.UUID
    bundle_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============== 기본 정책 템플릿 ==============

DEFAULT_THRESHOLDS = [
    {
        "measurement_type": "spo2",
        "warning_min": 94,
        "critical_min": 90,
        "duration_seconds": 60,
        "unit": "%",
    },
    {
        "measurement_type": "heart_rate",
        "warning_min": 50,
        "warning_max": 100,
        "critical_min": 40,
        "critical_max": 120,
        "unit": "bpm",
    },
    {
        "measurement_type": "body_temperature",
        "warning_min": 36.0,
        "warning_max": 37.5,
        "critical_min": 35.0,
        "critical_max": 38.5,
        "unit": "°C",
    },
]

DEFAULT_ESCALATION_PLANS = [
    {
        "stage": 1,
        "name": "보호자 1차",
        "target_type": "guardian",
        "timeout_seconds": 60,
        "notification_channels": ["push", "call"],
    },
    {
        "stage": 2,
        "name": "보호자 2차",
        "target_type": "guardian",
        "timeout_seconds": 90,
        "notification_channels": ["push", "call"],
    },
    {
        "stage": 3,
        "name": "요양보호사/기관",
        "target_type": "caregiver",
        "timeout_seconds": 120,
        "notification_channels": ["call", "push"],
    },
    {
        "stage": 4,
        "name": "관제센터/운영자",
        "target_type": "operator",
        "timeout_seconds": 60,
        "notification_channels": ["call", "console"],
    },
    {
        "stage": 5,
        "name": "119 응급",
        "target_type": "emergency",
        "timeout_seconds": 0,
        "notification_channels": ["api"],
        "auto_escalate": False,
    },
]


# Forward reference 해결
PolicyBundleDetailResponse.model_rebuild()
