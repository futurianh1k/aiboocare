"""
인증 API 엔드포인트

- POST /login - 로그인
- POST /logout - 로그아웃
- POST /refresh - 토큰 갱신
- GET /me - 현재 사용자 정보
- POST /change-password - 비밀번호 변경

보안 규칙:
- Access Token: HttpOnly + Secure + SameSite 쿠키
- Refresh Token: HttpOnly + Secure + SameSite 쿠키
- 토큰 값은 응답 본문에 포함하지 않음
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    PasswordChangeRequest,
    TokenRefreshResponse,
)
from app.services.auth import AuthService

router = APIRouter()


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
) -> None:
    """인증 쿠키 설정
    
    HttpOnly + Secure + SameSite 쿠키로 토큰 전달
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=settings.COOKIE_HTTPONLY,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth",  # Refresh Token은 auth 경로에서만 전송
    )


def clear_auth_cookies(response: Response) -> None:
    """인증 쿠키 제거"""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """로그인
    
    이메일/비밀번호로 인증 후 JWT 토큰을 HttpOnly 쿠키로 발급합니다.
    
    Note: 토큰 값은 응답 본문에 포함되지 않습니다 (보안).
    """
    auth_service = AuthService(db)
    client_ip = get_client_ip(request)
    
    user = await auth_service.authenticate(
        email=login_data.email,
        password=login_data.password,
        ip_address=client_ip,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    
    # 토큰 발급
    access_token, refresh_token = await auth_service.create_tokens(user)
    
    # 쿠키 설정
    set_auth_cookies(response, access_token, refresh_token)
    
    return LoginResponse(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """로그아웃
    
    Refresh Token을 무효화하고 쿠키를 제거합니다.
    """
    auth_service = AuthService(db)
    client_ip = get_client_ip(request)
    
    await auth_service.logout(
        user_id=current_user["user_id"],
        ip_address=client_ip,
    )
    
    # 쿠키 제거
    clear_auth_cookies(response)
    
    return LogoutResponse()


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    """토큰 갱신
    
    Refresh Token을 사용하여 새로운 Access/Refresh Token을 발급합니다.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token이 없습니다.",
        )
    
    auth_service = AuthService(db)
    client_ip = get_client_ip(request)
    
    result = await auth_service.refresh_tokens(
        refresh_token=refresh_token,
        ip_address=client_ip,
    )
    
    if not result:
        # 토큰 갱신 실패 - 쿠키 제거
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 갱신에 실패했습니다. 다시 로그인해 주세요.",
        )
    
    new_access_token, new_refresh_token, user = result
    
    # 새 쿠키 설정
    set_auth_cookies(response, new_access_token, new_refresh_token)
    
    return TokenRefreshResponse()


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """현재 로그인한 사용자 정보 조회"""
    from uuid import UUID
    
    from sqlalchemy import select
    
    from app.models.user import AdminUser
    
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == UUID(current_user["user_id"]))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    
    return CurrentUserResponse(
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
    )


@router.post("/change-password")
async def change_password(
    request: Request,
    response: Response,
    password_data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """비밀번호 변경
    
    비밀번호 변경 후 모든 세션이 무효화됩니다.
    """
    # 비밀번호 강도 검증
    if not password_data.validate_password_strength():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비밀번호는 8자 이상, 대문자/소문자/숫자를 포함해야 합니다.",
        )
    
    auth_service = AuthService(db)
    client_ip = get_client_ip(request)
    
    success = await auth_service.change_password(
        user_id=current_user["user_id"],
        current_password=password_data.current_password,
        new_password=password_data.new_password,
        ip_address=client_ip,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )
    
    # 쿠키 제거 (재로그인 필요)
    clear_auth_cookies(response)
    
    return {"message": "비밀번호가 변경되었습니다. 다시 로그인해 주세요."}
