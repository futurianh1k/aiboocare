"""
AI 서비스 API 엔드포인트

- STT: 음성 → 텍스트 변환
- LLM: 대화 처리
- TTS: 텍스트 → 음성 변환
- Risk Assessment: 위험도 분류

보안 규칙:
- 민감 정보(PII)는 마스킹하여 처리
- 대화 로그는 최소 정보만 저장
"""

import base64
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm import ConversationIntent, get_llm_service
from app.ai.risk_classifier import RiskClassifier, RiskLevel
from app.ai.stt import get_stt_service
from app.ai.tts import get_tts_service
from app.api.deps import get_current_user_optional, get_db
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


# ============== 요청/응답 스키마 ==============

class STTRequest(BaseModel):
    """STT 요청 (Base64 오디오)"""
    audio_base64: str = Field(..., description="Base64 인코딩된 오디오 데이터")
    audio_format: str = Field("wav", description="오디오 포맷 (wav, mp3, webm)")
    language: str = Field("ko", description="언어 코드")


class STTResponse(BaseModel):
    """STT 응답"""
    success: bool
    text: str
    language: str
    confidence: float
    latency_ms: float
    provider: str


class ChatRequest(BaseModel):
    """LLM 대화 요청"""
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = Field(None, description="대화 세션 ID")
    history: Optional[List[Dict[str, str]]] = Field(None, description="이전 대화 기록")
    user_context: Optional[Dict[str, Any]] = Field(None, description="사용자 컨텍스트")


class ChatResponse(BaseModel):
    """LLM 대화 응답"""
    success: bool
    response: str
    intent: Optional[str]
    emotion: Optional[str]
    action: Optional[str]
    latency_ms: float
    provider: str


class TTSRequest(BaseModel):
    """TTS 요청"""
    text: str = Field(..., min_length=1, max_length=4000)
    voice: Optional[str] = Field(None, description="음성 선택")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="재생 속도")
    return_base64: bool = Field(False, description="Base64로 응답 여부")


class TTSResponse(BaseModel):
    """TTS 응답 (Base64)"""
    success: bool
    audio_base64: str
    audio_format: str
    duration_seconds: float
    latency_ms: float
    provider: str


class RiskAssessmentRequest(BaseModel):
    """위험도 평가 요청"""
    text: Optional[str] = Field(None, description="분석할 텍스트")
    vital_data: Optional[Dict[str, float]] = Field(
        None, 
        description="생체 데이터 {spo2, heart_rate, body_temperature}",
    )
    conversation_history: Optional[List[str]] = Field(None, description="최근 대화 기록")


class RiskAssessmentResponse(BaseModel):
    """위험도 평가 응답"""
    level: str
    confidence: float
    reasons: List[str]
    keywords_detected: List[str]
    recommended_action: str
    should_escalate: bool
    escalation_target: Optional[str]
    vital_concerns: List[str]


# ============== STT API ==============

@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    request: STTRequest,
    provider: Optional[str] = Query(None, description="프로바이더 (openai, google)"),
):
    """음성을 텍스트로 변환 (STT)
    
    Base64로 인코딩된 오디오 데이터를 받아 텍스트로 변환합니다.
    """
    try:
        # Base64 디코딩
        audio_data = base64.b64decode(request.audio_base64)
        
        # 오디오 크기 제한 (최대 25MB)
        if len(audio_data) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="오디오 파일이 너무 큽니다. (최대 25MB)",
            )
        
        # STT 서비스 호출
        stt_service = get_stt_service(provider)
        result = await stt_service.transcribe(
            audio_data=audio_data,
            language=request.language,
            audio_format=request.audio_format,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"STT 변환 실패: {result.error}",
            )
        
        return STTResponse(
            success=True,
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            latency_ms=result.latency_ms,
            provider=result.provider,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="음성 변환 중 오류가 발생했습니다.",
        )


@router.post("/stt/upload", response_model=STTResponse)
async def speech_to_text_upload(
    audio_file: UploadFile = File(...),
    language: str = Query("ko", description="언어 코드"),
    provider: Optional[str] = Query(None, description="프로바이더"),
):
    """음성 파일 업로드 및 변환 (STT)"""
    try:
        # 파일 크기 제한
        content = await audio_file.read()
        if len(content) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="오디오 파일이 너무 큽니다. (최대 25MB)",
            )
        
        # 파일 형식 추출
        filename = audio_file.filename or "audio.wav"
        audio_format = filename.split(".")[-1].lower()
        if audio_format not in ["wav", "mp3", "webm", "ogg", "m4a"]:
            audio_format = "wav"
        
        # STT 서비스 호출
        stt_service = get_stt_service(provider)
        result = await stt_service.transcribe(
            audio_data=content,
            language=language,
            audio_format=audio_format,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"STT 변환 실패: {result.error}",
            )
        
        return STTResponse(
            success=True,
            text=result.text,
            language=result.language,
            confidence=result.confidence,
            latency_ms=result.latency_ms,
            provider=result.provider,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STT upload API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="음성 변환 중 오류가 발생했습니다.",
        )


