"""
AI 서비스 기본 인터페이스 및 공통 타입

모든 AI 서비스의 기본 클래스와 공통 데이터 타입을 정의합니다.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AIProvider(str, Enum):
    """AI 서비스 프로바이더"""
    OPENAI = "openai"
    GOOGLE = "google"
    ANTHROPIC = "anthropic"
    CLOVA = "clova"


@dataclass
class AIServiceResult:
    """AI 서비스 결과 기본 클래스"""
    success: bool
    provider: str
    model: str
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class STTResult(AIServiceResult):
    """STT 결과"""
    text: str = ""
    language: str = "ko"
    confidence: float = 0.0
    segments: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LLMResult(AIServiceResult):
    """LLM 결과"""
    response: str = ""
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    usage: Dict[str, int] = field(default_factory=dict)  # tokens


@dataclass
class TTSResult(AIServiceResult):
    """TTS 결과"""
    audio_data: bytes = b""
    audio_format: str = "mp3"
    duration_seconds: float = 0.0


class BaseAIService(ABC):
    """AI 서비스 기본 추상 클래스"""
    
    provider: AIProvider
    
    @abstractmethod
    async def health_check(self) -> bool:
        """서비스 상태 확인"""
        pass
    
    def _measure_latency(self, start_time: datetime) -> float:
        """지연시간 측정 (ms)"""
        return (datetime.utcnow() - start_time).total_seconds() * 1000
