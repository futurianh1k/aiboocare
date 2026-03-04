"""
인증 관련 Pydantic 스키마

- 로그인 요청/응답
- 토큰 갱신
- 현재 사용자 정보
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """로그인 요청 스키마"""
    email: EmailStr = Field(..., description="이메일")
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")


class LoginResponse(BaseModel):
    """로그인 응답 스키마
    
    Note: Access Token은 HttpOnly 쿠키로 전달되므로 응답 본문에 포함하지 않습니다.
    """
    message: str = "로그인 성공"
    user_id: str
    email: str
    name: str
    role: str


class TokenRefreshResponse(BaseModel):
    """토큰 갱신 응답 스키마"""
    message: str = "토큰 갱신 성공"


class CurrentUserResponse(BaseModel):
    """현재 사용자 정보 응답 스키마"""
    user_id: str
    email: str
    name: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None


class LogoutResponse(BaseModel):
    """로그아웃 응답 스키마"""
    message: str = "로그아웃 성공"


class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청 스키마"""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    
    def validate_password_strength(self) -> bool:
        """비밀번호 강도 검증
        
        최소 요구사항:
        - 8자 이상
        - 대문자 포함
        - 소문자 포함
        - 숫자 포함
        """
        pwd = self.new_password
        return (
            len(pwd) >= 8 and
            any(c.isupper() for c in pwd) and
            any(c.islower() for c in pwd) and
            any(c.isdigit() for c in pwd)
        )
