"""
애플리케이션 설정 관리
참고: pydantic-settings 라이브러리를 사용한 환경변수 기반 설정
https://docs.pydantic.dev/latest/concepts/pydantic_settings/
"""

from functools import lru_cache
from typing import Any, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 설정 클래스
    
    환경변수 또는 .env 파일에서 설정값을 로드합니다.
    민감한 정보(시크릿)는 환경변수/Secret Manager를 통해 관리합니다.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ============== 앱 기본 설정 ==============
    APP_NAME: str = "AI Care Companion"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # ============== API 설정 ==============
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # ============== 데이터베이스 설정 ==============
    # PostgreSQL + TimescaleDB
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_USER: str = "aiboocare"
    DATABASE_PASSWORD: str = ""  # 환경변수로 주입 필수
    DATABASE_NAME: str = "aiboocare"
    
    @property
    def DATABASE_URL(self) -> str:
        """SQLAlchemy 데이터베이스 URL (동기)"""
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """SQLAlchemy 데이터베이스 URL (비동기)"""
        return (
            f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )
    
    # ============== Redis 설정 ==============
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        """Redis 연결 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ============== MQTT 설정 ==============
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_CLIENT_ID: str = "aiboocare-backend"
    
    # ============== JWT/인증 설정 ==============
    SECRET_KEY: str = ""  # 환경변수로 주입 필수 (최소 32자)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ============== 암호화 설정 ==============
    # PII 필드 암호화용 키 (AES-256-GCM)
    PII_ENCRYPTION_KEY: str = ""  # 환경변수로 주입 필수 (32바이트 base64 인코딩)
    
    # ============== 로깅 설정 ==============
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json 또는 text
    
    # ============== 보안 설정 ==============
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Cookie 설정
    COOKIE_SECURE: bool = True  # HTTPS only
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "lax"  # strict, lax, none
    
    # ============== AI 서비스 설정 ==============
    # OpenAI
    OPENAI_API_KEY: str = ""  # 환경변수로 주입
    OPENAI_MODEL: str = "gpt-4o-mini"  # 대화 처리용 모델
    OPENAI_STT_MODEL: str = "whisper-1"  # STT 모델
    OPENAI_TTS_MODEL: str = "tts-1"  # TTS 모델
    OPENAI_TTS_VOICE: str = "nova"  # TTS 음성 (alloy, echo, fable, onyx, nova, shimmer)
    
    # Google Cloud (STT/TTS 대안)
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    
    # Anthropic Claude (LLM 대안)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    
    # CLOVA (네이버, 한국어 TTS 대안)
    CLOVA_CLIENT_ID: str = ""
    CLOVA_CLIENT_SECRET: str = ""
    
    # AI 서비스 선택 (기본 프로바이더)
    AI_STT_PROVIDER: str = "openai"  # openai, google
    AI_LLM_PROVIDER: str = "openai"  # openai, anthropic
    AI_TTS_PROVIDER: str = "openai"  # openai, google, clova
    
    # AI 서비스 공통 설정
    AI_MAX_AUDIO_DURATION_SECONDS: int = 300  # 최대 오디오 길이 (5분)
    AI_MAX_TEXT_LENGTH: int = 4000  # 최대 텍스트 길이
    AI_TEMPERATURE: float = 0.7  # LLM 창의성 (0.0~2.0)
    AI_MAX_TOKENS: int = 1024  # LLM 최대 응답 토큰
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """SECRET_KEY 검증 - 프로덕션에서는 반드시 설정 필요"""
        if not v and cls.model_config.get("env_prefix", "") != "TEST_":
            # 테스트 환경이 아닌 경우 경고
            import warnings
            warnings.warn(
                "SECRET_KEY가 설정되지 않았습니다. 프로덕션 환경에서는 반드시 설정해야 합니다.",
                UserWarning,
            )
        return v


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 반환 (캐싱)"""
    return Settings()


# 전역 설정 인스턴스
settings = get_settings()
