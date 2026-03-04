"""
MQTT 이벤트 수신 워커

MQTT 브로커에서 이벤트/측정 데이터를 수신하여 처리합니다.

토픽 구조:
- aiboocare/devices/{serial}/events    - 이벤트 수신
- aiboocare/devices/{serial}/measurements - 측정 데이터 수신
- aiboocare/devices/{serial}/status    - 상태/Heartbeat 수신

메시지 형식 (JSON):
{
    "serial_number": "DEV-001",
    "event_type": "fall",
    "severity": "critical",
    "timestamp": 1709570000000,
    "data": {...}
}
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiomqtt
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.db.session import async_session_maker
from app.schemas.event import MQTTEventPayload, MQTTMeasurementPayload
from app.services.device import DeviceService
from app.services.event import EventService, MeasurementService


class MQTTWorker:
    """MQTT 이벤트 수신 워커"""
    
    # 토픽 패턴
    TOPIC_EVENTS = "aiboocare/devices/+/events"
    TOPIC_MEASUREMENTS = "aiboocare/devices/+/measurements"
    TOPIC_STATUS = "aiboocare/devices/+/status"
    
    def __init__(self):
        self.running = False
        self._client: Optional[aiomqtt.Client] = None
    
    @asynccontextmanager
    async def _get_db_session(self):
        """데이터베이스 세션 컨텍스트 매니저"""
        async with async_session_maker() as session:
            try:
                yield session
            finally:
                await session.close()
    
    async def start(self):
        """워커 시작"""
        self.running = True
        
        logger.info(
            f"Starting MQTT worker: "
            f"broker={settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}"
        )
        
        while self.running:
            try:
                await self._run()
            except aiomqtt.MqttError as e:
                logger.error(f"MQTT connection error: {e}")
                if self.running:
                    logger.info("Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"MQTT worker error: {e}")
                if self.running:
                    await asyncio.sleep(5)
    
    async def stop(self):
        """워커 중지"""
        self.running = False
        logger.info("MQTT worker stopping...")
    
    async def _run(self):
        """MQTT 클라이언트 실행"""
        async with aiomqtt.Client(
            hostname=settings.MQTT_BROKER_HOST,
            port=settings.MQTT_BROKER_PORT,
            username=settings.MQTT_USERNAME,
            password=settings.MQTT_PASSWORD,
            identifier=settings.MQTT_CLIENT_ID,
        ) as client:
            self._client = client
            
            # 토픽 구독
            await client.subscribe(self.TOPIC_EVENTS)
            await client.subscribe(self.TOPIC_MEASUREMENTS)
            await client.subscribe(self.TOPIC_STATUS)
            
            logger.info(
                f"MQTT subscribed to topics: "
                f"{self.TOPIC_EVENTS}, {self.TOPIC_MEASUREMENTS}, {self.TOPIC_STATUS}"
            )
            
            # 메시지 수신 루프
            async for message in client.messages:
                if not self.running:
                    break
                
                try:
                    await self._handle_message(message)
                except Exception as e:
                    logger.error(f"Error handling MQTT message: {e}")
    
    async def _handle_message(self, message: aiomqtt.Message):
        """메시지 처리"""
        topic = str(message.topic)
        payload = message.payload
        
        # JSON 파싱
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in MQTT message: topic={topic}")
            return
        
        # 토픽에서 일련번호 추출
        topic_parts = topic.split("/")
        if len(topic_parts) < 4:
            logger.warning(f"Invalid topic format: {topic}")
            return
        
        serial_number = topic_parts[2]
        message_type = topic_parts[3]
        
        logger.debug(
            f"MQTT message received: "
            f"topic={topic}, serial={serial_number}, type={message_type}"
        )
        
        # 메시지 타입별 처리
        if message_type == "events":
            await self._handle_event(serial_number, data)
        elif message_type == "measurements":
            await self._handle_measurement(serial_number, data)
        elif message_type == "status":
            await self._handle_status(serial_number, data)
    
    async def _handle_event(self, serial_number: str, data: Dict[str, Any]):
        """이벤트 메시지 처리"""
        try:
            # 데이터 검증
            data["serial_number"] = serial_number
            payload = MQTTEventPayload(**data)
            
            # 타임스탬프 변환
            occurred_at = datetime.now(timezone.utc)
            if payload.timestamp:
                occurred_at = datetime.fromtimestamp(
                    payload.timestamp / 1000,
                    tz=timezone.utc,
                )
            
            async with self._get_db_session() as session:
                from app.schemas.event import EventCreateFromDevice
                
                event_data = EventCreateFromDevice(
                    serial_number=serial_number,
                    event_type=payload.event_type,
                    severity=payload.severity,
                    occurred_at=occurred_at,
                    event_data=payload.data,
                )
                
                service = EventService(session)
                event, case = await service.create_event_from_device(event_data)
                
                if event:
                    logger.info(
                        f"Event created from MQTT: "
                        f"serial={serial_number}, "
                        f"type={payload.event_type}, "
                        f"case={case.case_number if case else None}"
                    )
                    
                    # 즉시 에스컬레이션 필요 여부 확인
                    if case and self._needs_immediate_escalation(event):
                        await self._trigger_immediate_escalation(session, case, event)
                else:
                    logger.warning(
                        f"Failed to create event from MQTT: serial={serial_number}"
                    )
        
        except ValidationError as e:
            logger.warning(f"Invalid event payload: {e}")
        except Exception as e:
            logger.error(f"Error handling event: {e}")
    
    async def _handle_measurement(self, serial_number: str, data: Dict[str, Any]):
        """측정 데이터 메시지 처리"""
        try:
            data["serial_number"] = serial_number
            payload = MQTTMeasurementPayload(**data)
            
            # 타임스탬프 변환
            recorded_at = datetime.now(timezone.utc)
            if payload.timestamp:
                recorded_at = datetime.fromtimestamp(
                    payload.timestamp / 1000,
                    tz=timezone.utc,
                )
            
            async with self._get_db_session() as session:
                # 기기 조회
                device_service = DeviceService(session)
                device = await device_service.get_by_serial(serial_number)
                
                if not device or not device.user_id:
                    logger.warning(
                        f"Measurement from unknown/unassigned device: {serial_number}"
                    )
                    return
                
                from app.schemas.event import MeasurementCreate
                
                measurement_data = MeasurementCreate(
                    user_id=device.user_id,
                    device_id=device.id,
                    measurement_type=payload.measurement_type,
                    recorded_at=recorded_at,
                    value=payload.value,
                    value_json=payload.data,
                    unit=payload.unit,
                )
                
                measurement_service = MeasurementService(session)
                await measurement_service.create(measurement_data)
                
                logger.debug(
                    f"Measurement saved: "
                    f"serial={serial_number}, "
                    f"type={payload.measurement_type}"
                )
                
                # 이상값 감지 (Rule Evaluator 호출)
                await self._check_measurement_anomaly(
                    session, device, payload, recorded_at
                )
        
        except ValidationError as e:
            logger.warning(f"Invalid measurement payload: {e}")
        except Exception as e:
            logger.error(f"Error handling measurement: {e}")
    
    async def _handle_status(self, serial_number: str, data: Dict[str, Any]):
        """상태/Heartbeat 메시지 처리"""
        try:
            async with self._get_db_session() as session:
                from app.schemas.device import DeviceStatusUpdate
                
                status_data = DeviceStatusUpdate(
                    battery_level=data.get("battery_level"),
                    wifi_rssi=data.get("wifi_rssi"),
                    cpu_temp=data.get("cpu_temp"),
                )
                
                device_service = DeviceService(session)
                await device_service.process_heartbeat(serial_number, status_data)
                
                logger.debug(f"Heartbeat processed: serial={serial_number}")
        
        except Exception as e:
            logger.error(f"Error handling status: {e}")
    
    def _needs_immediate_escalation(self, event) -> bool:
        """즉시 에스컬레이션 필요 여부 확인
        
        즉시 119 에스컬레이션 조건:
        - 응급 키워드 발화
        - SpO2 < 90% 지속 + 호흡곤란
        - 낙상 후 무응답
        """
        from app.models.event import EventSeverity, EventType
        
        # EMERGENCY 심각도는 즉시 에스컬레이션
        if event.severity == EventSeverity.EMERGENCY:
            return True
        
        # 응급 키워드 발화
        if event.event_type == EventType.EMERGENCY_VOICE:
            return True
        
        # 낙상 + CRITICAL
        if event.event_type == EventType.FALL and event.severity == EventSeverity.CRITICAL:
            return True
        
        return False
    
    async def _trigger_immediate_escalation(self, session, case, event):
        """즉시 에스컬레이션 트리거"""
        from app.services.event import CaseService
        
        logger.warning(
            f"IMMEDIATE ESCALATION TRIGGERED: "
            f"case={case.case_number}, "
            f"event_type={event.event_type.value}"
        )
        
        case_service = CaseService(session)
        await case_service.escalate(
            case_id=case.id,
            to_stage=5,  # 119 단계
            current_user_id="system",
        )
        
        # TODO: 119 연계 API 호출 또는 알림 발송
    
    async def _check_measurement_anomaly(
        self,
        session,
        device,
        payload: MQTTMeasurementPayload,
        recorded_at: datetime,
    ):
        """측정값 이상 감지 및 이벤트 생성
        
        임계치:
        - SpO2 < 90% → low_spo2 이벤트
        - 심박수 < 40 또는 > 120 → abnormal_vital 이벤트
        """
        event_type = None
        severity = "warning"
        description = None
        
        if payload.measurement_type == "spo2" and payload.value:
            if payload.value < 90:
                event_type = "low_spo2"
                severity = "critical"
                description = f"SpO2 저하 감지: {payload.value}%"
            elif payload.value < 94:
                event_type = "low_spo2"
                severity = "warning"
                description = f"SpO2 주의: {payload.value}%"
        
        elif payload.measurement_type == "heart_rate" and payload.value:
            if payload.value < 40 or payload.value > 120:
                event_type = "abnormal_vital"
                severity = "critical" if payload.value < 30 or payload.value > 150 else "warning"
                description = f"비정상 심박수: {payload.value} bpm"
        
        if event_type:
            from app.schemas.event import EventCreate
            
            event_data = EventCreate(
                user_id=device.user_id,
                device_id=device.id,
                event_type=event_type,
                severity=severity,
                occurred_at=recorded_at,
                event_data={
                    "measurement_type": payload.measurement_type,
                    "value": payload.value,
                    "unit": payload.unit,
                },
                description=description,
            )
            
            event_service = EventService(session)
            event, case = await event_service.create_event(event_data)
            
            logger.info(
                f"Anomaly event created: "
                f"type={event_type}, "
                f"value={payload.value}"
            )


# 전역 워커 인스턴스
mqtt_worker = MQTTWorker()


async def start_mqtt_worker():
    """MQTT 워커 시작 (앱 시작 시 호출)"""
    await mqtt_worker.start()


async def stop_mqtt_worker():
    """MQTT 워커 중지 (앱 종료 시 호출)"""
    await mqtt_worker.stop()
