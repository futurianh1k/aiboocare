"""
디바이스 연동 모듈

- MQTT 프로토콜 정의
- 디바이스 프로비저닝
- OTA 업데이트 관리
- 펌웨어 버전 관리

디바이스 종류:
- ESP32-S3: 음성 인터페이스, 센서 허브
- Raspberry Pi: AI 처리, 카메라
"""

from app.device.mqtt_protocol import MQTTProtocol, MQTTTopic
from app.device.provisioning import DeviceProvisioningService

__all__ = [
    "MQTTProtocol",
    "MQTTTopic",
    "DeviceProvisioningService",
]
