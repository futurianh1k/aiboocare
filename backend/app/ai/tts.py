"""
TTS (Text-to-Speech) 서비스

텍스트를 자연스러운 음성으로 변환합니다.

지원 프로바이더:
- OpenAI TTS
- Google Cloud Text-to-Speech
- NAVER CLOVA Voice (한국어 특화)

참고:
- 어르신 청취를 위한 명확한 발음
- 적절한 속도와 톤
- 한국어 자연스러운 억양
"""

import base64
from abc import abstractmethod
from datetime import datetime
from typing import Optional

import httpx

from app.ai.base import AIProvider, BaseAIService, TTSResult
from app.core.config import settings
from app.core.logging import logger


class TTSService(BaseAIService):
    """TTS 서비스 추상 클래스"""
    
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """텍스트를 음성으로 변환
        
        Args:
            text: 변환할 텍스트
            voice: 음성 선택 (프로바이더별 상이)
            speed: 재생 속도 (0.5~2.0, 기본 1.0)
            
        Returns:
            TTSResult: 변환 결과 (오디오 바이트)
        """
        pass


class OpenAITTSService(TTSService):
    """OpenAI TTS 서비스"""
    
    provider = AIProvider.OPENAI
    
    # 사용 가능한 음성
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_TTS_MODEL
        self.default_voice = settings.OPENAI_TTS_VOICE
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
            return bool(self.api_key)
        except Exception:
            return False
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """OpenAI TTS로 음성 합성"""
        start_time = datetime.utcnow()
        
        try:
            # 텍스트 길이 제한
            if len(text) > settings.AI_MAX_TEXT_LENGTH:
                text = text[:settings.AI_MAX_TEXT_LENGTH]
            
            # 음성 선택
            voice = voice or self.default_voice
            if voice not in self.VOICES:
                voice = self.default_voice
            
            # 속도 범위 제한
            speed = max(0.25, min(4.0, speed))
            
            # API 호출
            response = await self.client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=text,
                speed=speed,
                response_format="mp3",
            )
            
            # 오디오 데이터 읽기
            audio_data = response.content
            
            latency = self._measure_latency(start_time)
            
            # 대략적인 재생 시간 추정 (한국어 기준 분당 ~200자)
            duration = len(text) / 200 * 60 / speed
            
            logger.info(
                f"TTS completed: provider=openai, "
                f"voice={voice}, "
                f"chars={len(text)}, "
                f"latency={latency:.0f}ms"
            )
            
            return TTSResult(
                success=True,
                provider="openai",
                model=self.model,
                latency_ms=latency,
                audio_data=audio_data,
                audio_format="mp3",
                duration_seconds=duration,
                metadata={"voice": voice, "speed": speed},
            )
            
        except Exception as e:
            latency = self._measure_latency(start_time)
            logger.error(f"TTS failed: {e}")
            
            return TTSResult(
                success=False,
                provider="openai",
                model=self.model,
                latency_ms=latency,
                error=str(e),
            )


class GoogleTTSService(TTSService):
    """Google Cloud Text-to-Speech 서비스"""
    
    provider = AIProvider.GOOGLE
    
    # 한국어 음성
    KOREAN_VOICES = {
        "female_a": "ko-KR-Wavenet-A",
        "female_b": "ko-KR-Wavenet-B",
        "male_c": "ko-KR-Wavenet-C",
        "male_d": "ko-KR-Wavenet-D",
    }
    
    def __init__(self):
        self._client = None
    
    async def health_check(self) -> bool:
        """서비스 상태 확인"""
        try:
            return bool(settings.GOOGLE_APPLICATION_CREDENTIALS)
        except Exception:
            return False
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """Google Cloud TTS로 음성 합성"""
        start_time = datetime.utcnow()
        
        try:
            from google.cloud import texttospeech_v1
            
            if self._client is None:
                self._client = texttospeech_v1.TextToSpeechAsyncClient()
            
            # 음성 선택
            voice_name = self.KOREAN_VOICES.get(voice, "ko-KR-Wavenet-A")
            
            # 요청 구성
            synthesis_input = texttospeech_v1.SynthesisInput(text=text)
            
            voice_params = texttospeech_v1.VoiceSelectionParams(
                language_code="ko-KR",
                name=voice_name,
            )
            
            audio_config = texttospeech_v1.AudioConfig(
                audio_encoding=texttospeech_v1.AudioEncoding.MP3,
                speaking_rate=speed,
                pitch=0.0,
            )
            
            # API 호출
            response = await self._client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )
            
            latency = self._measure_latency(start_time)
            
            # 대략적인 재생 시간 추정
            duration = len(text) / 200 * 60 / speed
            
            logger.info(
                f"TTS completed: provider=google, "
                f"voice={voice_name}, "
                f"chars={len(text)}, "
                f"latency={latency:.0f}ms"
            )
            
            return TTSResult(
                success=True,
                provider="google",
                model="wavenet",
                latency_ms=latency,
                audio_data=response.audio_content,
                audio_format="mp3",
                duration_seconds=duration,
                metadata={"voice": voice_name, "speed": speed},
            )
            
        except Exception as e:
            latency = self._measure_latency(start_time)
            logger.error(f"Google TTS failed: {e}")
            
            return TTSResult(
                success=False,
                provider="google",
                model="wavenet",
                latency_ms=latency,
                error=str(e),
            )