# ============== LLM Chat API ==============

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    provider: Optional[str] = Query(None, description="프로바이더 (openai, anthropic)"),
):
    """AI 대화 처리 (LLM)
    
    사용자 메시지에 대한 AI 응답을 생성합니다.
    의도 분석, 감정 분석, 응급 상황 감지를 함께 수행합니다.
    """
    try:
        # LLM 서비스 호출
        llm_service = get_llm_service(provider)
        result = await llm_service.chat(
            message=request.message,
            conversation_history=request.history,
            user_context=request.user_context,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"대화 처리 실패: {result.error}",
            )
        
        return ChatResponse(
            success=True,
            response=result.response,
            intent=result.intent,
            emotion=result.entities.get("emotion"),
            action=result.entities.get("action"),
            latency_ms=result.latency_ms,
            provider=result.provider,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="대화 처리 중 오류가 발생했습니다.",
        )


@router.post("/analyze-intent")
async def analyze_intent(
    message: str = Query(..., min_length=1, max_length=1000),
    provider: Optional[str] = Query(None),
):
    """텍스트 의도 분석"""
    try:
        llm_service = get_llm_service(provider)
        result = await llm_service.analyze_intent(message)
        
        return result
        
    except Exception as e:
        logger.error(f"Intent analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="의도 분석 중 오류가 발생했습니다.",
        )


# ============== TTS API ==============

@router.post("/tts")
async def text_to_speech(
    request: TTSRequest,
    provider: Optional[str] = Query(None, description="프로바이더 (openai, google, clova)"),
):
    """텍스트를 음성으로 변환 (TTS)
    
    return_base64=True이면 JSON으로 Base64 응답
    return_base64=False이면 오디오 바이너리 직접 응답
    """
    try:
        # TTS 서비스 호출
        tts_service = get_tts_service(provider)
        result = await tts_service.synthesize(
            text=request.text,
            voice=request.voice,
            speed=request.speed,
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"TTS 변환 실패: {result.error}",
            )
        
        # Base64 응답
        if request.return_base64:
            return TTSResponse(
                success=True,
                audio_base64=base64.b64encode(result.audio_data).decode(),
                audio_format=result.audio_format,
                duration_seconds=result.duration_seconds,
                latency_ms=result.latency_ms,
                provider=result.provider,
            )
        
        # 바이너리 응답
        return Response(
            content=result.audio_data,
            media_type=f"audio/{result.audio_format}",
            headers={
                "X-TTS-Provider": result.provider,
                "X-TTS-Latency-Ms": str(int(result.latency_ms)),
                "X-TTS-Duration-Seconds": str(result.duration_seconds),
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="음성 합성 중 오류가 발생했습니다.",
        )


# ============== Risk Assessment API ==============

@router.post("/risk-assessment", response_model=RiskAssessmentResponse)
async def assess_risk(
    request: RiskAssessmentRequest,
    use_llm: bool = Query(True, description="LLM 심층 분석 사용 여부"),
):
    """위험도 평가
    
    텍스트와 생체 데이터를 분석하여 위험도를 평가합니다.
    """
    try:
        classifier = RiskClassifier(use_llm=use_llm)
        result = await classifier.assess_risk(
            text=request.text,
            vital_data=request.vital_data,
            conversation_history=request.conversation_history,
        )
        
        return RiskAssessmentResponse(
            level=result.level.value,
            confidence=result.confidence,
            reasons=result.reasons,
            keywords_detected=result.keywords_detected,
            recommended_action=result.recommended_action,
            should_escalate=result.should_escalate,
            escalation_target=result.escalation_target,
            vital_concerns=result.vital_concerns,
        )
        
    except Exception as e:
        logger.error(f"Risk assessment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="위험도 평가 중 오류가 발생했습니다.",
        )


# ============== Health Check ==============

@router.get("/health")
async def ai_health_check():
    """AI 서비스 상태 확인"""
    status_result = {
        "stt": {"openai": False, "google": False},
        "llm": {"openai": False, "anthropic": False},
        "tts": {"openai": False, "google": False, "clova": False},
    }
    
    # STT 상태
    try:
        stt_openai = get_stt_service("openai")
        status_result["stt"]["openai"] = await stt_openai.health_check()
    except Exception:
        pass
    
    # LLM 상태
    try:
        llm_openai = get_llm_service("openai")
        status_result["llm"]["openai"] = await llm_openai.health_check()
    except Exception:
        pass
    
    try:
        llm_anthropic = get_llm_service("anthropic")
        status_result["llm"]["anthropic"] = await llm_anthropic.health_check()
    except Exception:
        pass
    
    # TTS 상태
    try:
        tts_openai = get_tts_service("openai")
        status_result["tts"]["openai"] = await tts_openai.health_check()
    except Exception:
        pass
    
    # 전체 상태 결정
    any_available = any(
        any(v.values()) for v in status_result.values()
    )
    
    return {
        "status": "healthy" if any_available else "degraded",
        "providers": status_result,
        "default_providers": {
            "stt": settings.AI_STT_PROVIDER,
            "llm": settings.AI_LLM_PROVIDER,
            "tts": settings.AI_TTS_PROVIDER,
        },
    }
