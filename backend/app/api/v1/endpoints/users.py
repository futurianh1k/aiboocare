"""
사용자 관리 API 엔드포인트

- AdminUser CRUD (관리자/운영자)
- CareUser CRUD (대상자/독거노인)

보안 규칙:
- 모든 Admin 액션은 Audit Log에 기록
- PII 접근은 권한 검증 후에만 허용
- 목록 조회 시 PII는 마스킹하여 반환
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin, require_operator
from app.schemas.user import (
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    CareUserCreate,
    CareUserDetailResponse,
    CareUserResponse,
    CareUserUpdate,
)
from app.services.user import AdminUserService, CareUserService

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


# ============== AdminUser API ==============

@router.get("/admin", response_model=List[AdminUserResponse])
async def list_admin_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """관리자 목록 조회 (Admin 전용)"""
    service = AdminUserService(db)
    users = await service.list_all(skip=skip, limit=limit)
    return users


@router.get("/admin/{user_id}", response_model=AdminUserResponse)
async def get_admin_user(
    user_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """관리자 상세 조회 (Admin 전용)"""
    service = AdminUserService(db)
    user = await service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="관리자를 찾을 수 없습니다.",
        )
    
    return user


@router.post("/admin", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    request: Request,
    data: AdminUserCreate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """관리자 생성 (Admin 전용)"""
    service = AdminUserService(db)
    
    try:
        user = await service.create(
            data=data,
            current_user_id=current_user["user_id"],
            ip_address=get_client_ip(request),
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/admin/{user_id}", response_model=AdminUserResponse)
async def update_admin_user(
    request: Request,
    user_id: UUID,
    data: AdminUserUpdate,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """관리자 정보 수정 (Admin 전용)"""
    service = AdminUserService(db)
    
    user = await service.update(
        user_id=user_id,
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="관리자를 찾을 수 없습니다.",
        )
    
    return user


@router.delete("/admin/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    request: Request,
    user_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """관리자 삭제 (Admin 전용)"""
    service = AdminUserService(db)
    
    success = await service.delete(
        user_id=user_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="관리자를 찾을 수 없습니다.",
        )


# ============== CareUser API ==============

@router.get("/care", response_model=List[CareUserResponse])
async def list_care_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """대상자 목록 조회 (Operator 이상)
    
    PII는 제외하고 반환합니다.
    """
    service = CareUserService(db)
    users = await service.list_all(skip=skip, limit=limit, is_active=is_active)
    return users


@router.get("/care/{user_id}", response_model=CareUserResponse)
async def get_care_user(
    user_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """대상자 기본 정보 조회 (Operator 이상)
    
    PII는 제외하고 반환합니다.
    """
    service = CareUserService(db)
    user = await service.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상자를 찾을 수 없습니다.",
        )
    
    return user


@router.get("/care/{user_id}/detail", response_model=CareUserDetailResponse)
async def get_care_user_detail(
    user_id: UUID,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """대상자 상세 정보 조회 (PII 포함, Operator 이상)
    
    PII를 복호화하여 반환합니다.
    이 API 호출은 Audit Log에 기록됩니다.
    """
    from app.core.logging import audit_logger
    
    service = CareUserService(db)
    user = await service.get_by_id(user_id, include_pii=True)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상자를 찾을 수 없습니다.",
        )
    
    # PII 접근 감사 기록
    audit_logger.log_action(
        user_id=current_user["user_id"],
        action="care_user_pii_accessed",
        resource_type="care_user",
        resource_id=str(user_id),
    )
    
    # PII 복호화
    pii = service.decrypt_user_pii(user)
    
    return CareUserDetailResponse(
        id=user.id,
        code=user.code,
        consent_status=user.consent_status.value,
        consent_date=user.consent_date,
        is_active=user.is_active,
        notes=user.notes,
        created_at=user.created_at,
        updated_at=user.updated_at,
        name=pii.get("name", ""),
        phone=pii.get("phone"),
        address=pii.get("address"),
        birth_date=pii.get("birth_date"),
        emergency_contact=pii.get("emergency_contact"),
    )


@router.post("/care", response_model=CareUserResponse, status_code=status.HTTP_201_CREATED)
async def create_care_user(
    request: Request,
    data: CareUserCreate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """대상자 등록 (Operator 이상)
    
    PII는 암호화하여 저장됩니다.
    """
    service = CareUserService(db)
    
    try:
        user = await service.create(
            data=data,
            current_user_id=current_user["user_id"],
            ip_address=get_client_ip(request),
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.patch("/care/{user_id}", response_model=CareUserResponse)
async def update_care_user(
    request: Request,
    user_id: UUID,
    data: CareUserUpdate,
    current_user: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db),
):
    """대상자 정보 수정 (Operator 이상)"""
    service = CareUserService(db)
    
    user = await service.update(
        user_id=user_id,
        data=data,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상자를 찾을 수 없습니다.",
        )
    
    return user


@router.delete("/care/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_care_user(
    request: Request,
    user_id: UUID,
    current_user: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """대상자 삭제 (Admin 전용)"""
    service = CareUserService(db)
    
    success = await service.delete(
        user_id=user_id,
        current_user_id=current_user["user_id"],
        ip_address=get_client_ip(request),
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대상자를 찾을 수 없습니다.",
        )
