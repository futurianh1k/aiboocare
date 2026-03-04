"""
알림 서비스

다양한 채널을 통한 알림 발송:
- Push: FCM/APNs
- SMS: 문자 메시지
- Call: 전화 (TTS)
- Console: 운영자 콘솔 알림

참고: 실제 외부 서비스 연동은 별도 구현 필요
"""

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import audit_logger, logger
from app.models.event import ActionType, CareCase, CaseAction
from app.models.notification import (
    Alert,
    AlertStatus,
    NotificationChannel,
    NotificationDelivery,
)
from app.models.user import Guardian


class NotificationService:
    """알림 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_escalation_notification(
        self,
        case: CareCase,
        stage: int,
        target_type: str,
        channels: List[str],
    ) -> List[NotificationDelivery]:
        """에스컬레이션 알림 발송
        
        Args:
            case: 케이스
            stage: 에스컬레이션 단계
            target_type: 대상 유형 (guardian, caregiver, operator, emergency)
            channels: 사용할 채널 목록
            
        Returns:
            생성된 알림 배달 기록 목록
        """
        deliveries = []
        
        # 대상자별 알림 발송
        if target_type == "guardian":
            deliveries = await self._notify_guardians(case, stage, channels)
        elif target_type == "caregiver":
            deliveries = await self._notify_caregivers(case, stage, channels)
        elif target_type == "operator":
            deliveries = await self._notify_operators(case, stage, channels)
        elif target_type == "emergency":
            deliveries = await self._notify_emergency(case, stage, channels)
        
        return deliveries
    
    async def _create_alert(
        self,
        case: CareCase,
        stage: int,
        guardian_id: Optional[uuid.UUID] = None,
        operator_id: Optional[uuid.UUID] = None,
        timeout_seconds: int = 60,
    ) -> Alert:
        """Alert 생성"""
        alert = Alert(
            id=uuid.uuid4(),
            case_id=case.id,
            escalation_stage=stage,
            status=AlertStatus.PENDING,
            target_guardian_id=guardian_id,
            target_operator_id=operator_id,
            timeout_seconds=timeout_seconds,
            scheduled_at=datetime.now(timezone.utc),
        )
        
        self.db.add(alert)
        await self.db.commit()
        await self.db.refresh(alert)
        
        return alert
    
    def _build_alert_message(self, case: CareCase, stage: int) -> str:
        """알림 메시지 생성"""
        severity_text = {
            "info": "일반",
            "warning": "주의",
            "critical": "위험",
            "emergency": "응급",
        }.get(case.max_severity.value, "알림")
        
        return (
            f"[{severity_text}] 돌봄 대상자에게 상황이 발생했습니다.\n"
            f"케이스: {case.case_number}\n"
            f"단계: {stage}단계\n"
            "확인이 필요합니다."
        )
    
    async def _notify_guardians(
        self,
        case: CareCase,
        stage: int,
        channels: List[str],
    ) -> List[NotificationDelivery]:
        """보호자 알림 발송"""
        deliveries = []
        
        # 단계에 맞는 보호자 조회
        # Stage 1 → priority=1, Stage 2 → priority=2
        priority_threshold = stage
        
        result = await self.db.execute(
            select(Guardian).where(
                Guardian.care_user_id == case.user_id,
                Guardian.deleted_at.is_(None),
                Guardian.receive_notifications == True,
                Guardian.priority <= priority_threshold,
            ).order_by(Guardian.priority)
        )
        guardians = result.scalars().all()
        
        for guardian in guardians:
            # Alert 생성
            alert = await self._create_alert(
                case=case,
                stage=stage,
                guardian_id=guardian.id,
                timeout_seconds=60 if stage == 1 else 90,
            )
            
            for channel_str in channels:
                try:
                    channel = NotificationChannel(channel_str) if channel_str in [c.value for c in NotificationChannel] else NotificationChannel.PUSH
                except ValueError:
                    channel = NotificationChannel.PUSH
                
                delivery = await self._create_delivery(
                    alert=alert,
                    channel=channel,
                )
                deliveries.append(delivery)
                
                # 실제 발송 처리
                await self._send_via_channel(
                    delivery=delivery,
                    channel=channel,
                    guardian=guardian,
                    message=self._build_alert_message(case, stage),
                )
        
        return deliveries
    
    async def _notify_caregivers(
        self,
        case: CareCase,
        stage: int,
        channels: List[str],
    ) -> List[NotificationDelivery]:
        """요양보호사 알림 발송"""
        deliveries = []
        
        # Alert 생성
        alert = await self._create_alert(
            case=case,
            stage=stage,
            timeout_seconds=120,
        )
        
        for channel_str in channels:
            try:
                channel = NotificationChannel(channel_str) if channel_str in [c.value for c in NotificationChannel] else NotificationChannel.PUSH
            except ValueError:
                channel = NotificationChannel.PUSH
            
            delivery = await self._create_delivery(
                alert=alert,
                channel=channel,
            )
            deliveries.append(delivery)
        
        logger.info(f"Caregiver notification created: alert_id={alert.id}")
        
        return deliveries
    
    async def _notify_operators(
        self,
        case: CareCase,
        stage: int,
        channels: List[str],
    ) -> List[NotificationDelivery]:
        """운영자 알림 발송"""
        deliveries = []
        
        # Alert 생성
        alert = await self._create_alert(
            case=case,
            stage=stage,
            timeout_seconds=60,
        )
        
        for channel_str in channels:
            try:
                channel = NotificationChannel(channel_str) if channel_str in [c.value for c in NotificationChannel] else NotificationChannel.PUSH
            except ValueError:
                channel = NotificationChannel.PUSH
            
            delivery = await self._create_delivery(
                alert=alert,
                channel=channel,
            )
            deliveries.append(delivery)
        
        logger.warning(f"Operator notification created: case={case.case_number}")
        
        # TODO: 운영자 콘솔에 실시간 알림 표시 (WebSocket)
        
        return deliveries
    
    async def _notify_emergency(
        self,
        case: CareCase,
        stage: int,
        channels: List[str],
    ) -> List[NotificationDelivery]:
        """119 응급 알림"""
        deliveries = []
        
        # Alert 생성
        alert = await self._create_alert(
            case=case,
            stage=stage,
            timeout_seconds=0,
        )
        
        for channel_str in channels:
            try:
                channel = NotificationChannel(channel_str) if channel_str in [c.value for c in NotificationChannel] else NotificationChannel.PUSH
            except ValueError:
                channel = NotificationChannel.PUSH
            
            delivery = await self._create_delivery(
                alert=alert,
                channel=channel,
            )
            deliveries.append(delivery)
        
        logger.warning(f"119 EMERGENCY notification: case={case.case_number}")
        
        # TODO: 119 연계 API 호출
        # TODO: 모든 보호자에게 긴급 알림 발송
        
        audit_logger.log_action(
            user_id="system",
            action="emergency_119_notified",
            resource_type="care_case",
            resource_id=str(case.id),
            details={
                "case_number": case.case_number,
                "user_id": str(case.user_id),
            },
        )
        
        return deliveries
    
    async def _create_delivery(
        self,
        alert: Alert,
        channel: NotificationChannel,
        recipient_masked: Optional[str] = None,
    ) -> NotificationDelivery:
        """알림 배달 기록 생성"""
        delivery = NotificationDelivery(
            id=uuid.uuid4(),
            alert_id=alert.id,
            channel=channel,
            status=AlertStatus.PENDING,
            recipient_masked=recipient_masked,
            attempt_count=0,
        )
        
        self.db.add(delivery)
        await self.db.commit()
        await self.db.refresh(delivery)
        
        return delivery
    
    async def _send_via_channel(
        self,
        delivery: NotificationDelivery,
        channel: NotificationChannel,
        guardian: Optional[Guardian] = None,
        message: str = "",
    ):
        """채널별 실제 발송 처리"""
        try:
            delivery.attempt_count += 1
            
            if channel == NotificationChannel.PUSH:
                await self._send_push(delivery, guardian, message)
            elif channel == NotificationChannel.SMS:
                await self._send_sms(delivery, guardian, message)
            elif channel == NotificationChannel.VOICE_CALL:
                await self._send_call(delivery, guardian, message)
            
            delivery.status = AlertStatus.SENT
            delivery.sent_at = datetime.now(timezone.utc)
            
            # Alert 상태도 업데이트
            result = await self.db.execute(
                select(Alert).where(Alert.id == delivery.alert_id)
            )
            alert = result.scalar_one_or_none()
            if alert:
                alert.status = AlertStatus.SENT
                alert.sent_at = datetime.now(timezone.utc)
            
        except Exception as e:
            delivery.status = AlertStatus.FAILED
            delivery.error_message = str(e)
            logger.error(f"Notification delivery failed: {e}")
        
        await self.db.commit()
    
    async def _send_push(
        self,
        delivery: NotificationDelivery,
        guardian: Optional[Guardian],
        message: str,
    ):
        """Push 알림 발송 (FCM/APNs)"""
        # TODO: FCM/APNs 연동
        logger.info(f"Push notification sent: delivery_id={delivery.id}")
    
    async def _send_sms(
        self,
        delivery: NotificationDelivery,
        guardian: Optional[Guardian],
        message: str,
    ):
        """SMS 발송"""
        # TODO: SMS 서비스 연동
        logger.info(f"SMS sent: delivery_id={delivery.id}")
    
    async def _send_call(
        self,
        delivery: NotificationDelivery,
        guardian: Optional[Guardian],
        message: str,
    ):
        """전화 발신 (TTS)"""
        # TODO: TTS 전화 서비스 연동
        logger.info(f"Call initiated: delivery_id={delivery.id}")
    
    async def mark_as_delivered(
        self,
        delivery_id: uuid.UUID,
    ) -> Optional[NotificationDelivery]:
        """알림 전달 확인"""
        result = await self.db.execute(
            select(NotificationDelivery).where(NotificationDelivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        
        if not delivery:
            return None
        
        delivery.status = AlertStatus.DELIVERED
        delivery.delivered_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(delivery)
        
        return delivery
    
    async def acknowledge_alert(
        self,
        alert_id: uuid.UUID,
        acknowledger_id: str,
        acknowledger_type: str = "guardian",
        ack_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """알림 ACK 처리"""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        
        if not alert:
            return None
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.ack_data = {
            "acknowledger_id": acknowledger_id,
            "acknowledger_type": acknowledger_type,
            **(ack_data or {}),
        }
        
        # 연결된 케이스 ACK 처리
        from app.services.event import CaseService
        
        case_service = CaseService(self.db)
        await case_service.acknowledge(
            case_id=alert.case_id,
            acknowledger_type=acknowledger_type,
            acknowledger_id=acknowledger_id,
        )
        
        await self.db.commit()
        await self.db.refresh(alert)
        
        logger.info(
            f"Alert acknowledged: id={alert_id}, "
            f"by={acknowledger_type}:{acknowledger_id}"
        )
        
        return alert
    
    async def get_pending_alerts(
        self,
        case_id: Optional[uuid.UUID] = None,
    ) -> List[Alert]:
        """대기 중인 알림 조회"""
        query = select(Alert).where(
            Alert.status.in_([AlertStatus.PENDING, AlertStatus.SENT])
        )
        
        if case_id:
            query = query.where(Alert.case_id == case_id)
        
        query = query.order_by(Alert.scheduled_at)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def timeout_expired_alerts(self) -> List[Alert]:
        """타임아웃된 알림 처리"""
        now = datetime.now(timezone.utc)
        
        result = await self.db.execute(
            select(Alert).where(
                Alert.status.in_([AlertStatus.PENDING, AlertStatus.SENT]),
            )
        )
        alerts = result.scalars().all()
        
        timed_out = []
        for alert in alerts:
            # 타임아웃 체크
            deadline = alert.scheduled_at + timedelta(seconds=alert.timeout_seconds)
            if now > deadline and alert.timeout_seconds > 0:
                alert.status = AlertStatus.TIMEOUT
                alert.timeout_at = now
                timed_out.append(alert)
        
        if timed_out:
            await self.db.commit()
        
        return timed_out
