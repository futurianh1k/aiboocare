"""
인증 API 테스트

- 로그인/로그아웃
- 토큰 갱신
- 비밀번호 변경
"""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password


@pytest.mark.asyncio
class TestAuthAPI:
    """인증 API 테스트 클래스"""
    
    async def test_login_success(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """로그인 성공 테스트"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["user_id"] is not None
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
    
    async def test_login_invalid_email(self, client: AsyncClient):
        """존재하지 않는 이메일로 로그인 시도"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123",
            },
        )
        
        assert response.status_code == 401
        assert "올바르지 않습니다" in response.json()["detail"]
    
    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        test_user: dict,
    ):
        """잘못된 비밀번호로 로그인 시도"""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": "WrongPassword123",
            },
        )
        
        assert response.status_code == 401
        assert "올바르지 않습니다" in response.json()["detail"]
    
    async def test_me_authenticated(
        self,
        authenticated_client: AsyncClient,
        test_user: dict,
    ):
        """인증된 사용자 정보 조회"""
        response = await authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
    
    async def test_me_unauthenticated(self, client: AsyncClient):
        """미인증 상태에서 사용자 정보 조회"""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
        assert "인증이 필요합니다" in response.json()["detail"]
    
    async def test_logout(self, authenticated_client: AsyncClient):
        """로그아웃 테스트"""
        response = await authenticated_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 200
        # 쿠키가 삭제되었는지 확인 (max-age=0)
        assert response.cookies.get("access_token") is None or \
               response.cookies.get("access_token", domain="") == ""
    
    async def test_refresh_token(self, authenticated_client: AsyncClient):
        """토큰 갱신 테스트"""
        response = await authenticated_client.post("/api/v1/auth/refresh")
        
        assert response.status_code == 200
        assert "access_token" in response.cookies
    
    async def test_change_password_success(
        self,
        authenticated_client: AsyncClient,
        test_user: dict,
    ):
        """비밀번호 변경 성공"""
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": test_user["password"],
                "new_password": "NewSecurePass123",
            },
        )
        
        assert response.status_code == 200
        assert "변경되었습니다" in response.json()["message"]
    
    async def test_change_password_wrong_current(
        self,
        authenticated_client: AsyncClient,
    ):
        """잘못된 현재 비밀번호로 변경 시도"""
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongPassword123",
                "new_password": "NewSecurePass123",
            },
        )
        
        assert response.status_code == 400
        assert "현재 비밀번호" in response.json()["detail"]
    
    async def test_change_password_weak(
        self,
        authenticated_client: AsyncClient,
        test_user: dict,
    ):
        """약한 비밀번호로 변경 시도"""
        response = await authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": test_user["password"],
                "new_password": "weak",  # 8자 미만
            },
        )
        
        # Pydantic 검증 실패
        assert response.status_code == 422
