"""
보안 유틸리티 테스트

비밀번호 해싱, JWT, PII 암호화 테스트
"""

import base64
import secrets

import pytest

from app.core.security import (
    PIIEncryptor,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


class TestPasswordHashing:
    """비밀번호 해싱 테스트"""
    
    def test_hash_password(self):
        """비밀번호 해싱 테스트"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # BCrypt prefix
    
    def test_verify_password_correct(self):
        """올바른 비밀번호 검증"""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_wrong(self):
        """잘못된 비밀번호 검증"""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestJWT:
    """JWT 토큰 테스트"""
    
    def test_create_access_token(self):
        """Access Token 생성 테스트"""
        data = {"user_id": "test-user-123", "role": "admin"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
    
    def test_decode_access_token(self):
        """Access Token 디코딩 테스트"""
        data = {"user_id": "test-user-123", "role": "admin"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["user_id"] == "test-user-123"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
    
    def test_create_refresh_token(self):
        """Refresh Token 생성 테스트"""
        data = {"user_id": "test-user-123"}
        token = create_refresh_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["type"] == "refresh"
    
    def test_decode_invalid_token(self):
        """유효하지 않은 토큰 디코딩"""
        invalid_token = "invalid.token.here"
        
        payload = decode_token(invalid_token)
        
        assert payload is None


class TestPIIEncryption:
    """PII 암호화 테스트"""
    
    @pytest.fixture
    def encryptor(self):
        """테스트용 암호화 인스턴스"""
        # 32바이트 테스트 키 생성
        test_key = base64.b64encode(secrets.token_bytes(32)).decode()
        return PIIEncryptor(key=test_key)
    
    def test_encrypt_decrypt(self, encryptor):
        """암호화/복호화 테스트"""
        plaintext = "홍길동"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert encrypted != plaintext
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self, encryptor):
        """빈 문자열 암호화"""
        encrypted = encryptor.encrypt("")
        
        assert encrypted == ""
    
    def test_decrypt_empty_string(self, encryptor):
        """빈 문자열 복호화"""
        decrypted = encryptor.decrypt("")
        
        assert decrypted == ""
    
    def test_encrypt_unicode(self, encryptor):
        """유니코드 문자열 암호화"""
        plaintext = "테스트 유저 이름 🎉"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_different_encryptions_for_same_value(self, encryptor):
        """동일 값에 대해 다른 암호문 생성 (nonce 사용)"""
        plaintext = "테스트"
        
        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)
        
        # 같은 평문이어도 다른 암호문이 나와야 함 (nonce가 다르므로)
        assert encrypted1 != encrypted2
        
        # 하지만 둘 다 같은 값으로 복호화됨
        assert encryptor.decrypt(encrypted1) == encryptor.decrypt(encrypted2)


class TestRefreshTokenHash:
    """Refresh Token 해싱 테스트"""
    
    def test_hash_refresh_token(self):
        """Refresh Token 해싱"""
        token = "some.refresh.token.value"
        
        hashed = hash_refresh_token(token)
        
        assert hashed != token
        assert len(hashed) == 64  # SHA256 hex digest
    
    def test_same_token_same_hash(self):
        """동일 토큰은 동일 해시"""
        token = "some.refresh.token.value"
        
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)
        
        assert hash1 == hash2
