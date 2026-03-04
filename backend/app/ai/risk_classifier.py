"""
Risk Classifier (위험도 분류) 서비스

대화 내용과 생체 데이터를 분석하여 위험도를 분류합니다.

위험도 수준:
- NORMAL: 정상 (일상 대화)
- LOW: 낮음 (일반적인 건강 문의)
- MEDIUM: 중간 (주의 필요)
- HIGH: 높음 (콜 트리 시작)
- CRITICAL: 위험 (즉시 에스컬레이션)
- EMERGENCY: 응급 (즉시 119)

분류 기준:
- 응급 키워드 감지
- 생체 데이터 이상
- 대화 맥락 분석
- 감정 분석
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.ai.llm import ConversationIntent, get_llm_service
from app.core.logging import logger


class RiskLevel(str, Enum):
    """위험도 수준"""
    NORMAL = "normal"       # 정상
    LOW = "low"             # 낮음
    MEDIUM = "medium"       # 중간
    HIGH = "high"           # 높음
    CRITICAL = "critical"   # 위험
    EMERGENCY = "emergency" # 응급 (즉시 119)


@dataclass
class RiskAssessment:
    """위험도 평가 결과"""
    level: RiskLevel
    confidence: float
    reasons: List[str]
    keywords_detected: List[str]
    recommended_action: str
    should_escalate: bool
    escalation_target: Optional[str] = None  # guardian, operator, 119
    vital_concerns: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class RiskClassifier:
    """위험도 분류기"""
    
    # 응급 키워드 (즉시 119)
    EMERGENCY_KEYWORDS = {
        # 직접적인 도움 요청
        "살려줘": RiskLevel.EMERGENCY,
        "살려주세요": RiskLevel.EMERGENCY,
        "죽겠어": RiskLevel.EMERGENCY,
        "죽을 것 같아": RiskLevel.EMERGENCY,
        
        # 심장/흉통
        "흉통": RiskLevel.EMERGENCY,
        "가슴이 아파": RiskLevel.EMERGENCY,
        "가슴 아파": RiskLevel.EMERGENCY,
        "심장이 아파": RiskLevel.EMERGENCY,
        "가슴이 조여": RiskLevel.EMERGENCY,
        "가슴이 눌려": RiskLevel.EMERGENCY,
        
        # 호흡 곤란
        "호흡곤란": RiskLevel.EMERGENCY,
        "숨이 안 쉬어져": RiskLevel.EMERGENCY,
        "숨을 못 쉬겠어": RiskLevel.EMERGENCY,
        "숨이 막혀": RiskLevel.EMERGENCY,
        "숨이 안 쉬어": RiskLevel.EMERGENCY,
        
        # 의식 저하
        "쓰러졌어": RiskLevel.EMERGENCY,
        "의식이 없어": RiskLevel.EMERGENCY,
        "정신이 없어": RiskLevel.EMERGENCY,
        
        # 응급 서비스 요청
        "119": RiskLevel.EMERGENCY,
        "구급차": RiskLevel.EMERGENCY,
        "응급실": RiskLevel.EMERGENCY,
    }
    
    # 위험 키워드 (콜 트리 시작)
    HIGH_RISK_KEYWORDS = {
        # 낙상
        "넘어졌어": RiskLevel.HIGH,
        "넘어졌다": RiskLevel.HIGH,
        "넘어져": RiskLevel.HIGH,
        "못 일어나": RiskLevel.HIGH,
        "일어날 수가 없어": RiskLevel.HIGH,
        
        # 통증
        "아파 죽겠어": RiskLevel.HIGH,
        "너무 아파": RiskLevel.HIGH,
        "많이 아파": RiskLevel.HIGH,
        
        # 호흡 관련
        "숨이 차": RiskLevel.CRITICAL,
        "숨쉬기 힘들어": RiskLevel.HIGH,
        
        # 어지러움
        "심하게 어지러워": RiskLevel.HIGH,
        "어지러워서 못 움직여": RiskLevel.HIGH,
        
        # 도움 요청
        "도와줘": RiskLevel.CRITICAL,
        "도와주세요": RiskLevel.CRITICAL,
        "누가 좀": RiskLevel.HIGH,
    }
    
    # 주의 키워드 (모니터링)
    MEDIUM_RISK_KEYWORDS = {
        "어지러워": RiskLevel.MEDIUM,
        "어질어질": RiskLevel.MEDIUM,
        "아파": RiskLevel.LOW,
        "불편해": RiskLevel.LOW,
        "기운이 없어": RiskLevel.MEDIUM,
        "힘이 없어": RiskLevel.MEDIUM,
        "몸이 안 좋아": RiskLevel.MEDIUM,
        "기분이 안 좋아": RiskLevel.LOW,
        "우울해": RiskLevel.MEDIUM,
        "불안해": RiskLevel.MEDIUM,
        "무서워": RiskLevel.MEDIUM,
    }
    
    # 생체 데이터 임계값
    VITAL_THRESHOLDS = {
        "spo2": {
            "emergency": 85,    # 즉시 119
            "critical": 90,     # 콜 트리
            "warning": 94,      # 주의
        },
        "heart_rate": {
            "emergency_low": 30,
            "emergency_high": 160,
            "critical_low": 40,
            "critical_high": 130,
            "warning_low": 50,
            "warning_high": 110,
        },
        "body_temperature": {
            "critical_low": 35.0,
            "critical_high": 39.0,
            "warning_low": 36.0,
            "warning_high": 37.8,
        },
    }
    
    def __init__(self, use_llm: bool = True):
        """
        Args:
            use_llm: LLM을 사용한 심층 분석 여부
        """
        self.use_llm = use_llm
        self._llm_service = None
    
    @property
    def llm_service(self):
        """LLM 서비스 (lazy loading)"""
        if self._llm_service is None and self.use_llm:
            self._llm_service = get_llm_service()
        return self._llm_service
    
    async def assess_risk(
        self,
        text: Optional[str] = None,
        vital_data: Optional[Dict[str, float]] = None,
        conversation_history: Optional[List[str]] = None,
    ) -> RiskAssessment:
        """종합 위험도 평가
        
        Args:
            text: 분석할 텍스트 (대화 내용)
            vital_data: 생체 데이터 {"spo2": 95, "heart_rate": 80, ...}
            conversation_history: 최근 대화 기록
            
        Returns:
            RiskAssessment: 위험도 평가 결과
        """
        reasons = []
        keywords_detected = []
        vital_concerns = []
        
        # 최종 위험도 초기화
        max_risk_level = RiskLevel.NORMAL
        
        # 1. 텍스트 기반 키워드 분석
        if text:
            keyword_result = self._analyze_keywords(text)
            if keyword_result["level"] != RiskLevel.NORMAL:
                max_risk_level = self._max_risk(max_risk_level, keyword_result["level"])
                keywords_detected.extend(keyword_result["keywords"])
                reasons.append(f"키워드 감지: {', '.join(keyword_result['keywords'])}")
        
        # 2. 생체 데이터 분석
        if vital_data:
            vital_result = self._analyze_vitals(vital_data)
            if vital_result["level"] != RiskLevel.NORMAL:
                max_risk_level = self._max_risk(max_risk_level, vital_result["level"])
                vital_concerns.extend(vital_result["concerns"])
                reasons.extend(vital_result["reasons"])
        
        # 3. LLM 심층 분석 (선택적)
        if self.use_llm and text and max_risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]:
            llm_result = await self._analyze_with_llm(text, conversation_history)
            if llm_result.get("is_emergency"):
                max_risk_level = self._max_risk(max_risk_level, RiskLevel.EMERGENCY)
                reasons.append(f"LLM 분석: {llm_result.get('reason', '응급 상황 감지')}")
        
        # 4. 액션 결정
        action, escalation_target, should_escalate = self._determine_action(max_risk_level)
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(
            len(keywords_detected),
            len(vital_concerns),
            max_risk_level,
        )
        
        logger.info(
            f"Risk assessment: level={max_risk_level.value}, "
            f"keywords={len(keywords_detected)}, "
            f"vital_concerns={len(vital_concerns)}, "
            f"confidence={confidence:.2f}"
        )
        
        return RiskAssessment(
            level=max_risk_level,
            confidence=confidence,
            reasons=reasons,
            keywords_detected=keywords_detected,
            recommended_action=action,
            should_escalate=should_escalate,
            escalation_target=escalation_target,
            vital_concerns=vital_concerns,
        )
    
    def _analyze_keywords(self, text: str) -> Dict[str, Any]:
        """키워드 기반 분석"""
        text_normalized = text.lower().strip()
        detected_keywords = []
        max_level = RiskLevel.NORMAL
        
        # 응급 키워드 체크
        for keyword, level in self.EMERGENCY_KEYWORDS.items():
            if keyword in text_normalized:
                detected_keywords.append(keyword)
                max_level = self._max_risk(max_level, level)
        
        # 위험 키워드 체크
        for keyword, level in self.HIGH_RISK_KEYWORDS.items():
            if keyword in text_normalized:
                detected_keywords.append(keyword)
                max_level = self._max_risk(max_level, level)
        
        # 주의 키워드 체크
        for keyword, level in self.MEDIUM_RISK_KEYWORDS.items():
            if keyword in text_normalized:
                detected_keywords.append(keyword)
                max_level = self._max_risk(max_level, level)
        
        return {
            "level": max_level,
            "keywords": detected_keywords,
        }
    
    def _analyze_vitals(self, vital_data: Dict[str, float]) -> Dict[str, Any]:
        """생체 데이터 분석"""
        concerns = []
        reasons = []
        max_level = RiskLevel.NORMAL
        
        # SpO2 체크
        if "spo2" in vital_data:
            spo2 = vital_data["spo2"]
            thresholds = self.VITAL_THRESHOLDS["spo2"]
            
            if spo2 < thresholds["emergency"]:
                max_level = self._max_risk(max_level, RiskLevel.EMERGENCY)
                concerns.append(f"SpO2 심각 저하: {spo2}%")
                reasons.append(f"SpO2 {spo2}% (응급 수준)")
            elif spo2 < thresholds["critical"]:
                max_level = self._max_risk(max_level, RiskLevel.CRITICAL)
                concerns.append(f"SpO2 저하: {spo2}%")
                reasons.append(f"SpO2 {spo2}% (위험 수준)")
            elif spo2 < thresholds["warning"]:
                max_level = self._max_risk(max_level, RiskLevel.MEDIUM)
                concerns.append(f"SpO2 주의: {spo2}%")
                reasons.append(f"SpO2 {spo2}% (주의 필요)")
        
        # 심박수 체크
        if "heart_rate" in vital_data:
            hr = vital_data["heart_rate"]
            thresholds = self.VITAL_THRESHOLDS["heart_rate"]
            
            if hr < thresholds["emergency_low"] or hr > thresholds["emergency_high"]:
                max_level = self._max_risk(max_level, RiskLevel.EMERGENCY)
                concerns.append(f"심박수 이상: {hr} bpm")
                reasons.append(f"심박수 {hr} bpm (응급 수준)")
            elif hr < thresholds["critical_low"] or hr > thresholds["critical_high"]:
                max_level = self._max_risk(max_level, RiskLevel.CRITICAL)
                concerns.append(f"심박수 비정상: {hr} bpm")
                reasons.append(f"심박수 {hr} bpm (위험 수준)")
            elif hr < thresholds["warning_low"] or hr > thresholds["warning_high"]:
                max_level = self._max_risk(max_level, RiskLevel.MEDIUM)
                concerns.append(f"심박수 주의: {hr} bpm")
                reasons.append(f"심박수 {hr} bpm (주의 필요)")
        
        # 체온 체크
        if "body_temperature" in vital_data:
            temp = vital_data["body_temperature"]
            thresholds = self.VITAL_THRESHOLDS["body_temperature"]
            
            if temp < thresholds["critical_low"] or temp > thresholds["critical_high"]:
                max_level = self._max_risk(max_level, RiskLevel.HIGH)
                concerns.append(f"체온 이상: {temp}°C")
                reasons.append(f"체온 {temp}°C (위험 수준)")
            elif temp < thresholds["warning_low"] or temp > thresholds["warning_high"]:
                max_level = self._max_risk(max_level, RiskLevel.MEDIUM)
                concerns.append(f"체온 주의: {temp}°C")
                reasons.append(f"체온 {temp}°C (주의 필요)")
        
        return {
            "level": max_level,
            "concerns": concerns,
            "reasons": reasons,
        }
    
    async def _analyze_with_llm(
        self,
        text: str,
        conversation_history: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """LLM을 사용한 심층 분석"""
        try:
            if not self.llm_service:
                return {"is_emergency": False}
            
            result = await self.llm_service.analyze_intent(text)
            
            return {
                "is_emergency": result.get("is_emergency", False),
                "intent": result.get("intent"),
                "confidence": result.get("confidence", 0.0),
                "reason": f"의도: {result.get('intent')}, 감정: {result.get('emotion')}",
            }
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {"is_emergency": False, "error": str(e)}
    
    def _determine_action(
        self,
        risk_level: RiskLevel,
    ) -> tuple[str, Optional[str], bool]:
        """위험도에 따른 액션 결정
        
        Returns:
            (action, escalation_target, should_escalate)
        """
        if risk_level == RiskLevel.EMERGENCY:
            return "immediate_119", "119", True
        elif risk_level == RiskLevel.CRITICAL:
            return "start_call_tree", "guardian", True
        elif risk_level == RiskLevel.HIGH:
            return "alert_guardian", "guardian", True
        elif risk_level == RiskLevel.MEDIUM:
            return "monitor", None, False
        elif risk_level == RiskLevel.LOW:
            return "log", None, False
        else:
            return "none", None, False
    
    def _max_risk(self, level1: RiskLevel, level2: RiskLevel) -> RiskLevel:
        """두 위험도 중 더 높은 것 반환"""
        order = {
            RiskLevel.NORMAL: 0,
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
            RiskLevel.EMERGENCY: 5,
        }
        
        if order[level1] >= order[level2]:
            return level1
        return level2
    
    def _calculate_confidence(
        self,
        keyword_count: int,
        vital_concern_count: int,
        risk_level: RiskLevel,
    ) -> float:
        """신뢰도 계산"""
        base_confidence = 0.5
        
        # 키워드 수에 따라 증가
        base_confidence += min(keyword_count * 0.1, 0.3)
        
        # 생체 데이터 우려에 따라 증가
        base_confidence += min(vital_concern_count * 0.15, 0.2)
        
        # 위험도가 높을수록 신뢰도 증가
        level_boost = {
            RiskLevel.NORMAL: 0,
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 0.05,
            RiskLevel.HIGH: 0.1,
            RiskLevel.CRITICAL: 0.15,
            RiskLevel.EMERGENCY: 0.2,
        }
        base_confidence += level_boost.get(risk_level, 0)
        
        return min(base_confidence, 1.0)
