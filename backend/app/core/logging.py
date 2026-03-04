"""
로깅 설정 모듈

로깅 규칙 (ISMS-P 가이드라인):
- 로그에는 최소 정보만 기록 (user_id, action, resource_id, timestamp, IP)
- 개인정보 / 토큰 / 비밀번호 / API Key는 로그에 절대 기록 금지
- 에러 상세 스택트레이스는 내부 로그에만 기록

참고: loguru 라이브러리
https://github.com/Delgan/loguru
"""

import sys
from typing import Any, Dict

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """로깅 설정 초기화"""
    
    # 기본 핸들러 제거
    logger.remove()
    
    # 로그 포맷 설정
    if settings.LOG_FORMAT == "json":
        log_format = (
            '{{"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level": "{level}", '
            '"message": "{message}", '
            '"module": "{module}", '
            '"function": "{function}", '
            '"line": {line}}}'
        )
    else:
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
    
    # stdout 핸들러 추가
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=settings.LOG_FORMAT != "json",
        serialize=False,
    )
    
    # 파일 핸들러 추가 (프로덕션 환경)
    if settings.ENVIRONMENT == "production":
        logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # 매일 자정에 로테이션
            retention="30 days",  # 30일 보관
            compression="gz",
            format=log_format,
            level=settings.LOG_LEVEL,
        )


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """로그 데이터에서 민감 정보 제거
    
    Args:
        data: 로그에 기록할 데이터
        
    Returns:
        민감 정보가 마스킹된 데이터
    """
    sensitive_keys = {
        "password", "passwd", "pwd",
        "token", "access_token", "refresh_token",
        "secret", "secret_key", "api_key",
        "authorization", "auth",
        "ssn", "phone", "email",
        "name", "address",
        "pii_encryption_key",
    }
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized


class AuditLogger:
    """감사 로그 기록 클래스
    
    관리자 액션, 데이터 접근/변경 등을 기록합니다.
    """
    
    @staticmethod
    def log_action(
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        ip_address: str = "",
        details: Dict[str, Any] = None,
    ) -> None:
        """액션 로그 기록
        
        Args:
            user_id: 수행자 ID
            action: 액션 종류 (create, read, update, delete, login, logout 등)
            resource_type: 리소스 종류 (user, device, policy 등)
            resource_id: 리소스 ID
            ip_address: 클라이언트 IP
            details: 추가 상세 정보 (민감정보 제외)
        """
        log_entry = {
            "audit": True,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "ip_address": ip_address,
        }
        
        if details:
            log_entry["details"] = sanitize_log_data(details)
        
        logger.info(f"AUDIT: {log_entry}")
    
    @staticmethod
    def log_admin_action(
        admin_id: str,
        action: str,
        target_type: str,
        target_id: str,
        ip_address: str = "",
        changes: Dict[str, Any] = None,
    ) -> None:
        """관리자 액션 로그 기록
        
        모든 Admin 액션은 감사 로그에 기록됩니다 (ISMS-P 요구사항).
        """
        log_entry = {
            "audit": True,
            "admin_action": True,
            "admin_id": admin_id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "ip_address": ip_address,
        }
        
        if changes:
            log_entry["changes"] = sanitize_log_data(changes)
        
        logger.warning(f"ADMIN_AUDIT: {log_entry}")


# 전역 감사 로거 인스턴스
audit_logger = AuditLogger()
