"""
보안 유틸리티 모듈
- 비밀번호 해싱 (BCrypt)
- JWT 토큰 생성/검증
- PII 필드 암호화 (AES-256-GCM)

참고:
- passlib: https://passlib.readthedocs.io/
- python-jose: https://python-jose.readthedocs.io/
- cryptography: https://cryptography.io/
"""

import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ============== 비밀번호 해싱 ==============
# BCrypt 사용 (ISMS-P 권장)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """비밀번호를 BCrypt로 해싱
    
    Args:
        password: 평문 비밀번호
        
    Returns:
        해싱된 비밀번호 문자열
    """
    return pwd_context.hash(password)


# Alias for backward compatibility
get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증
    
    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해싱된 비밀번호
        
    Returns:
        일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============== JWT 토큰 ==============
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Access Token 생성
    
    Args:
        data: 토큰에 포함할 데이터 (user_id, role 등)
        expires_delta: 만료 시간 (기본값: 설정에서 로드)
        
    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Refresh Token 생성
    
    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 만료 시간 (기본값: 설정에서 로드)
        
    Returns:
        JWT 토큰 문자열
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT 토큰 디코딩 및 검증
    
    Args:
        token: JWT 토큰 문자열
        
    Returns:
        디코딩된 payload 또는 None (검증 실패 시)
        
    Note:
        토큰 값은 로그에 절대 기록하지 않습니다.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except JWTError:
        return None


# ============== PII 암호화 (AES-256-GCM) ==============
class PIIEncryptor:
    """PII(개인식별정보) 필드 암호화 클래스
    
    AES-256-GCM 알고리즘을 사용하여 민감한 개인정보를 암호화합니다.
    
    사용 예:
        encryptor = PIIEncryptor()
        encrypted = encryptor.encrypt("홍길동")
        decrypted = encryptor.decrypt(encrypted)
    """
    
    def __init__(self, key: Optional[str] = None):
        """
        Args:
            key: Base64 인코딩된 32바이트 암호화 키
                 (미지정 시 설정에서 로드)
        """
        key_str = key or settings.PII_ENCRYPTION_KEY
        if not key_str:
            raise ValueError(
                "PII_ENCRYPTION_KEY가 설정되지 않았습니다. "
                "환경변수 또는 .env 파일에서 설정해주세요."
            )
        self._key = base64.b64decode(key_str)
        if len(self._key) != 32:
            raise ValueError("PII_ENCRYPTION_KEY는 32바이트여야 합니다.")
        self._aesgcm = AESGCM(self._key)
    
    def encrypt(self, plaintext: str) -> str:
        """문자열 암호화
        
        Args:
            plaintext: 암호화할 평문 문자열
            
        Returns:
            Base64 인코딩된 암호문 (nonce:ciphertext 형식)
        """
        if not plaintext:
            return ""
        
        # 12바이트 난수 nonce 생성
        nonce = secrets.token_bytes(12)
        
        # 암호화
        ciphertext = self._aesgcm.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            None,  # associated_data
        )
        
        # nonce + ciphertext를 Base64로 인코딩
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("ascii")
    
    def decrypt(self, encrypted: str) -> str:
        """문자열 복호화
        
        Args:
            encrypted: Base64 인코딩된 암호문
            
        Returns:
            복호화된 평문 문자열
        """
        if not encrypted:
            return ""
        
        try:
            # Base64 디코딩
            combined = base64.b64decode(encrypted)
            
            # nonce와 ciphertext 분리
            nonce = combined[:12]
            ciphertext = combined[12:]
            
            # 복호화
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception:
            # 복호화 실패 시 예외를 다시 던지지 않고 빈 문자열 반환
            # (로그에 민감 정보 노출 방지)
            raise ValueError("복호화에 실패했습니다.")


# 전역 암호화 인스턴스 (lazy initialization)
_pii_encryptor: Optional[PIIEncryptor] = None


def get_pii_encryptor() -> PIIEncryptor:
    """PII 암호화 인스턴스 반환 (싱글톤)"""
    global _pii_encryptor
    if _pii_encryptor is None:
        _pii_encryptor = PIIEncryptor()
    return _pii_encryptor


def encrypt_pii(value: str) -> str:
    """PII 값 암호화 헬퍼 함수"""
    return get_pii_encryptor().encrypt(value)


def decrypt_pii(value: str) -> str:
    """PII 값 복호화 헬퍼 함수"""
    return get_pii_encryptor().decrypt(value)


# ============== Refresh Token 해싱 ==============
def hash_refresh_token(token: str) -> str:
    """Refresh Token을 DB 저장용으로 해싱
    
    Refresh Token은 원본을 클라이언트에만 전달하고,
    서버에는 해시값만 저장합니다.
    """
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()
