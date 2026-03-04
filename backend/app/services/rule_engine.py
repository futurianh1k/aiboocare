"""
Rule Evaluator 서비스

이벤트 발생 시 정책 룰을 평가하여 액션을 결정합니다.

Hard Rules (즉시 119):
- 응급 키워드 발화: "살려줘", "흉통", "호흡곤란", "숨이 차요"
- SpO2 < 90% 60초 이상 지속 + 호흡곤란
- 낙상 감지 + 60초 무동작 + 사용자 미응답
- SOS 버튼 + 확인 질문 미응답

Soft Rules (콜 트리 시작):
- 낙상 감지 단독
- 무활동 감지
- 비정상 생체 징후
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.event import (
    ActionType,
    CareCase,
    CareEvent,
    CaseAction,
    CaseStatus,
    EventSeverity,
    EventType,
    Measurement,
    MeasurementType,
)


class ActionDecision(str, Enum):
    """평가 결과 액션"""
    NONE = "none"                        # 추가 액션 없음
    START_CALL_TREE = "start_call_tree"  # 콜 트리 시작
    IMMEDIATE_119 = "immediate_119"      # 즉시 119 연계
    NOTIFY_GUARDIAN = "notify_guardian"  # 보호자 알림
    ALERT_OPERATOR = "alert_operator"    # 운영자 알림


@dataclass
class RuleEvaluationResult:
    """룰 평가 결과"""
    action: ActionDecision
    reason: str
    matched_rules: List[str]
    context: Dict[str, Any]


class RuleEvaluator:
    """룰 평가 엔진"""
    
    # 응급 키워드 목록
    EMERGENCY_KEYWORDS = [
        "살려줘", "살려주세요", "도와줘", "도와주세요",
        "흉통", "가슴이 아파", "가슴 아파",
        "호흡곤란", "숨이 안 쉬어져", "숨이 차", "숨이 막혀",
        "쓰러졌어", "넘어졌어", "못 일어나",
        "응급", "119", "구급차",
    ]
    
    # SpO2 임계값
    SPO2_CRITICAL = 90
    SPO2_WARNING = 94
    SPO2_DURATION_SECONDS = 60
    
    # 무활동 임계값 (분)
    INACTIVITY_CRITICAL_MINUTES = 30
    INACTIVITY_WARNING_MINUTES = 15
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def evaluate(
        self,
        event: CareEvent,
        case: Optional[CareCase] = None,
    ) -> RuleEvaluationResult:
        """이벤트에 대한 룰 평가
        
        Args:
            event: 평가할 이벤트
            case: 연결된 케이스 (있는 경우)
            
        Returns:
            RuleEvaluationResult: 평가 결과
        """
        matched_rules = []
        context = {
            "event_id": str(event.id),
            "event_type": event.event_type.value,
            "severity": event.severity.value,
            "user_id": str(event.user_id),
        }
        
        # 1. Hard Rules 체크 (즉시 119)
        hard_rule_result = await self._check_hard_rules(event, context)
        if hard_rule_result:
            matched_rules.append(hard_rule_result)
            return RuleEvaluationResult(
                action=ActionDecision.IMMEDIATE_119,
                reason=f"Hard Rule 충족: {hard_rule_result}",
                matched_rules=matched_rules,
                context=context,
            )
        
        # 2. EMERGENCY 심각도 체크
        if event.severity == EventSeverity.EMERGENCY:
            matched_rules.append("emergency_severity")
            return RuleEvaluationResult(
                action=ActionDecision.IMMEDIATE_119,
                reason="EMERGENCY 심각도 이벤트",
                matched_rules=matched_rules,
                context=context,
            )
        
        # 3. Soft Rules 체크 (콜 트리 시작)
        soft_rule_result = await self._check_soft_rules(event, context)
        if soft_rule_result:
            matched_rules.append(soft_rule_result)
            return RuleEvaluationResult(
                action=ActionDecision.START_CALL_TREE,
                reason=f"Soft Rule 충족: {soft_rule_result}",
                matched_rules=matched_rules,
                context=context,
            )
        
        # 4. CRITICAL 심각도는 콜 트리 시작
        if event.severity == EventSeverity.CRITICAL:
            matched_rules.append("critical_severity")
            return RuleEvaluationResult(
                action=ActionDecision.START_CALL_TREE,
                reason="CRITICAL 심각도 이벤트",
                matched_rules=matched_rules,
                context=context,
            )
        
        # 5. WARNING 심각도는 운영자 알림
        if event.severity == EventSeverity.WARNING:
            matched_rules.append("warning_severity")
            return RuleEvaluationResult(
                action=ActionDecision.ALERT_OPERATOR,
                reason="WARNING 심각도 이벤트",
                matched_rules=matched_rules,
                context=context,
            )
        
        # 액션 없음
        return RuleEvaluationResult(
            action=ActionDecision.NONE,
            reason="룰 미해당",
            matched_rules=matched_rules,
            context=context,
        )
    
    async def _check_hard_rules(
        self,
        event: CareEvent,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Hard Rules 체크 (즉시 119)"""
        
        # 1. 응급 키워드 발화
        if event.event_type == EventType.EMERGENCY_VOICE:
            return "emergency_voice_keyword"
        
        # 2. SOS 버튼 + 미응답 (이벤트 데이터에서 확인)
        if event.event_type == EventType.EMERGENCY_BUTTON:
            event_data = event.event_data or {}
            if event_data.get("user_no_response"):
                return "sos_button_no_response"
        
        # 3. SpO2 < 90% 지속
        if event.event_type == EventType.LOW_SPO2:
            # 최근 SpO2 측정값 확인
            is_sustained = await self._check_sustained_low_spo2(
                event.user_id,
                event.occurred_at,
            )
            if is_sustained:
                context["spo2_duration_exceeded"] = True
                return "sustained_low_spo2"
        
        # 4. 낙상 + 무응답
        if event.event_type == EventType.FALL:
            event_data = event.event_data or {}
            if event_data.get("no_movement_after_fall"):
                return "fall_no_movement"
            if event_data.get("user_no_response"):
                return "fall_no_response"
        
        return None
    
    async def _check_soft_rules(
        self,
        event: CareEvent,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Soft Rules 체크 (콜 트리 시작)"""
        
        # 1. 낙상 감지
        if event.event_type == EventType.FALL:
            return "fall_detected"
        
        # 2. 무활동 감지
        if event.event_type == EventType.INACTIVITY:
            event_data = event.event_data or {}
            duration_minutes = event_data.get("duration_minutes", 0)
            if duration_minutes >= self.INACTIVITY_CRITICAL_MINUTES:
                return "prolonged_inactivity_critical"
            elif duration_minutes >= self.INACTIVITY_WARNING_MINUTES:
                return "prolonged_inactivity_warning"
        
        # 3. 비정상 생체 징후
        if event.event_type == EventType.ABNORMAL_VITAL:
            return "abnormal_vital_signs"
        
        # 4. 저산소증 (non-sustained)
        if event.event_type == EventType.LOW_SPO2:
            return "low_spo2"
        
        return None
    
    async def _check_sustained_low_spo2(
        self,
        user_id: uuid.UUID,
        reference_time: datetime,
    ) -> bool:
        """SpO2 < 90%가 60초 이상 지속되었는지 확인"""
        window_start = reference_time - timedelta(seconds=self.SPO2_DURATION_SECONDS)
        
        result = await self.db.execute(
            select(Measurement).where(
                Measurement.user_id == user_id,
                Measurement.measurement_type == MeasurementType.SPO2,
                Measurement.recorded_at >= window_start,
                Measurement.recorded_at <= reference_time,
            ).order_by(Measurement.recorded_at.desc())
        )
        
        measurements = list(result.scalars().all())
        
        if not measurements:
            return False
        
        # 모든 측정값이 90% 미만인지 확인
        low_count = sum(
            1 for m in measurements
            if m.value is not None and m.value < self.SPO2_CRITICAL
        )
        
        # 3개 이상의 연속 저하 측정
        return low_count >= 3
    
    async def execute_action(
        self,
        result: RuleEvaluationResult,
        case: CareCase,
    ) -> None:
        """평가 결과에 따른 액션 실행
        
        Args:
            result: 룰 평가 결과
            case: 대상 케이스
        """
        if result.action == ActionDecision.NONE:
            return
        
        if result.action == ActionDecision.IMMEDIATE_119:
            await self._execute_119_escalation(case, result)
        
        elif result.action == ActionDecision.START_CALL_TREE:
            await self._execute_start_call_tree(case, result)
        
        elif result.action == ActionDecision.ALERT_OPERATOR:
            await self._execute_alert_operator(case, result)
        
        elif result.action == ActionDecision.NOTIFY_GUARDIAN:
            await self._execute_notify_guardian(case, result)
    
    async def _execute_119_escalation(
        self,
        case: CareCase,
        result: RuleEvaluationResult,
    ) -> None:
        """119 즉시 에스컬레이션 실행"""
        logger.warning(
            f"119 ESCALATION: "
            f"case={case.case_number}, "
            f"reason={result.reason}"
        )
        
        case.status = CaseStatus.ESCALATED_119
        case.current_escalation_stage = 5
        
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action_type=ActionType.ESCALATED_119,
            to_stage=5,
            to_status=CaseStatus.ESCALATED_119.value,
            action_data={
                "reason": result.reason,
                "matched_rules": result.matched_rules,
                "context": result.context,
            },
            note=f"자동 119 에스컬레이션: {result.reason}",
        )
        
        self.db.add(action)
        await self.db.commit()
        
        # TODO: 119 연계 API 호출
        # TODO: 모든 보호자에게 긴급 알림 발송
    
    async def _execute_start_call_tree(
        self,
        case: CareCase,
        result: RuleEvaluationResult,
    ) -> None:
        """콜 트리 시작"""
        logger.info(
            f"Starting call tree: "
            f"case={case.case_number}, "
            f"reason={result.reason}"
        )
        
        case.status = CaseStatus.ESCALATING
        case.current_escalation_stage = 1
        
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action_type=ActionType.ESCALATED,
            from_stage=0,
            to_stage=1,
            to_status=CaseStatus.ESCALATING.value,
            action_data={
                "reason": result.reason,
                "matched_rules": result.matched_rules,
            },
            note=f"콜 트리 시작: {result.reason}",
        )
        
        self.db.add(action)
        await self.db.commit()
        
        # TODO: Stage 1 알림 발송 (보호자 1차)
    
    async def _execute_alert_operator(
        self,
        case: CareCase,
        result: RuleEvaluationResult,
    ) -> None:
        """운영자 알림"""
        logger.info(
            f"Alerting operator: "
            f"case={case.case_number}, "
            f"reason={result.reason}"
        )
        
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action_type=ActionType.NOTIFICATION_SENT,
            action_data={
                "target": "operator",
                "reason": result.reason,
            },
            note=f"운영자 알림: {result.reason}",
        )
        
        self.db.add(action)
        await self.db.commit()
        
        # TODO: 운영자 콘솔에 알림 표시
    
    async def _execute_notify_guardian(
        self,
        case: CareCase,
        result: RuleEvaluationResult,
    ) -> None:
        """보호자 알림"""
        logger.info(
            f"Notifying guardian: "
            f"case={case.case_number}, "
            f"reason={result.reason}"
        )
        
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action_type=ActionType.NOTIFICATION_SENT,
            action_data={
                "target": "guardian",
                "reason": result.reason,
            },
            note=f"보호자 알림: {result.reason}",
        )
        
        self.db.add(action)
        await self.db.commit()
        
        # TODO: 보호자 앱 푸시 알림


class EmergencyKeywordDetector:
    """응급 키워드 탐지기"""
    
    # 응급 키워드와 심각도 매핑
    KEYWORDS = {
        # 즉시 119 (EMERGENCY)
        "살려줘": EventSeverity.EMERGENCY,
        "살려주세요": EventSeverity.EMERGENCY,
        "흉통": EventSeverity.EMERGENCY,
        "가슴이 아파": EventSeverity.EMERGENCY,
        "호흡곤란": EventSeverity.EMERGENCY,
        "숨이 안 쉬어져": EventSeverity.EMERGENCY,
        "숨이 막혀": EventSeverity.EMERGENCY,
        "쓰러졌어": EventSeverity.EMERGENCY,
        "119 불러줘": EventSeverity.EMERGENCY,
        "구급차": EventSeverity.EMERGENCY,
        
        # 콜 트리 시작 (CRITICAL)
        "넘어졌어": EventSeverity.CRITICAL,
        "못 일어나": EventSeverity.CRITICAL,
        "어지러워": EventSeverity.CRITICAL,
        "숨이 차": EventSeverity.CRITICAL,
        "도와줘": EventSeverity.CRITICAL,
        "도와주세요": EventSeverity.CRITICAL,
        
        # 확인 필요 (WARNING)
        "몸이 안 좋아": EventSeverity.WARNING,
        "아파": EventSeverity.WARNING,
        "힘들어": EventSeverity.WARNING,
    }
    
    @classmethod
    def detect(cls, text: str) -> Optional[tuple[str, EventSeverity]]:
        """텍스트에서 응급 키워드 탐지
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            (발견된 키워드, 심각도) 또는 None
        """
        text_lower = text.lower()
        
        # 가장 높은 심각도의 키워드 찾기
        highest_severity = None
        matched_keyword = None
        
        for keyword, severity in cls.KEYWORDS.items():
            if keyword in text_lower:
                if highest_severity is None or cls._severity_order(severity) > cls._severity_order(highest_severity):
                    highest_severity = severity
                    matched_keyword = keyword
        
        if matched_keyword:
            return (matched_keyword, highest_severity)
        
        return None
    
    @staticmethod
    def _severity_order(severity: EventSeverity) -> int:
        """심각도 순서"""
        return {
            EventSeverity.INFO: 0,
            EventSeverity.WARNING: 1,
            EventSeverity.CRITICAL: 2,
            EventSeverity.EMERGENCY: 3,
        }.get(severity, 0)
