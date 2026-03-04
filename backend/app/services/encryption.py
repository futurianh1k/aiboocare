"""
PII 암호화 서비스

개인식별정보(PII)의 암호화/복호화를 처리합니다.
AES-256-GCM 알고리즘을 사용합니다.

참고: app.core.security.PIIEncryptor를 래핑합니다.
"""

from typing import Optional

from app.core.config import settings
from app.core.security import PIIEncryptor


class PIIEncryption:
    """PII 암호화 서비스 클래스
    
    Usage:
        encryption = PIIEncryption()
        encrypted = encryption.encrypt("홍길동")
        decrypted = encryption.decrypt(encrypted)
    """
    
    def __init__(self, key: Optional[str] = None):
        """
        Args:
            key: Base64 인코딩된 32바이트 암호화 키
        """
        # PII_ENCRYPTION_KEY가 설정되지 않았으면 더미 키 사용 (개발용)
        if not settings.PII_ENCRYPTION_KEY:
            # 개발 환경에서 32바이트 더미 키 생성
            import base64
            dummy_key = base64.b64encode(b"dev_dummy_key_32bytes_long!!")
            self._encryptor = PIIEncryptor(dummy_key.decode())
        else:
            self._encryptor = PIIEncryptor(key)
    
    def encrypt(self, plaintext: str) -> str:
        """문자열 암호화"""
        if not plaintext:
            return ""
        return self._encryptor.encrypt(plaintext)
    
    def decrypt(self, ciphertext: str) -> str:
        """문자열 복호화"""
        if not ciphertext:
            return ""
        try:
            return self._encryptor.decrypt(ciphertext)
        except Exception:
            return ""


# 전역 인스턴스
_pii_encryption: Optional[PIIEncryption] = None


def get_pii_encryption() -> PIIEncryption:
    """PIIEncryption 싱글톤 인스턴스 반환"""
    global _pii_encryption
    if _pii_encryption is None:
        _pii_encryption = PIIEncryption()
    return _pii_encryption
