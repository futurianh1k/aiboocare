"""
STT (Speech-to-Text) 서비스

음성 데이터를 텍스트로 변환합니다.

지원 프로바이더:
- OpenAI Whisper
- Google Cloud Speech-to-Text

참고:
- 한국어 음성 인식에 최적화
- 응급 키워드 감지를 위한 정확한 전사 필요
"""

import io
from abc import abstractmethod
from datetime import datetime
from typing import BinaryIO, Optional, Union

from app.ai.base import AIProvider, BaseAIService, STTResult
from app.core.config import settings
from app.core.logging import logger


class STTService(BaseAIService):
    """STT 서비스 추상 클래스"""
    
    @abstractmethod
    async def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: str = "ko",
        audio_format: str = "wav",
    ) -> STTResult:
        """음성을 텍스트로 변환
        
        Args:
            audio_data: 오디오 데이터 (bytes 또는 파일 객체)
            language: 언어 코드 (기본: ko)
            audio_format: 오디오 포맷 (wav, mp3, webm 등)
            
        Returns:
            STTResult: 변환 결과
        """
        pass


class OpenAISTTService(STTService):
    """OpenAI Whisper STT 서비스"""
    
    provider = AIProvider.OPENAI
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_STT_MODEL
        self._client = None
    
    @property
    def client(self):
        """OpenAI 클라이언트 (lazy loading)"""
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client
    
    async def health_check(self) -> bool:
        """서비스 상태 확인"""
        try:
            # 간단한 API 호출로 확인
            return bool(self.api_key)
        except Exception:
            return False
    
    async def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: str = "ko",
        audio_format: str = "wav",
    ) -> STTResult:
        """OpenAI Whisper로 음성 변환"""
        start_time = datetime.utcnow()
        
        try:
            # bytes를 파일 객체로 변환
            if isinstance(audio_data, bytes):
                audio_file = io.BytesIO(audio_data)
                audio_file.name = f"audio.{audio_format}"
            else:
                audio_file = audio_data
            
            # Whisper API 호출
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=language,
                response_format="verbose_json",
            )
            
            latency = self._measure_latency(start_time)
            
            # 세그먼트 정보 추출
            segments = []
            if hasattr(response, 'segments') and response.segments:
                segments = [
                    {
                        "start": seg.start,
                        "end": seg.end,
                        "text": seg.text,
                    }
                    for seg in response.segments
                ]
            
            logger.info(
                f"STT completed: provider=openai, "
                f"language={language}, "
                f"latency={latency:.0f}ms"
            )
            
            return STTResult(
                success=True,
                provider="openai",
                model=self.model,
                latency_ms=latency,
                text=response.text,
                language=response.language or language,
                confidence=1.0,  # Whisper는 confidence 제공 안함
                segments=segments,
            )
            
        except Exception as e:
            latency = self._measure_latency(start_time)
            logger.error(f"STT failed: {e}")
            
            return STTResult(
                success=False,
                provider="openai",
                model=self.model,
                latency_ms=latency,
                error=str(e),
            )


class GoogleSTTService(STTService):
    """Google Cloud Speech-to-Text 서비스"""
    
    provider = AIProvider.GOOGLE
    
    def __init__(self):
        self._client = None
    
    async def health_check(self) -> bool:
        """서비스 상태 확인"""
        try:
            return bool(settings.GOOGLE_APPLICATION_CREDENTIALS)
        except Exception:
            return False
    
    async def transcribe(
        self,
        audio_data: Union[bytes, BinaryIO],
        language: str = "ko",
        audio_format: str = "wav",
    ) -> STTResult:
        """Google Cloud로 음성 변환"""
        start_time = datetime.utcnow()
        
        try:
            from google.cloud import speech_v1
            
            if self._client is None:
                self._client = speech_v1.SpeechAsyncClient()
            
            # bytes로 변환
            if isinstance(audio_data, io.IOBase):
                audio_bytes = audio_data.read()
            else:
                audio_bytes = audio_data
            
            # 오디오 설정
            audio = speech_v1.RecognitionAudio(content=audio_bytes)
            
            # 인코딩 매핑
            encoding_map = {
                "wav": speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                "mp3": speech_v1.RecognitionConfig.AudioEncoding.MP3,
                "webm": speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                "ogg": speech_v1.RecognitionConfig.AudioEncoding.OGG_OPUS,
            }
            
            config = speech_v1.RecognitionConfig(
                encoding=encoding_map.get(
                    audio_format,
                    speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
                ),
                language_code=f"{language}-KR" if language == "ko" else language,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
            )
            
            # API 호출
            response = await self._client.recognize(config=config, audio=audio)
            
            latency = self._measure_latency(start_time)
            
            # 결과 처리
            text = ""
            confidence = 0.0
            segments = []
            
            for result in response.results:
                if result.alternatives:
                    best = result.alternatives[0]
                    text += best.transcript
                    confidence = max(confidence, best.confidence)
                    
                    for word in best.words:
                        segments.append({
                            "start": word.start_time.total_seconds(),
                            "end": word.end_time.total_seconds(),
                            "text": word.word,
                        })
            
            logger.info(
                f"STT completed: provider=google, "
                f"language={language}, "
                f"latency={latency:.0f}ms"
            )
            
            return STTResult(
                success=True,
                provider="google",
                model="speech-v1",
                latency_ms=latency,
                text=text,
                language=language,
                confidence=confidence,
                segments=segments,
            )
            
        except Exception as e:
            latency = self._measure_latency(start_time)
            logger.error(f"Google STT failed: {e}")
            
            return STTResult(
                success=False,
                provider="google",
                model="speech-v1",
                latency_ms=latency,
                error=str(e),
            )


def get_stt_service(provider: Optional[str] = None) -> STTService:
    """STT 서비스 인스턴스 반환
    
    Args:
        provider: 프로바이더 (없으면 설정값 사용)
        
    Returns:
        STTService: STT 서비스 인스턴스
    """
    provider = provider or settings.AI_STT_PROVIDER
    
    if provider == "google":
        return GoogleSTTService()
    else:
        return OpenAISTTService()
