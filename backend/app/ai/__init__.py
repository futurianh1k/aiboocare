"""
AI 서비스 모듈

- STT (Speech-to-Text): 음성 → 텍스트 변환
- LLM (Language Model): 대화 처리 및 의도 분석
- TTS (Text-to-Speech): 텍스트 → 음성 변환
- Risk Classifier: 위험도 분류

각 서비스는 추상 인터페이스를 통해 다양한 프로바이더를 지원합니다.
- OpenAI (Whisper, GPT-4, TTS)
- Google Cloud (Speech-to-Text, Text-to-Speech)
- Anthropic (Claude)
- NAVER CLOVA (한국어 특화)
"""

from app.ai.llm import LLMService, get_llm_service
from app.ai.risk_classifier import RiskClassifier, RiskLevel
from app.ai.stt import STTService, get_stt_service
from app.ai.tts import TTSService, get_tts_service

__all__ = [
    "STTService",
    "get_stt_service",
    "LLMService",
    "get_llm_service",
    "TTSService",
    "get_tts_service",
    "RiskClassifier",
    "RiskLevel",
]
