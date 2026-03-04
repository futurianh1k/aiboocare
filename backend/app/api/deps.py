"""
FastAPI 의존성 주입 모듈

공통 의존성:
- 데이터베이스 세션
- 현재 사용자 인증
- Role 기반 권한 검사
"""

from typing import AsyncGenerator, Optional

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import audit_logger
from app.core.security import decode_token
from app.db.session import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """데이터베이스 세션 의존성
    
    Yields:
        AsyncSession: 비동기 SQLAlchemy 세션
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user_optional(
    access_token: Optional[str] = Cookie(None, alias="access_token"),
) -> Optional[dict]:
    """현재 사용자 정보 반환 (선택적)
    
    토큰이 없거나 유효하지 않으면 None 반환
    """
    if not access_token:
        return None
    
    payload = decode_token(access_token)
    if not payload or payload.get("type") != "access":
        return None
    
    return payload


async def get_current_user(
    access_token: Optional[str] = Cookie(None, alias="access_token"),
) -> dict:
    """현재 인증된 사용자 정보 반환 (필수)
    
    Args:
        access_token: HttpOnly 쿠키로 전달된 JWT 토큰
        
    Returns:
        사용자 payload (user_id, role 포함)
        
    Raises:
        HTTPException: 인증 실패 시 401
        
    Note:
        에러 메시지에 토큰 값을 포함하지 않습니다.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다.",
        )
    
    payload = decode_token(access_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다.",
        )
    
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰 유형입니다.",
        )
    
    return payload


class RoleChecker:
    """Role 기반 권한 검사 의존성 클래스
    
    사용 예:
        @router.get("/admin")
        async def admin_endpoint(
            user: dict = Depends(RoleChecker(["admin"]))
        ):
            ...
    """
    
    def __init__(self, allowed_roles: list[str]):
        """
        Args:
            allowed_roles: 허용할 Role 목록
        """
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        """권한 검사 실행
        
        Args:
            current_user: 현재 인증된 사용자
            
        Returns:
            사용자 정보 (권한 검사 통과 시)
            
        Raises:
            HTTPException: 권한 없음 시 403
        """
        user_role = current_user.get("role", "")
        
        if user_role not in self.allowed_roles:
            # 감사 로그 기록 (권한 없는 접근 시도)
            audit_logger.log_action(
                user_id=current_user.get("user_id", "unknown"),
                action="access_denied",
                resource_type="endpoint",
                resource_id="",
                details={"required_roles": self.allowed_roles, "user_role": user_role},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 작업을 수행할 권한이 없습니다.",
            )
        
        return current_user


# 편의 의존성 인스턴스
require_admin = RoleChecker(["admin"])
require_operator = RoleChecker(["admin", "operator"])
require_guardian = RoleChecker(["admin", "operator", "guardian"])


def require_roles(allowed_roles: list) -> RoleChecker:
    """Role 기반 권한 검사 의존성 함수
    
    사용 예:
        @router.get("/admin")
        async def admin_endpoint(
            user: dict = Depends(require_roles([UserRole.ADMIN]))
        ):
            ...
    
    Args:
        allowed_roles: 허용할 Role 목록 (UserRole enum 또는 문자열)
        
    Returns:
        RoleChecker 인스턴스
    """
    # UserRole enum을 문자열로 변환
    role_strings = [
        r.value if hasattr(r, 'value') else str(r)
        for r in allowed_roles
    ]
    return RoleChecker(role_strings)
