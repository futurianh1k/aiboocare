"""
LLM (Large Language Model) 서비스

사용자와의 대화를 처리하고 의도를 분석합니다.

지원 프로바이더:
- OpenAI GPT-4
- Anthropic Claude

기능:
- 대화 응답 생성
- 의도 분석 (일상 대화, 건강 문의, 응급 상황 등)
- 감정 분석
- 응급 키워드 감지

참고:
- PII (개인정보)는 마스킹하여 전송
- 대화 로그는 최소 정보만 저장
"""

import json
from abc import abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.ai.base import AIProvider, BaseAIService, LLMResult
from app.core.config import settings
from app.core.logging import logger


class ConversationIntent(str, Enum):
    """대화 의도 분류"""
    GREETING = "greeting"              # 인사
    DAILY_CHAT = "daily_chat"          # 일상 대화
    HEALTH_INQUIRY = "health_inquiry"  # 건강 문의
    MEDICATION = "medication"          # 약 복용 관련
    EMERGENCY = "emergency"            # 응급 상황
    ASSISTANCE = "assistance"          # 도움 요청
    EMOTION_SUPPORT = "emotion_support"  # 정서 지원
    REMINDER = "reminder"              # 리마인더/알림
    UNKNOWN = "unknown"


SYSTEM_PROMPT = """당신은 독거노인을 돌보는 AI 케어 동반자입니다.
이름은 "아이부"입니다.

역할:
1. 따뜻하고 친근한 대화 상대가 되어주세요
2. 건강 상태를 자연스럽게 확인하세요
3. 약 복용, 식사, 수면 등 일상을 체크하세요
4. 응급 상황 징후를 감지하면 즉시 알려주세요

응급 키워드 감지 시:
- "살려줘", "흉통", "호흡곤란", "숨이 막혀" 등 → [EMERGENCY] 태그 사용
- 낙상, 의식 저하 등의 상황 → [ALERT] 태그 사용

대화 원칙:
- 존댓말 사용 (어르신 대상)
- 간결하고 명확한 문장
- 공감과 경청
- 긍정적이고 따뜻한 톤

응답 형식 (JSON):
{
    "response": "사용자에게 전달할 응답",
    "intent": "대화 의도 분류",
    "emotion": "감지된 감정 (happy, sad, anxious, pain, neutral)",
    "health_concern": "건강 관련 우려사항 (있는 경우)",
    "action": "필요한 액션 (null, remind_medication, check_vital, alert_guardian, emergency_119)"
}
"""


class LLMService(BaseAIService):
    """LLM 서비스 추상 클래스"""
    
    @abstractmethod
    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> LLMResult:
        """대화 응답 생성
        
        Args:
            message: 사용자 메시지
            conversation_history: 이전 대화 기록
            user_context: 사용자 컨텍스트 (이름, 건강 상태 등)
            
        Returns:
            LLMResult: 응답 결과
        """
        pass
    
    @abstractmethod
    async def analyze_intent(
        self,
        message: str,
    ) -> Dict[str, Any]:
        """의도 분석
        
        Args:
            message: 분석할 메시지
            
        Returns:
            의도 분석 결과
        """
        pass


