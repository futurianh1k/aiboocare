"""
정책 관리 API 엔드포인트

- PolicyBundle CRUD + 활성화
- PolicyThreshold CRUD
- EscalationPlan CRUD
- PolicyRule CRUD

보안 규칙:
- 모든 정책 변경은 Admin 권한 필요
- 조회는 Operator 이상
- 모든 변경은 Audit Log에 기록
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin, require_operator
from app.schemas.policy import (
    EscalationPlanCreate,
    EscalationPlanResponse,
    EscalationPlanUpdate,
    PolicyBundleCreate,
    PolicyBundleDetailResponse,
    PolicyBundleResponse,
    PolicyBundleUpdate,
    PolicyRuleCreate,
    PolicyRuleResponse,
    PolicyRuleUpdate,
    PolicyThresholdCreate,
    PolicyThresholdResponse,
    PolicyThresholdUpdate,
)
from app.services.policy import (
    EscalationPlanService,
    PolicyBundleService,
    PolicyRuleService,
    PolicyThresholdService,
)

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


# ============== PolicyBundle API ==============

@router.get("/bundles", response_model=List[PolicyBundleResponse])
async def list_policy_bundles(
    status: Optional[str] = Query(None, pattern="^(draft|active|deprecated|archived)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """정책 번들 목록 조회 (Operator 이상)"""
    service = PolicyBundleService(db)
    bundles = await service.list_all(status=status, skip=skip, limit=limit)
    
    return [
        PolicyBundleResponse(
            id=b.id,
            name=b.name,
            version=b.version,
            description=b.description,
            status=b.status.value,
            activated_at=b.activated_at,
            deactivated_at=b.deactivated_at,
            created_by_id=b.created_by_id,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        for b in bundles
    ]


@router.get("/bundles/active", response_model=PolicyBundleDetailResponse)
async def get_active_policy_bundle(
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """현재 활성 정책 번들 조회 (상세, Operator 이상)"""
    service = PolicyBundleService(db)
    bundle = await service.get_active_bundle()
    
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="활성화된 정책 번들이 없습니다.",
        )
    
    return PolicyBundleDetailResponse(
        id=bundle.id,
        name=bundle.name,
        version=bundle.version,
        description=bundle.description,
        status=bundle.status.value,
        activated_at=bundle.activated_at,
        deactivated_at=bundle.deactivated_at,
        created_by_id=bundle.created_by_id,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
        thresholds=[
            PolicyThresholdResponse(
                id=t.id,
                bundle_id=t.bundle_id,
                measurement_type=t.measurement_type,
                warning_min=t.warning_min,
                warning_max=t.warning_max,
                critical_min=t.critical_min,
                critical_max=t.critical_max,
                duration_seconds=t.duration_seconds,
                unit=t.unit,
                is_active=t.is_active,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in bundle.thresholds
        ],
        escalation_plans=[
            EscalationPlanResponse(
                id=p.id,
                bundle_id=p.bundle_id,
                stage=p.stage,
                name=p.name,
                target_type=p.target_type,
                timeout_seconds=p.timeout_seconds,
                notification_channels=p.notification_channels,
                auto_escalate=p.auto_escalate,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in sorted(bundle.escalation_plans, key=lambda x: x.stage)
        ],
        rules=[
            PolicyRuleResponse(
                id=r.id,
                bundle_id=r.bundle_id,
                name=r.name,
                description=r.description,
                condition_type=r.condition_type.value,
                rule_json=r.rule_json,
                action_json=r.action_json,
                priority=r.priority,
                is_active=r.is_active,
                is_emergency_rule=r.is_emergency_rule,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in sorted(bundle.rules, key=lambda x: x.priority)
        ],
    )


@router.get("/bundles/{bundle_id}", response_model=PolicyBundleDetailResponse)
async def get_policy_bundle(
    bundle_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """정책 번들 상세 조회 (Operator 이상)"""
    service = PolicyBundleService(db)
    bundle = await service.get_by_id(bundle_id, include_details=True)
    
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="정책 번들을 찾을 수 없습니다.",
        )
    
    return PolicyBundleDetailResponse(
        id=bundle.id,
        name=bundle.name,
        version=bundle.version,
        description=bundle.description,
        status=bundle.status.value,
        activated_at=bundle.activated_at,
        deactivated_at=bundle.deactivated_at,
        created_by_id=bundle.created_by_id,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
        thresholds=[
            PolicyThresholdResponse(
                id=t.id,
                bundle_id=t.bundle_id,
                measurement_type=t.measurement_type,
                warning_min=t.warning_min,
                warning_max=t.warning_max,
                critical_min=t.critical_min,
                critical_max=t.critical_max,
                duration_seconds=t.duration_seconds,
                unit=t.unit,
                is_active=t.is_active,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in bundle.thresholds
        ],
        escalation_plans=[
            EscalationPlanResponse(
                id=p.id,
                bundle_id=p.bundle_id,
                stage=p.stage,
                name=p.name,
                target_type=p.target_type,
                timeout_seconds=p.timeout_seconds,
                notification_channels=p.notification_channels,
                auto_escalate=p.auto_escalate,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in sorted(bundle.escalation_plans, key=lambda x: x.stage)
        ],
        rules=[
            PolicyRuleResponse(
                id=r.id,
                bundle_id=r.bundle_id,
                name=r.name,
                description=r.description,
                condition_type=r.condition_type.value,
                rule_json=r.rule_json,
                action_json=r.action_json,
                priority=r.priority,
                is_active=r.is_active,
                is_emergency_rule=r.is_emergency_rule,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in sorted(bundle.rules, key=lambda x: x.priority)
        ],
    )


@router.post("/bundles", response_model=PolicyBundleResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_bundle(
    request: Request,
    data: PolicyBundleCreate,
    with_defaults: bool = Query(True, description="기본 설정 포함 여부"),
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """정책 번들 생성 (Admin 전용)
    
    with_defaults=True면 기본 임계치와 에스컬레이션 플랜이 자동 생성됩니다.
    """
    service = PolicyBundleService(db)
    
    if with_defaults:
        bundle = await service.create_with_defaults(
            data=data,
            current_user_id=current_user["user_id"],
            ip_address=get_client_ip(request),
        )
    else:
        bundle = await service.create(
            data=data,
            current_user_id=current_user["user_id"],
            ip_address=get_client_ip(request),
        )
    
    return PolicyBundleResponse(
        id=bundle.id,
        name=bundle.name,
        version=bundle.version,
        description=bundle.description,
        status=bundle.status.value,
        activated_at=bundle.activated_at,
        deactivated_at=bundle.deactivated_at,
        created_by_id=bundle.created_by_id,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
    )


@router.patch("/bundles/{bundle_id}", response_model=PolicyBundleResponse)
async def update_policy_bundle(
    request: Request,
    bundle_id: UUID,
    data: PolicyBundleUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """정책 번들 수정 (Admin 전용)"""
    service = PolicyBundleService(db)
    
    bundle = await service.update(
        bundle_id=bundle_id,
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="정책 번들을 찾을 수 없습니다.",
        )
    
    return PolicyBundleResponse(
        id=bundle.id,
        name=bundle.name,
        version=bundle.version,
        description=bundle.description,
        status=bundle.status.value,
        activated_at=bundle.activated_at,
        deactivated_at=bundle.deactivated_at,
        created_by_id=bundle.created_by_id,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
    )


@router.post("/bundles/{bundle_id}/activate", response_model=PolicyBundleResponse)
async def activate_policy_bundle(
    request: Request,
    bundle_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """정책 번들 활성화 (Admin 전용)
    
    기존 활성 번들은 자동으로 deprecated 상태로 변경됩니다.
    """
    service = PolicyBundleService(db)
    
    bundle = await service.activate(
        bundle_id=bundle_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="정책 번들을 찾을 수 없습니다.",
        )
    
    return PolicyBundleResponse(
        id=bundle.id,
        name=bundle.name,
        version=bundle.version,
        description=bundle.description,
        status=bundle.status.value,
        activated_at=bundle.activated_at,
        deactivated_at=bundle.deactivated_at,
        created_by_id=bundle.created_by_id,
        created_at=bundle.created_at,
        updated_at=bundle.updated_at,
    )


@router.delete("/bundles/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_bundle(
    request: Request,
    bundle_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """정책 번들 삭제 (Admin 전용)
    
    활성 상태의 번들은 삭제할 수 없습니다.
    """
    service = PolicyBundleService(db)
    
    try:
        success = await service.delete(
            bundle_id=bundle_id,
            current_user_id=current_user["user_id"],
            ip_address=get_client_ip(request),
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="정책 번들을 찾을 수 없습니다.",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============== PolicyThreshold API ==============

@router.get("/bundles/{bundle_id}/thresholds", response_model=List[PolicyThresholdResponse])
async def list_thresholds(
    bundle_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """번들의 임계치 목록 조회 (Operator 이상)"""
    service = PolicyThresholdService(db)
    thresholds = await service.list_by_bundle(bundle_id)
    
    return [
        PolicyThresholdResponse(
            id=t.id,
            bundle_id=t.bundle_id,
            measurement_type=t.measurement_type,
            warning_min=t.warning_min,
            warning_max=t.warning_max,
            critical_min=t.critical_min,
            critical_max=t.critical_max,
            duration_seconds=t.duration_seconds,
            unit=t.unit,
            is_active=t.is_active,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in thresholds
    ]


@router.post("/thresholds", response_model=PolicyThresholdResponse, status_code=status.HTTP_201_CREATED)
async def create_threshold(
    data: PolicyThresholdCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """임계치 생성 (Admin 전용)"""
    service = PolicyThresholdService(db)
    threshold = await service.create(data, current_user["user_id"])
    
    return PolicyThresholdResponse(
        id=threshold.id,
        bundle_id=threshold.bundle_id,
        measurement_type=threshold.measurement_type,
        warning_min=threshold.warning_min,
        warning_max=threshold.warning_max,
        critical_min=threshold.critical_min,
        critical_max=threshold.critical_max,
        duration_seconds=threshold.duration_seconds,
        unit=threshold.unit,
        is_active=threshold.is_active,
        created_at=threshold.created_at,
        updated_at=threshold.updated_at,
    )


@router.patch("/thresholds/{threshold_id}", response_model=PolicyThresholdResponse)
async def update_threshold(
    threshold_id: UUID,
    data: PolicyThresholdUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """임계치 수정 (Admin 전용)"""
    service = PolicyThresholdService(db)
    threshold = await service.update(threshold_id, data)
    
    if not threshold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="임계치를 찾을 수 없습니다.",
        )
    
    return PolicyThresholdResponse(
        id=threshold.id,
        bundle_id=threshold.bundle_id,
        measurement_type=threshold.measurement_type,
        warning_min=threshold.warning_min,
        warning_max=threshold.warning_max,
        critical_min=threshold.critical_min,
        critical_max=threshold.critical_max,
        duration_seconds=threshold.duration_seconds,
        unit=threshold.unit,
        is_active=threshold.is_active,
        created_at=threshold.created_at,
        updated_at=threshold.updated_at,
    )


@router.delete("/thresholds/{threshold_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_threshold(
    threshold_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """임계치 삭제 (Admin 전용)"""
    service = PolicyThresholdService(db)
    success = await service.delete(threshold_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="임계치를 찾을 수 없습니다.",
        )


# ============== EscalationPlan API ==============

@router.get("/bundles/{bundle_id}/escalation-plans", response_model=List[EscalationPlanResponse])
async def list_escalation_plans(
    bundle_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """번들의 에스컬레이션 플랜 목록 조회 (Operator 이상)"""
    service = EscalationPlanService(db)
    plans = await service.list_by_bundle(bundle_id)
    
    return [
        EscalationPlanResponse(
            id=p.id,
            bundle_id=p.bundle_id,
            stage=p.stage,
            name=p.name,
            target_type=p.target_type,
            timeout_seconds=p.timeout_seconds,
            notification_channels=p.notification_channels,
            auto_escalate=p.auto_escalate,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in plans
    ]


@router.post("/escalation-plans", response_model=EscalationPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_escalation_plan(
    data: EscalationPlanCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """에스컬레이션 플랜 생성 (Admin 전용)"""
    service = EscalationPlanService(db)
    plan = await service.create(data, current_user["user_id"])
    
    return EscalationPlanResponse(
        id=plan.id,
        bundle_id=plan.bundle_id,
        stage=plan.stage,
        name=plan.name,
        target_type=plan.target_type,
        timeout_seconds=plan.timeout_seconds,
        notification_channels=plan.notification_channels,
        auto_escalate=plan.auto_escalate,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.patch("/escalation-plans/{plan_id}", response_model=EscalationPlanResponse)
async def update_escalation_plan(
    plan_id: UUID,
    data: EscalationPlanUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """에스컬레이션 플랜 수정 (Admin 전용)"""
    service = EscalationPlanService(db)
    plan = await service.update(plan_id, data)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="에스컬레이션 플랜을 찾을 수 없습니다.",
        )
    
    return EscalationPlanResponse(
        id=plan.id,
        bundle_id=plan.bundle_id,
        stage=plan.stage,
        name=plan.name,
        target_type=plan.target_type,
        timeout_seconds=plan.timeout_seconds,
        notification_channels=plan.notification_channels,
        auto_escalate=plan.auto_escalate,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.delete("/escalation-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_escalation_plan(
    plan_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """에스컬레이션 플랜 삭제 (Admin 전용)"""
    service = EscalationPlanService(db)
    success = await service.delete(plan_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="에스컬레이션 플랜을 찾을 수 없습니다.",
        )


# ============== PolicyRule API ==============

@router.get("/bundles/{bundle_id}/rules", response_model=List[PolicyRuleResponse])
async def list_policy_rules(
    bundle_id: UUID,
    is_active: Optional[bool] = Query(None),
    is_emergency: Optional[bool] = Query(None),
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """번들의 정책 룰 목록 조회 (Operator 이상)"""
    service = PolicyRuleService(db)
    rules = await service.list_by_bundle(
        bundle_id,
        is_active=is_active,
        is_emergency=is_emergency,
    )
    
    return [
        PolicyRuleResponse(
            id=r.id,
            bundle_id=r.bundle_id,
            name=r.name,
            description=r.description,
            condition_type=r.condition_type.value,
            rule_json=r.rule_json,
            action_json=r.action_json,
            priority=r.priority,
            is_active=r.is_active,
            is_emergency_rule=r.is_emergency_rule,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rules
    ]


@router.post("/rules", response_model=PolicyRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_rule(
    data: PolicyRuleCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """정책 룰 생성 (Admin 전용)"""
    service = PolicyRuleService(db)
    rule = await service.create(data, current_user["user_id"])
    
    return PolicyRuleResponse(
        id=rule.id,
        bundle_id=rule.bundle_id,
        name=rule.name,
        description=rule.description,
        condition_type=rule.condition_type.value,
        rule_json=rule.rule_json,
        action_json=rule.action_json,
        priority=rule.priority,
        is_active=rule.is_active,
        is_emergency_rule=rule.is_emergency_rule,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.patch("/rules/{rule_id}", response_model=PolicyRuleResponse)
async def update_policy_rule(
    rule_id: UUID,
    data: PolicyRuleUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """정책 룰 수정 (Admin 전용)"""
    service = PolicyRuleService(db)
    rule = await service.update(rule_id, data)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="정책 룰을 찾을 수 없습니다.",
        )
    
    return PolicyRuleResponse(
        id=rule.id,
        bundle_id=rule.bundle_id,
        name=rule.name,
        description=rule.description,
        condition_type=rule.condition_type.value,
        rule_json=rule.rule_json,
        action_json=rule.action_json,
        priority=rule.priority,
        is_active=rule.is_active,
        is_emergency_rule=rule.is_emergency_rule,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy_rule(
    rule_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """정책 룰 삭제 (Admin 전용)"""
    service = PolicyRuleService(db)
    success = await service.delete(rule_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="정책 룰을 찾을 수 없습니다.",
        )
