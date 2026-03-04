"""
푸시 알림 서비스 (FCM)

Firebase Cloud Messaging을 사용하여 보호자 앱에 푸시 알림을 전송합니다.

참고:
- FCM 서버 키는 환경변수로 관리
- 토큰은 보호자 DB에 저장
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


@dataclass
class PushResult:
    """푸시 알림 결과"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    token: Optional[str] = None


class FCMService:
    """Firebase Cloud Messaging 서비스"""
    
    FCM_API_URL = "https://fcm.googleapis.com/fcm/send"
    
    def __init__(self):
        self.server_key = settings.FCM_SERVER_KEY
        self.enabled = bool(self.server_key)
    
    async def send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "high",
    ) -> PushResult:
        """단일 토큰에 푸시 전송
        
        Args:
            token: FCM 디바이스 토큰
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (앱에서 처리)
            priority: 우선순위 (high, normal)
            
        Returns:
            PushResult: 전송 결과
        """
        if not self.enabled:
            logger.warning("FCM is not configured")
            return PushResult(success=False, error="FCM not configured")
        
        payload = {
            "to": token,
            "priority": priority,
            "notification": {
                "title": title,
                "body": body,
                "sound": "default",
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
            },
        }
        
        if data:
            payload["data"] = {k: str(v) for k, v in data.items()}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.FCM_API_URL,
                    headers={
                        "Authorization": f"key={self.server_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=10.0,
                )
            
            result = response.json()
            
            if result.get("success") == 1:
                logger.info(f"FCM push sent: token={token[:20]}...")
                return PushResult(
                    success=True,
                    message_id=result.get("results", [{}])[0].get("message_id"),
                    token=token,
                )
            else:
                error = result.get("results", [{}])[0].get("error")
                logger.warning(f"FCM push failed: {error}")
                return PushResult(
                    success=False,
                    error=error,
                    token=token,
                )
        
        except Exception as e:
            logger.error(f"FCM request failed: {e}")
            return PushResult(success=False, error=str(e), token=token)
    
    async def send_to_tokens(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> List[PushResult]:
        """여러 토큰에 푸시 전송
        
        Args:
            tokens: FCM 토큰 리스트
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터
            
        Returns:
            List[PushResult]: 전송 결과 리스트
        """
        results = []
        for token in tokens:
            result = await self.send_to_token(token, title, body, data)
            results.append(result)
        return results
    
    async def send_case_alert(
        self,
        token: str,
        case_number: str,
        case_id: str,
        event_type: str,
        severity: str,
        care_user_name: str,
    ) -> PushResult:
        """케이스 알림 전송
        
        Args:
            token: FCM 토큰
            case_number: 케이스 번호
            case_id: 케이스 ID
            event_type: 이벤트 유형
            severity: 심각도
            care_user_name: 돌봄 대상자 이름
            
        Returns:
            PushResult: 전송 결과
        """
        # 심각도에 따른 제목
        severity_titles = {
            "emergency": "🚨 응급 상황",
            "critical": "⚠️ 위험 알림",
            "warning": "⚡ 주의 알림",
            "info": "ℹ️ 알림",
        }
        title = severity_titles.get(severity, "📢 케이스 알림")
        
        # 이벤트 유형에 따른 본문
        event_messages = {
            "fall": f"{care_user_name}님의 낙상이 감지되었습니다.",
            "inactivity": f"{care_user_name}님의 무활동이 감지되었습니다.",
            "emergency_button": f"{care_user_name}님이 응급 버튼을 눌렀습니다.",
            "emergency_voice": f"{care_user_name}님이 도움을 요청했습니다.",
            "abnormal_vital": f"{care_user_name}님의 생체 징후 이상이 감지되었습니다.",
            "low_spo2": f"{care_user_name}님의 산소포화도가 낮습니다.",
        }
        body = event_messages.get(event_type, f"{care_user_name}님의 케이스가 발생했습니다.")
        
        data = {
            "type": "case_alert",
            "case_id": case_id,
            "case_number": case_number,
            "event_type": event_type,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return await self.send_to_token(token, title, body, data, priority="high")
    
    async def send_escalation_alert(
        self,
        token: str,
        case_number: str,
        case_id: str,
        stage: int,
        care_user_name: str,
        timeout_seconds: int,
    ) -> PushResult:
        """에스컬레이션 알림 전송
        
        콜 트리에서 다음 단계로 에스컬레이션 시 전송합니다.
        """
        title = f"📞 응답 요청 (단계 {stage})"
        body = f"{care_user_name}님의 케이스입니다. {timeout_seconds}초 내 확인해주세요."
        
        data = {
            "type": "escalation_alert",
            "case_id": case_id,
            "case_number": case_number,
            "stage": str(stage),
            "timeout_seconds": str(timeout_seconds),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        return await self.send_to_token(token, title, body, data, priority="high")


# 전역 인스턴스
_fcm_service: Optional[FCMService] = None


def get_fcm_service() -> FCMService:
    """FCM 서비스 인스턴스 반환"""
    global _fcm_service
    if _fcm_service is None:
        _fcm_service = FCMService()
    return _fcm_service