class ClovaTTSService(TTSService):
    """NAVER CLOVA Voice TTS 서비스
    
    한국어 음성 합성에 특화된 서비스
    """
    
    provider = AIProvider.CLOVA
    
    # 사용 가능한 음성
    VOICES = {
        "nara": "여성 (나라)",
        "nara_call": "여성 콜센터 (나라)",
        "nminsang": "남성 (민상)",
        "nhajun": "남성 아이 (하준)",
        "ndain": "여성 아이 (다인)",
        "njiyun": "여성 (지윤)",
        "nsujin": "여성 (수진)",
        "njinho": "남성 (진호)",
        "nminjun": "남성 (민준)",
    }
    
    API_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"
    
    def __init__(self):
        self.client_id = settings.CLOVA_CLIENT_ID
        self.client_secret = settings.CLOVA_CLIENT_SECRET
    
    async def health_check(self) -> bool:
        """서비스 상태 확인"""
        try:
            return bool(self.client_id and self.client_secret)
        except Exception:
            return False
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: float = 1.0,
    ) -> TTSResult:
        """CLOVA Voice로 음성 합성"""
        start_time = datetime.utcnow()
        
        try:
            # 텍스트 길이 제한 (CLOVA는 1000자 제한)
            if len(text) > 1000:
                text = text[:1000]
            
            # 음성 선택 (기본: 나라)
            voice = voice or "nara"
            if voice not in self.VOICES:
                voice = "nara"
            
            # 속도 범위 제한 (CLOVA: -5 ~ 5)
            clova_speed = int((speed - 1.0) * 5)
            clova_speed = max(-5, min(5, clova_speed))
            
            # API 호출
            headers = {
                "X-NCP-APIGW-API-KEY-ID": self.client_id,
                "X-NCP-APIGW-API-KEY": self.client_secret,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            
            data = {
                "speaker": voice,
                "text": text,
                "volume": "0",
                "speed": str(clova_speed),
                "pitch": "0",
                "format": "mp3",
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.API_URL,
                    headers=headers,
                    data=data,
                    timeout=30.0,
                )
            
            latency = self._measure_latency(start_time)
            
            if response.status_code == 200:
                # 대략적인 재생 시간 추정
                duration = len(text) / 200 * 60 / speed
                
                logger.info(
                    f"TTS completed: provider=clova, "
                    f"voice={voice}, "
                    f"chars={len(text)}, "
                    f"latency={latency:.0f}ms"
                )
                
                return TTSResult(
                    success=True,
                    provider="clova",
                    model="premium",
                    latency_ms=latency,
                    audio_data=response.content,
                    audio_format="mp3",
                    duration_seconds=duration,
                    metadata={"voice": voice, "speed": speed},
                )
            else:
                raise Exception(f"CLOVA API error: {response.status_code}")
            
        except Exception as e:
            latency = self._measure_latency(start_time)
            logger.error(f"CLOVA TTS failed: {e}")
            
            return TTSResult(
                success=False,
                provider="clova",
                model="premium",
                latency_ms=latency,
                error=str(e),
            )


def get_tts_service(provider: Optional[str] = None) -> TTSService:
    """TTS 서비스 인스턴스 반환
    
    Args:
        provider: 프로바이더 (없으면 설정값 사용)
        
    Returns:
        TTSService: TTS 서비스 인스턴스
    """
    provider = provider or settings.AI_TTS_PROVIDER
    
    if provider == "google":
        return GoogleTTSService()
    elif provider == "clova":
        return ClovaTTSService()
    else:
        return OpenAITTSService()