class OpenAILLMService(LLMService):
    """OpenAI GPT LLM 서비스"""
    
    provider = AIProvider.OPENAI
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
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
    
    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> LLMResult:
        """OpenAI GPT로 대화 응답 생성"""
        start_time = datetime.utcnow()
        
        try:
            # 메시지 구성
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            
            # 사용자 컨텍스트 추가
            if user_context:
                context_msg = self._build_context_message(user_context)
                messages.append({"role": "system", "content": context_msg})
            
            # 대화 기록 추가
            if conversation_history:
                messages.extend(conversation_history[-10:])  # 최근 10개만
            
            # 현재 메시지 추가
            messages.append({"role": "user", "content": message})
            
            # API 호출
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=settings.AI_TEMPERATURE,
                max_tokens=settings.AI_MAX_TOKENS,
                response_format={"type": "json_object"},
            )
            
            latency = self._measure_latency(start_time)
            
            # 응답 파싱
            content = response.choices[0].message.content
            parsed = self._parse_response(content)
            
            logger.info(
                f"LLM chat completed: provider=openai, "
                f"intent={parsed.get('intent', 'unknown')}, "
                f"latency={latency:.0f}ms"
            )
            
            return LLMResult(
                success=True,
                provider="openai",
                model=self.model,
                latency_ms=latency,
                response=parsed.get("response", content),
                intent=parsed.get("intent"),
                entities={
                    "emotion": parsed.get("emotion"),
                    "health_concern": parsed.get("health_concern"),
                    "action": parsed.get("action"),
                },
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            )
            
        except Exception as e:
            latency = self._measure_latency(start_time)
            logger.error(f"LLM chat failed: {e}")
            
            return LLMResult(
                success=False,
                provider="openai",
                model=self.model,
                latency_ms=latency,
                error=str(e),
            )
    
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """의도 분석"""
        start_time = datetime.utcnow()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """주어진 한국어 메시지의 의도를 분석하세요.
응답 형식 (JSON):
{
    "intent": "greeting|daily_chat|health_inquiry|medication|emergency|assistance|emotion_support|reminder|unknown",
    "confidence": 0.0-1.0,
    "keywords": ["감지된", "키워드"],
    "is_emergency": true/false,
    "emotion": "happy|sad|anxious|pain|neutral"
}"""
                    },
                    {"role": "user", "content": message}
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "error": str(e),
            }
    
    def _build_context_message(self, context: Dict[str, Any]) -> str:
        """사용자 컨텍스트 메시지 생성"""
        parts = ["사용자 정보:"]
        
        if context.get("name"):
            parts.append(f"- 이름: {context['name']}님")
        if context.get("age"):
            parts.append(f"- 연령: {context['age']}세")
        if context.get("health_conditions"):
            parts.append(f"- 건강 상태: {', '.join(context['health_conditions'])}")
        if context.get("medications"):
            parts.append(f"- 복용 약물: {', '.join(context['medications'])}")
        if context.get("last_vital"):
            parts.append(f"- 최근 생체 정보: {context['last_vital']}")
        
        return "\n".join(parts)
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """응답 파싱"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"response": content}


class AnthropicLLMService(LLMService):
    """Anthropic Claude LLM 서비스"""
    
    provider = AIProvider.ANTHROPIC
    
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.model = settings.ANTHROPIC_MODEL
        self._client = None
    
    @property
    def client(self):
        """Anthropic 클라이언트 (lazy loading)"""
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client
    
    async def health_check(self) -> bool:
        """서비스 상태 확인"""
        try:
            return bool(self.api_key)
        except Exception:
            return False
    
    async def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> LLMResult:
        """Claude로 대화 응답 생성"""
        start_time = datetime.utcnow()
        
        try:
            # 시스템 프롬프트 구성
            system = SYSTEM_PROMPT
            if user_context:
                system += "\n\n" + self._build_context_message(user_context)
            
            # 메시지 구성
            messages = []
            if conversation_history:
                messages.extend(conversation_history[-10:])
            messages.append({"role": "user", "content": message})
            
            # API 호출
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.AI_MAX_TOKENS,
                system=system,
                messages=messages,
            )
            
            latency = self._measure_latency(start_time)
            
            # 응답 파싱
            content = response.content[0].text
            parsed = self._parse_response(content)
            
            logger.info(
                f"LLM chat completed: provider=anthropic, "
                f"intent={parsed.get('intent', 'unknown')}, "
                f"latency={latency:.0f}ms"
            )
            
            return LLMResult(
                success=True,
                provider="anthropic",
                model=self.model,
                latency_ms=latency,
                response=parsed.get("response", content),
                intent=parsed.get("intent"),
                entities={
                    "emotion": parsed.get("emotion"),
                    "health_concern": parsed.get("health_concern"),
                    "action": parsed.get("action"),
                },
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            )
            
        except Exception as e:
            latency = self._measure_latency(start_time)
            logger.error(f"Claude chat failed: {e}")
            
            return LLMResult(
                success=False,
                provider="anthropic",
                model=self.model,
                latency_ms=latency,
                error=str(e),
            )
    
    async def analyze_intent(self, message: str) -> Dict[str, Any]:
        """의도 분석"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=200,
                system="""주어진 한국어 메시지의 의도를 분석하세요.
응답은 반드시 JSON 형식으로:
{
    "intent": "greeting|daily_chat|health_inquiry|medication|emergency|assistance|emotion_support|reminder|unknown",
    "confidence": 0.0-1.0,
    "keywords": ["감지된", "키워드"],
    "is_emergency": true/false,
    "emotion": "happy|sad|anxious|pain|neutral"
}""",
                messages=[{"role": "user", "content": message}],
            )
            
            content = response.content[0].text
            # JSON 부분만 추출
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
                return json.loads(json_str)
            return {"intent": "unknown", "confidence": 0.0}
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "error": str(e),
            }
    
    def _build_context_message(self, context: Dict[str, Any]) -> str:
        """사용자 컨텍스트 메시지 생성"""
        parts = ["사용자 정보:"]
        
        if context.get("name"):
            parts.append(f"- 이름: {context['name']}님")
        if context.get("age"):
            parts.append(f"- 연령: {context['age']}세")
        if context.get("health_conditions"):
            parts.append(f"- 건강 상태: {', '.join(context['health_conditions'])}")
        if context.get("medications"):
            parts.append(f"- 복용 약물: {', '.join(context['medications'])}")
        
        return "\n".join(parts)
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """응답 파싱"""
        try:
            # JSON 부분만 추출
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
                return json.loads(json_str)
            return {"response": content}
        except json.JSONDecodeError:
            return {"response": content}


def get_llm_service(provider: Optional[str] = None) -> LLMService:
    """LLM 서비스 인스턴스 반환
    
    Args:
        provider: 프로바이더 (없으면 설정값 사용)
        
    Returns:
        LLMService: LLM 서비스 인스턴스
    """
    provider = provider or settings.AI_LLM_PROVIDER
    
    if provider == "anthropic":
        return AnthropicLLMService()
    else:
        return OpenAILLMService()
