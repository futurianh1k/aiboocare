"""
정책 관리 서비스

- PolicyBundle CRUD
- PolicyThreshold CRUD
- EscalationPlan CRUD
- PolicyRule CRUD
- 활성 정책 로드 및 캐싱
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import audit_logger, logger
from app.models.policy import (
    BundleStatus,
    EscalationPlan,
    PolicyBundle,
    PolicyRule,
    PolicyThreshold,
    RuleConditionType,
)
from app.schemas.policy import (
    DEFAULT_ESCALATION_PLANS,
    DEFAULT_THRESHOLDS,
    EscalationPlanCreate,
    EscalationPlanUpdate,
    PolicyBundleCreate,
    PolicyBundleUpdate,
    PolicyRuleCreate,
    PolicyRuleUpdate,
    PolicyThresholdCreate,
    PolicyThresholdUpdate,
)


class PolicyBundleService:
    """정책 번들 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(
        self,
        bundle_id: uuid.UUID,
        include_details: bool = False,
    ) -> Optional[PolicyBundle]:
        """ID로 번들 조회"""
        query = select(PolicyBundle).where(
            PolicyBundle.id == bundle_id,
            PolicyBundle.deleted_at.is_(None),
        )
        
        if include_details:
            query = query.options(
                selectinload(PolicyBundle.thresholds),
                selectinload(PolicyBundle.escalation_plans),
                selectinload(PolicyBundle.rules),
            )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active_bundle(self) -> Optional[PolicyBundle]:
        """현재 활성 번들 조회"""
        result = await self.db.execute(
            select(PolicyBundle)
            .where(
                PolicyBundle.status == BundleStatus.ACTIVE,
                PolicyBundle.deleted_at.is_(None),
            )
            .options(
                selectinload(PolicyBundle.thresholds),
                selectinload(PolicyBundle.escalation_plans),
                selectinload(PolicyBundle.rules),
            )
            .order_by(PolicyBundle.activated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def list_all(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[PolicyBundle]:
        """번들 목록 조회"""
        query = select(PolicyBundle).where(PolicyBundle.deleted_at.is_(None))
        
        if status:
            query = query.where(PolicyBundle.status == BundleStatus(status))
        
        query = query.order_by(PolicyBundle.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(
        self,
        data: PolicyBundleCreate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> PolicyBundle:
        """번들 생성"""
        bundle = PolicyBundle(
            id=uuid.uuid4(),
            name=data.name,
            version=data.version,
            description=data.description,
            status=BundleStatus.DRAFT,
            created_by_id=uuid.UUID(current_user_id) if current_user_id else None,
        )
        
        self.db.add(bundle)
        await self.db.commit()
        await self.db.refresh(bundle)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="policy_bundle_created",
            resource_type="policy_bundle",
            resource_id=str(bundle.id),
            ip_address=ip_address,
        )
        
        return bundle
    
    async def create_with_defaults(
        self,
        data: PolicyBundleCreate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> PolicyBundle:
        """기본 설정 포함하여 번들 생성"""
        bundle = await self.create(data, current_user_id, ip_address)
        
        # 기본 임계치 추가
        for threshold_data in DEFAULT_THRESHOLDS:
            threshold = PolicyThreshold(
                id=uuid.uuid4(),
                bundle_id=bundle.id,
                **threshold_data,
            )
            self.db.add(threshold)
        
        # 기본 에스컬레이션 플랜 추가
        for plan_data in DEFAULT_ESCALATION_PLANS:
            plan = EscalationPlan(
                id=uuid.uuid4(),
                bundle_id=bundle.id,
                **plan_data,
            )
            self.db.add(plan)
        
        await self.db.commit()
        await self.db.refresh(bundle)
        
        return bundle
    
    async def update(
        self,
        bundle_id: uuid.UUID,
        data: PolicyBundleUpdate,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[PolicyBundle]:
        """번들 수정"""
        bundle = await self.get_by_id(bundle_id)
        if not bundle:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == "status":
                setattr(bundle, field, BundleStatus(value))
            else:
                setattr(bundle, field, value)
        
        await self.db.commit()
        await self.db.refresh(bundle)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="policy_bundle_updated",
            resource_type="policy_bundle",
            resource_id=str(bundle.id),
            ip_address=ip_address,
        )
        
        return bundle
    
    async def activate(
        self,
        bundle_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> Optional[PolicyBundle]:
        """번들 활성화 (기존 활성 번들은 deprecated로 변경)"""
        bundle = await self.get_by_id(bundle_id)
        if not bundle:
            return None
        
        # 기존 활성 번들 비활성화
        result = await self.db.execute(
            select(PolicyBundle).where(
                PolicyBundle.status == BundleStatus.ACTIVE,
                PolicyBundle.id != bundle_id,
                PolicyBundle.deleted_at.is_(None),
            )
        )
        active_bundles = result.scalars().all()
        
        for active_bundle in active_bundles:
            active_bundle.status = BundleStatus.DEPRECATED
            active_bundle.deactivated_at = datetime.now(timezone.utc)
        
        # 새 번들 활성화
        bundle.status = BundleStatus.ACTIVE
        bundle.activated_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(bundle)
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="policy_bundle_activated",
            resource_type="policy_bundle",
            resource_id=str(bundle.id),
            ip_address=ip_address,
        )
        
        logger.info(f"Policy bundle activated: {bundle.name} v{bundle.version}")
        
        return bundle
    
    async def delete(
        self,
        bundle_id: uuid.UUID,
        current_user_id: str = "",
        ip_address: str = "",
    ) -> bool:
        """번들 삭제 (소프트 삭제)"""
        bundle = await self.get_by_id(bundle_id)
        if not bundle:
            return False
        
        # 활성 번들은 삭제 불가
        if bundle.status == BundleStatus.ACTIVE:
            raise ValueError("활성 상태의 번들은 삭제할 수 없습니다.")
        
        bundle.soft_delete()
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=current_user_id,
            action="policy_bundle_deleted",
            resource_type="policy_bundle",
            resource_id=str(bundle.id),
            ip_address=ip_address,
        )
        
        return True


class PolicyThresholdService:
    """센서 임계치 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, threshold_id: uuid.UUID) -> Optional[PolicyThreshold]:
        """ID로 임계치 조회"""
        result = await self.db.execute(
            select(PolicyThreshold).where(PolicyThreshold.id == threshold_id)
        )
        return result.scalar_one_or_none()
    
    async def list_by_bundle(self, bundle_id: uuid.UUID) -> List[PolicyThreshold]:
        """번들의 임계치 목록 조회"""
        result = await self.db.execute(
            select(PolicyThreshold)
            .where(PolicyThreshold.bundle_id == bundle_id)
            .order_by(PolicyThreshold.measurement_type)
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        data: PolicyThresholdCreate,
        current_user_id: str = "",
    ) -> PolicyThreshold:
        """임계치 생성"""
        threshold = PolicyThreshold(
            id=uuid.uuid4(),
            bundle_id=data.bundle_id,
            measurement_type=data.measurement_type,
            warning_min=data.warning_min,
            warning_max=data.warning_max,
            critical_min=data.critical_min,
            critical_max=data.critical_max,
            duration_seconds=data.duration_seconds,
            unit=data.unit,
            is_active=data.is_active,
        )
        
        self.db.add(threshold)
        await self.db.commit()
        await self.db.refresh(threshold)
        
        return threshold
    
    async def update(
        self,
        threshold_id: uuid.UUID,
        data: PolicyThresholdUpdate,
    ) -> Optional[PolicyThreshold]:
        """임계치 수정"""
        threshold = await self.get_by_id(threshold_id)
        if not threshold:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(threshold, field, value)
        
        await self.db.commit()
        await self.db.refresh(threshold)
        
        return threshold
    
    async def delete(self, threshold_id: uuid.UUID) -> bool:
        """임계치 삭제"""
        threshold = await self.get_by_id(threshold_id)
        if not threshold:
            return False
        
        await self.db.delete(threshold)
        await self.db.commit()
        
        return True


class EscalationPlanService:
    """콜 트리 설정 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, plan_id: uuid.UUID) -> Optional[EscalationPlan]:
        """ID로 플랜 조회"""
        result = await self.db.execute(
            select(EscalationPlan).where(EscalationPlan.id == plan_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_stage(
        self,
        bundle_id: uuid.UUID,
        stage: int,
    ) -> Optional[EscalationPlan]:
        """번들과 단계로 플랜 조회"""
        result = await self.db.execute(
            select(EscalationPlan).where(
                EscalationPlan.bundle_id == bundle_id,
                EscalationPlan.stage == stage,
            )
        )
        return result.scalar_one_or_none()
    
    async def list_by_bundle(self, bundle_id: uuid.UUID) -> List[EscalationPlan]:
        """번들의 플랜 목록 조회 (단계 순)"""
        result = await self.db.execute(
            select(EscalationPlan)
            .where(EscalationPlan.bundle_id == bundle_id)
            .order_by(EscalationPlan.stage)
        )
        return list(result.scalars().all())
    
    async def create(
        self,
        data: EscalationPlanCreate,
        current_user_id: str = "",
    ) -> EscalationPlan:
        """플랜 생성"""
        plan = EscalationPlan(
            id=uuid.uuid4(),
            bundle_id=data.bundle_id,
            stage=data.stage,
            name=data.name,
            target_type=data.target_type,
            timeout_seconds=data.timeout_seconds,
            notification_channels=data.notification_channels,
            auto_escalate=data.auto_escalate,
            is_active=data.is_active,
        )
        
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        
        return plan
    
    async def update(
        self,
        plan_id: uuid.UUID,
        data: EscalationPlanUpdate,
    ) -> Optional[EscalationPlan]:
        """플랜 수정"""
        plan = await self.get_by_id(plan_id)
        if not plan:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)
        
        await self.db.commit()
        await self.db.refresh(plan)
        
        return plan
    
    async def delete(self, plan_id: uuid.UUID) -> bool:
        """플랜 삭제"""
        plan = await self.get_by_id(plan_id)
        if not plan:
            return False
        
        await self.db.delete(plan)
        await self.db.commit()
        
        return True


class PolicyRuleService:
    """복합 조건 룰 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, rule_id: uuid.UUID) -> Optional[PolicyRule]:
        """ID로 룰 조회"""
        result = await self.db.execute(
            select(PolicyRule).where(
                PolicyRule.id == rule_id,
                PolicyRule.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def list_by_bundle(
        self,
        bundle_id: uuid.UUID,
        is_active: Optional[bool] = None,
        is_emergency: Optional[bool] = None,
    ) -> List[PolicyRule]:
        """번들의 룰 목록 조회 (우선순위 순)"""
        query = select(PolicyRule).where(
            PolicyRule.bundle_id == bundle_id,
            PolicyRule.deleted_at.is_(None),
        )
        
        if is_active is not None:
            query = query.where(PolicyRule.is_active == is_active)
        
        if is_emergency is not None:
            query = query.where(PolicyRule.is_emergency_rule == is_emergency)
        
        query = query.order_by(PolicyRule.priority)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_emergency_rules(self, bundle_id: uuid.UUID) -> List[PolicyRule]:
        """긴급 룰 목록 조회 (Hard Rules)"""
        return await self.list_by_bundle(
            bundle_id,
            is_active=True,
            is_emergency=True,
        )
    
    async def create(
        self,
        data: PolicyRuleCreate,
        current_user_id: str = "",
    ) -> PolicyRule:
        """룰 생성"""
        rule = PolicyRule(
            id=uuid.uuid4(),
            bundle_id=data.bundle_id,
            name=data.name,
            description=data.description,
            condition_type=RuleConditionType(data.condition_type),
            rule_json=data.rule_json,
            action_json=data.action_json,
            priority=data.priority,
            is_active=data.is_active,
            is_emergency_rule=data.is_emergency_rule,
        )
        
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        
        return rule
    
    async def update(
        self,
        rule_id: uuid.UUID,
        data: PolicyRuleUpdate,
    ) -> Optional[PolicyRule]:
        """룰 수정"""
        rule = await self.get_by_id(rule_id)
        if not rule:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        
        await self.db.commit()
        await self.db.refresh(rule)
        
        return rule
    
    async def delete(
        self,
        rule_id: uuid.UUID,
        current_user_id: str = "",
    ) -> bool:
        """룰 삭제 (소프트 삭제)"""
        rule = await self.get_by_id(rule_id)
        if not rule:
            return False
        
        rule.soft_delete()
        await self.db.commit()
        
        return True
