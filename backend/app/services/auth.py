"""
인증 서비스

- 로그인/로그아웃
- 토큰 관리
- 비밀번호 변경

참고: ISMS-P 보안 가이드라인 준수
- 비밀번호 BCrypt 해싱
- JWT HttpOnly 쿠키
- Refresh Token DB 해시 저장
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import audit_logger, logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.user import AdminUser


class AuthService:
    """인증 서비스 클래스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str = "",
    ) -> Optional[AdminUser]:
        """사용자 인증
        
        Args:
            email: 이메일
            password: 비밀번호
            ip_address: 클라이언트 IP (감사 로그용)
            
        Returns:
            인증 성공 시 AdminUser, 실패 시 None
            
        Note:
            비밀번호는 로그에 절대 기록하지 않습니다.
        """
        # 이메일로 사용자 조회
        result = await self.db.execute(
            select(AdminUser).where(
                AdminUser.email == email,
                AdminUser.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # 사용자 없음 - 타이밍 공격 방지를 위해 해시 검증 수행
            verify_password(password, "$2b$12$dummy.hash.for.timing.attack")
            logger.warning(f"Login failed: user not found (email masked)")
            return None
        
        if not user.is_active:
            logger.warning(f"Login failed: user inactive (user_id={user.id})")
            return None
        
        if not verify_password(password, user.password_hash):
            logger.warning(f"Login failed: invalid password (user_id={user.id})")
            audit_logger.log_action(
                user_id=str(user.id),
                action="login_failed",
                resource_type="admin_user",
                resource_id=str(user.id),
                ip_address=ip_address,
            )
            return None
        
        # 로그인 성공 - 마지막 로그인 시간 업데이트
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=str(user.id),
            action="login_success",
            resource_type="admin_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return user
    
    async def create_tokens(
        self,
        user: AdminUser,
    ) -> tuple[str, str]:
        """Access Token과 Refresh Token 생성
        
        Args:
            user: 인증된 사용자
            
        Returns:
            (access_token, refresh_token) 튜플
        """
        token_data = {
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Refresh Token 해시를 DB에 저장
        user.refresh_token_hash = hash_refresh_token(refresh_token)
        await self.db.commit()
        
        return access_token, refresh_token
    
    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: str = "",
    ) -> Optional[tuple[str, str, AdminUser]]:
        """토큰 갱신
        
        Args:
            refresh_token: 현재 Refresh Token
            ip_address: 클라이언트 IP
            
        Returns:
            성공 시 (new_access_token, new_refresh_token, user), 실패 시 None
        """
        payload = decode_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            logger.warning("Token refresh failed: invalid token")
            return None
        
        user_id = payload.get("user_id")
        if not user_id:
            return None
        
        # 사용자 조회
        result = await self.db.execute(
            select(AdminUser).where(
                AdminUser.id == UUID(user_id),
                AdminUser.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            logger.warning(f"Token refresh failed: user invalid (user_id={user_id})")
            return None
        
        # DB에 저장된 해시와 비교 (토큰 재사용 공격 방지)
        current_hash = hash_refresh_token(refresh_token)
        if user.refresh_token_hash != current_hash:
            logger.warning(f"Token refresh failed: token mismatch (user_id={user_id})")
            # 잠재적 토큰 도용 - Refresh Token 무효화
            user.refresh_token_hash = None
            await self.db.commit()
            return None
        
        # 새 토큰 발급
        access_token, new_refresh_token = await self.create_tokens(user)
        
        audit_logger.log_action(
            user_id=str(user.id),
            action="token_refresh",
            resource_type="admin_user",
            resource_id=str(user.id),
            ip_address=ip_address,
        )
        
        return access_token, new_refresh_token, user
    
    async def logout(
        self,
        user_id: str,
        ip_address: str = "",
    ) -> bool:
        """로그아웃 (Refresh Token 무효화)
        
        Args:
            user_id: 사용자 ID
            ip_address: 클라이언트 IP
            
        Returns:
            성공 여부
        """
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Refresh Token 해시 제거
        user.refresh_token_hash = None
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=user_id,
            action="logout",
            resource_type="admin_user",
            resource_id=user_id,
            ip_address=ip_address,
        )
        
        return True
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
        ip_address: str = "",
    ) -> bool:
        """비밀번호 변경
        
        Args:
            user_id: 사용자 ID
            current_password: 현재 비밀번호
            new_password: 새 비밀번호
            ip_address: 클라이언트 IP
            
        Returns:
            성공 여부
        """
        result = await self.db.execute(
            select(AdminUser).where(AdminUser.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # 현재 비밀번호 확인
        if not verify_password(current_password, user.password_hash):
            logger.warning(f"Password change failed: invalid current password (user_id={user_id})")
            return False
        
        # 새 비밀번호 해싱 및 저장
        user.password_hash = hash_password(new_password)
        # 비밀번호 변경 시 모든 세션 무효화
        user.refresh_token_hash = None
        await self.db.commit()
        
        audit_logger.log_action(
            user_id=user_id,
            action="password_changed",
            resource_type="admin_user",
            resource_id=user_id,
            ip_address=ip_address,
        )
        
        return True
