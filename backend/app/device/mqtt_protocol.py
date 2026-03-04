"""
MQTT 프로토콜 정의

디바이스-서버 간 MQTT 통신 규약을 정의합니다.

토픽 구조:
- aiboo/{device_id}/telemetry/{type}  # 디바이스 → 서버 (센서 데이터)
- aiboo/{device_id}/event/{type}      # 디바이스 → 서버 (이벤트)
- aiboo/{device_id}/cmd/{command}     # 서버 → 디바이스 (명령)
- aiboo/{device_id}/response/{cmd}    # 디바이스 → 서버 (명령 응답)
- aiboo/{device_id}/status            # 디바이스 → 서버 (상태/하트비트)

참고: QoS 레벨
- 0: 최대 1회 전송 (센서 데이터)
- 1: 최소 1회 전송 (이벤트)
- 2: 정확히 1회 전송 (중요 명령)
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MQTTTopic:
    """MQTT 토픽 생성 유틸리티"""
    
    PREFIX = "aiboo"
    
    # ============== 디바이스 → 서버 ==============
    
    @classmethod
    def telemetry(cls, device_id: str, telemetry_type: str) -> str:
        """텔레메트리 토픽
        
        Args:
            device_id: 디바이스 시리얼 번호
            telemetry_type: vital, activity, environment
        """
        return f"{cls.PREFIX}/{device_id}/telemetry/{telemetry_type}"
    
    @classmethod
    def event(cls, device_id: str, event_type: str) -> str:
        """이벤트 토픽
        
        Args:
            device_id: 디바이스 시리얼 번호
            event_type: fall, emergency, inactivity 등
        """
        return f"{cls.PREFIX}/{device_id}/event/{event_type}"
    
    @classmethod
    def status(cls, device_id: str) -> str:
        """상태/하트비트 토픽"""
        return f"{cls.PREFIX}/{device_id}/status"
    
    @classmethod
    def response(cls, device_id: str, command: str) -> str:
        """명령 응답 토픽"""
        return f"{cls.PREFIX}/{device_id}/response/{command}"
    
    @classmethod
    def audio(cls, device_id: str) -> str:
        """오디오 스트림 토픽"""
        return f"{cls.PREFIX}/{device_id}/audio/stream"
    
    # ============== 서버 → 디바이스 ==============
    
    @classmethod
    def command(cls, device_id: str, cmd: str) -> str:
        """명령 토픽
        
        Args:
            device_id: 디바이스 시리얼 번호
            cmd: config, reboot, ota, speak 등
        """
        return f"{cls.PREFIX}/{device_id}/cmd/{cmd}"
    
    @classmethod
    def tts_audio(cls, device_id: str) -> str:
        """TTS 오디오 전송 토픽"""
        return f"{cls.PREFIX}/{device_id}/cmd/audio"
    
    # ============== 구독 패턴 ==============
    
    @classmethod
    def subscribe_all_telemetry(cls) -> str:
        """모든 디바이스 텔레메트리 구독"""
        return f"{cls.PREFIX}/+/telemetry/#"
    
    @classmethod
    def subscribe_all_events(cls) -> str:
        """모든 디바이스 이벤트 구독"""
        return f"{cls.PREFIX}/+/event/#"
    
    @classmethod
    def subscribe_all_status(cls) -> str:
        """모든 디바이스 상태 구독"""
        return f"{cls.PREFIX}/+/status"
    
    @classmethod
    def subscribe_device(cls, device_id: str) -> str:
        """특정 디바이스 모든 메시지 구독"""
        return f"{cls.PREFIX}/{device_id}/#"


class TelemetryType(str, Enum):
    """텔레메트리 종류"""
    VITAL = "vital"          # 생체 데이터 (SpO2, 심박수 등)
    ACTIVITY = "activity"    # 활동 데이터 (가속도, 움직임)
    ENVIRONMENT = "environment"  # 환경 데이터 (온도, 습도)
    AUDIO_LEVEL = "audio_level"  # 오디오 레벨


class EventType(str, Enum):
    """이벤트 종류"""
    FALL = "fall"
    INACTIVITY = "inactivity"
    EMERGENCY_BUTTON = "emergency_button"
    EMERGENCY_VOICE = "emergency_voice"
    ABNORMAL_VITAL = "abnormal_vital"
    LOW_SPO2 = "low_spo2"


class CommandType(str, Enum):
    """명령 종류"""
    CONFIG = "config"          # 설정 변경
    REBOOT = "reboot"          # 재부팅
    OTA = "ota"                # OTA 업데이트
    SPEAK = "speak"            # TTS 재생
    PING = "ping"              # 연결 확인
    CALIBRATE = "calibrate"    # 센서 캘리브레이션
    FACTORY_RESET = "factory_reset"  # 공장 초기화


@dataclass
class MQTTMessage:
    """MQTT 메시지 기본 구조"""
    device_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    msg_id: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TelemetryMessage(MQTTMessage):
    """텔레메트리 메시지
    
    센서에서 수집한 데이터를 서버로 전송합니다.
    """
    type: str = ""  # vital, activity, environment
    data: Dict[str, Any] = field(default_factory=dict)
    
    # 예시 data 구조:
    # vital: {"spo2": 97, "heart_rate": 72, "body_temp": 36.5}
    # activity: {"accel_x": 0.1, "accel_y": 0.2, "accel_z": 9.8, "step_count": 1234}
    # environment: {"temperature": 24.5, "humidity": 55, "light": 300}


@dataclass
class EventMessage(MQTTMessage):
    """이벤트 메시지
    
    감지된 이벤트를 서버로 전송합니다.
    """
    event_type: str = ""  # fall, emergency_button 등
    severity: str = "warning"  # info, warning, critical, emergency
    data: Dict[str, Any] = field(default_factory=dict)
    
    # 예시 data 구조:
    # fall: {"impact_force": 2.5, "duration_ms": 150, "position": "bathroom"}
    # emergency_button: {"press_duration_ms": 1500}
    # emergency_voice: {"keyword": "살려줘", "confidence": 0.95}


@dataclass
class StatusMessage(MQTTMessage):
    """상태/하트비트 메시지
    
    디바이스 상태를 주기적으로 전송합니다 (기본 60초).
    """
    status: str = "online"  # online, busy, error
    firmware_version: str = ""
    uptime_seconds: int = 0
    free_heap: int = 0  # ESP32 힙 메모리
    wifi_rssi: int = 0  # WiFi 신호 강도
    battery_level: Optional[int] = None  # 배터리 레벨 (%)
    sensors: Dict[str, str] = field(default_factory=dict)  # 센서 상태


@dataclass
class CommandMessage(MQTTMessage):
    """명령 메시지 (서버 → 디바이스)"""
    command: str = ""  # config, reboot, ota, speak 등
    payload: Dict[str, Any] = field(default_factory=dict)
    
    # 예시 payload 구조:
    # config: {"telemetry_interval": 30, "event_sensitivity": "high"}
    # ota: {"url": "https://...", "version": "1.2.0", "md5": "abc123"}
    # speak: {"text": "약 드실 시간입니다", "voice": "nova"}


@dataclass
class ResponseMessage(MQTTMessage):
    """응답 메시지 (디바이스 → 서버)"""
    command: str = ""  # 원본 명령
    success: bool = True
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class MQTTProtocol:
    """MQTT 프로토콜 유틸리티"""
    
    # QoS 레벨 정의
    QOS_TELEMETRY = 0  # 센서 데이터는 손실 허용
    QOS_EVENT = 1      # 이벤트는 최소 1회 전달 보장
    QOS_COMMAND = 2    # 명령은 정확히 1회 전달
    
    # 메시지 크기 제한
    MAX_PAYLOAD_SIZE = 256 * 1024  # 256KB
    
    # 하트비트 간격
    HEARTBEAT_INTERVAL = 60  # 초
    
    @staticmethod
    def parse_telemetry(payload: bytes) -> Optional[TelemetryMessage]:
        """텔레메트리 메시지 파싱"""
        try:
            data = json.loads(payload.decode('utf-8'))
            return TelemetryMessage(**data)
        except Exception:
            return None
    
    @staticmethod
    def parse_event(payload: bytes) -> Optional[EventMessage]:
        """이벤트 메시지 파싱"""
        try:
            data = json.loads(payload.decode('utf-8'))
            return EventMessage(**data)
        except Exception:
            return None
    
    @staticmethod
    def parse_status(payload: bytes) -> Optional[StatusMessage]:
        """상태 메시지 파싱"""
        try:
            data = json.loads(payload.decode('utf-8'))
            return StatusMessage(**data)
        except Exception:
            return None
    
    @staticmethod
    def create_command(
        device_id: str,
        command: str,
        payload: Dict[str, Any],
        msg_id: Optional[str] = None,
    ) -> CommandMessage:
        """명령 메시지 생성"""
        import uuid as uuid_module
        return CommandMessage(
            device_id=device_id,
            command=command,
            payload=payload,
            msg_id=msg_id or str(uuid_module.uuid4()),
        )
    
    @staticmethod
    def create_speak_command(
        device_id: str,
        text: str,
        voice: str = "nova",
    ) -> CommandMessage:
        """TTS 재생 명령 생성"""
        return MQTTProtocol.create_command(
            device_id=device_id,
            command="speak",
            payload={"text": text, "voice": voice},
        )
    
    @staticmethod
    def create_ota_command(
        device_id: str,
        firmware_url: str,
        version: str,
        md5_hash: str,
    ) -> CommandMessage:
        """OTA 업데이트 명령 생성"""
        return MQTTProtocol.create_command(
            device_id=device_id,
            command="ota",
            payload={
                "url": firmware_url,
                "version": version,
                "md5": md5_hash,
            },
        )
    
    @staticmethod
    def extract_device_id(topic: str) -> Optional[str]:
        """토픽에서 디바이스 ID 추출
        
        예: aiboo/DEVICE001/telemetry/vital → DEVICE001
        """
        parts = topic.split('/')
        if len(parts) >= 2 and parts[0] == "aiboo":
            return parts[1]
        return None
    
    @staticmethod
    def get_message_type(topic: str) -> Optional[str]:
        """토픽에서 메시지 종류 추출
        
        예: aiboo/DEVICE001/event/fall → event
        """
        parts = topic.split('/')
        if len(parts) >= 3:
            return parts[2]
        return None
