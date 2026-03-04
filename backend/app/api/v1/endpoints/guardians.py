"""
보호자 관리 API 엔드포인트

보안 규칙:
- PII는 마스킹하여 반환 (기본)
- 상세 조회 시에만 복호화 (권한 필요)
- 모든 CRUD 작업은 Audit Log에 기록
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_operator
from app.schemas.user import (
    GuardianCreate,
    GuardianDetailResponse,
    GuardianResponse,
    GuardianUpdate,
)
from app.services.user import GuardianService

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.get("/care/{care_user_id}/guardians", response_model=List[GuardianResponse])
async def list_guardians(
    care_user_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """대상자의 보호자 목록 조회 (Operator 이상)
    
    PII는 마스킹하여 반환합니다.
    콜 트리 우선순위 순으로 정렬됩니다.
    """
    service = GuardianService(db)
    guardians = await service.list_by_care_user(care_user_id)
    
    result = []
    for guardian in guardians:
        # PII 복호화 후 마스킹
        pii = service.decrypt_guardian_pii(guardian)
        
        result.append(GuardianResponse(
            id=guardian.id,
            care_user_id=guardian.care_user_id,
            relationship_type=guardian.relationship_type,
            priority=guardian.priority,
            receive_notifications=guardian.receive_notifications,
            name_masked=service.mask_name(pii["name"]),
            phone_masked=service.mask_phone(pii["phone"]),
            created_at=guardian.created_at,
            updated_at=guardian.updated_at,
        ))
    
    return result


@router.get("/guardians/{guardian_id}", response_model=GuardianDetailResponse)
async def get_guardian_detail(
    guardian_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """보호자 상세 정보 조회 (PII 포함, Operator 이상)
    
    이 API 호출은 Audit Log에 기록됩니다.
    """
    from app.core.logging import audit_logger
    
    service = GuardianService(db)
    guardian = await service.get_by_id(guardian_id)
    
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="보호자를 찾을 수 없습니다.",
        )
    
    # PII 접근 감사 기록
    audit_logger.log_action(
        user_id=current_user["user_id"],
        action="guardian_pii_accessed",
        resource_type="guardian",
        resource_id=str(guardian_id),
    )
    
    # PII 복호화
    pii = service.decrypt_guardian_pii(guardian)
    
    return GuardianDetailResponse(
        id=guardian.id,
        care_user_id=guardian.care_user_id,
        relationship_type=guardian.relationship_type,
        priority=guardian.priority,
        receive_notifications=guardian.receive_notifications,
        name=pii["name"],
        phone=pii["phone"],
        email=pii.get("email"),
        created_at=guardian.created_at,
        updated_at=guardian.updated_at,
    )


@router.post("/guardians", response_model=GuardianResponse, status_code=status.HTTP_201_CREATED)
async def create_guardian(
    request: Request,
    data: GuardianCreate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """보호자 등록 (Operator 이상)
    
    PII는 암호화하여 저장됩니다.
    """
    service = GuardianService(db)
    
    guardian = await service.create(
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    # PII 복호화 후 마스킹하여 반환
    pii = service.decrypt_guardian_pii(guardian)
    
    return GuardianResponse(
        id=guardian.id,
        care_user_id=guardian.care_user_id,
        relationship_type=guardian.relationship_type,
        priority=guardian.priority,
        receive_notifications=guardian.receive_notifications,
        name_masked=service.mask_name(pii["name"]),
        phone_masked=service.mask_phone(pii["phone"]),
        created_at=guardian.created_at,
        updated_at=guardian.updated_at,
    )


@router.patch("/guardians/{guardian_id}", response_model=GuardianResponse)
async def update_guardian(
    request: Request,
    guardian_id: UUID,
    data: GuardianUpdate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """보호자 정보 수정 (Operator 이상)"""
    service = GuardianService(db)
    
    guardian = await service.update(
        guardian_id=guardian_id,
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="보호자를 찾을 수 없습니다.",
        )
    
    # PII 복호화 후 마스킹하여 반환
    pii = service.decrypt_guardian_pii(guardian)
    
    return GuardianResponse(
        id=guardian.id,
        care_user_id=guardian.care_user_id,
        relationship_type=guardian.relationship_type,
        priority=guardian.priority,
        receive_notifications=guardian.receive_notifications,
        name_masked=service.mask_name(pii["name"]),
        phone_masked=service.mask_phone(pii["phone"]),
        created_at=guardian.created_at,
        updated_at=guardian.updated_at,
    )


@router.delete("/guardians/{guardian_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardian(
    request: Request,
    guardian_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """보호자 삭제 (Operator 이상)"""
    service = GuardianService(db)
    
    success = await service.delete(
        guardian_id=guardian_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="보호자를 찾을 수 없습니다.",
        )


@router.patch("/guardians/{guardian_id}/priority", response_model=GuardianResponse)
async def update_guardian_priority(
    request: Request,
    guardian_id: UUID,
    priority: int,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """보호자 콜 트리 우선순위 변경 (Operator 이상)
    
    Args:
        priority: 우선순위 (1이 가장 높음, 1-10)
    """
    if priority < 1 or priority > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="우선순위는 1-10 사이여야 합니다.",
        )
    
    service = GuardianService(db)
    
    guardian = await service.update(
        guardian_id=guardian_id,
        data=GuardianUpdate(priority=priority),
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not guardian:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="보호자를 찾을 수 없습니다.",
        )
    
    # PII 복호화 후 마스킹하여 반환
    pii = service.decrypt_guardian_pii(guardian)
    
    return GuardianResponse(
        id=guardian.id,
        care_user_id=guardian.care_user_id,
        relationship_type=guardian.relationship_type,
        priority=guardian.priority,
        receive_notifications=guardian.receive_notifications,
        name_masked=service.mask_name(pii["name"]),
        phone_masked=service.mask_phone(pii["phone"]),
        created_at=guardian.created_at,
        updated_at=guardian.updated_at,
    )
