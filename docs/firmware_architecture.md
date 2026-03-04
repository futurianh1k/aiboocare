# AI Care Companion - 디바이스 펌웨어 아키텍처

## 1. 개요

AI Care Companion 디바이스는 독거노인의 가정에 설치되어 다음 기능을 수행합니다:

- **음성 인터페이스**: 사용자와의 대화
- **센서 모니터링**: 생체 데이터, 활동, 환경 모니터링
- **이벤트 감지**: 낙상, 무활동, 응급 상황 감지
- **원격 통신**: MQTT를 통한 서버 연동

## 2. 지원 하드웨어

### ESP32-S3 기반

**용도**: 저전력 센서 허브, 음성 인터페이스

```
┌─────────────────────────────────────┐
│           ESP32-S3 DevKit           │
├─────────────────────────────────────┤
│  CPU: Xtensa LX7 Dual-core 240MHz   │
│  RAM: 512KB SRAM + 8MB PSRAM        │
│  Flash: 16MB                        │
│  WiFi: 802.11 b/g/n                 │
│  Bluetooth: BLE 5.0                 │
├─────────────────────────────────────┤
│  센서 연결:                          │
│  - I2S: 마이크 (INMP441)             │
│  - I2S: 스피커 (MAX98357A)           │
│  - I2C: SpO2 센서 (MAX30102)         │
│  - I2C: IMU (MPU6050)               │
│  - GPIO: 응급 버튼                   │
└─────────────────────────────────────┘
```

### Raspberry Pi 4/5 기반

**용도**: AI 처리, 카메라, 고급 센서

```
┌─────────────────────────────────────┐
│         Raspberry Pi 4/5            │
├─────────────────────────────────────┤
│  CPU: Cortex-A76 Quad-core          │
│  RAM: 4GB / 8GB                     │
│  Storage: microSD 32GB+             │
│  WiFi: 802.11 ac                    │
│  Ethernet: Gigabit                  │
├─────────────────────────────────────┤
│  추가 기능:                          │
│  - 카메라 모듈 (CSI)                 │
│  - mmWave 레이더 (UART)             │
│  - 로컬 AI 추론                     │
│  - ESP32 연동 (UART/SPI)            │
└─────────────────────────────────────┘
```

## 3. 소프트웨어 아키텍처

### ESP32-S3 펌웨어 구조

```
firmware/
├── main/
│   ├── main.c                 # 진입점
│   ├── app_config.h           # 설정
│   │
│   ├── network/
│   │   ├── wifi_manager.c     # WiFi 연결 관리
│   │   └── mqtt_client.c      # MQTT 클라이언트
│   │
│   ├── sensors/
│   │   ├── sensor_hub.c       # 센서 허브
│   │   ├── spo2_sensor.c      # SpO2 센서 (MAX30102)
│   │   ├── imu_sensor.c       # IMU (MPU6050)
│   │   └── button_handler.c   # 버튼 처리
│   │
│   ├── audio/
│   │   ├── audio_pipeline.c   # 오디오 파이프라인
│   │   ├── i2s_mic.c          # 마이크 입력
│   │   ├── i2s_speaker.c      # 스피커 출력
│   │   └── wake_word.c        # 웨이크워드 감지
│   │
│   ├── event/
│   │   ├── fall_detector.c    # 낙상 감지
│   │   ├── inactivity_monitor.c # 무활동 감지
│   │   └── emergency_handler.c  # 응급 처리
│   │
│   ├── ota/
│   │   └── ota_updater.c      # OTA 업데이트
│   │
│   └── utils/
│       ├── logger.c           # 로깅
│       └── nvs_storage.c      # 설정 저장
│
├── components/                 # 외부 컴포넌트
│   ├── esp-mqtt/
│   └── esp-tflite-micro/      # TFLite 추론 (웨이크워드)
│
├── partitions.csv             # 파티션 테이블
├── sdkconfig                  # ESP-IDF 설정
└── CMakeLists.txt
```

### Raspberry Pi 소프트웨어 구조

```
aiboo-device/
├── src/
│   ├── main.py                # 진입점
│   ├── config.py              # 설정 관리
│   │
│   ├── network/
│   │   ├── mqtt_client.py     # MQTT 클라이언트
│   │   └── api_client.py      # REST API 클라이언트
│   │
│   ├── sensors/
│   │   ├── sensor_manager.py  # 센서 관리자
│   │   ├── camera.py          # 카메라 모듈
│   │   ├── radar.py           # mmWave 레이더
│   │   └── esp32_bridge.py    # ESP32 연동
│   │
│   ├── audio/
│   │   ├── audio_manager.py   # 오디오 관리
│   │   ├── stt_client.py      # STT API 클라이언트
│   │   └── tts_player.py      # TTS 재생
│   │
│   ├── ai/
│   │   ├── local_inference.py # 로컬 AI 추론
│   │   ├── fall_detection.py  # 낙상 감지 모델
│   │   └── activity_recognition.py # 활동 인식
│   │
│   └── system/
│       ├── health_monitor.py  # 시스템 모니터링
│       └── ota_manager.py     # OTA 관리
│
├── models/                    # AI 모델 파일
│   ├── fall_detection.tflite
│   └── wake_word.tflite
│
├── config/
│   └── default.yaml           # 기본 설정
│
├── scripts/
│   ├── install.sh             # 설치 스크립트
│   └── update.sh              # 업데이트 스크립트
│
├── systemd/
│   └── aiboo-device.service   # systemd 서비스
│
├── requirements.txt
└── setup.py
```

## 4. MQTT 통신 프로토콜

### 토픽 구조

```
aiboo/{device_id}/telemetry/{type}   # 디바이스 → 서버 (센서 데이터)
aiboo/{device_id}/event/{type}       # 디바이스 → 서버 (이벤트)
aiboo/{device_id}/status             # 디바이스 → 서버 (하트비트)
aiboo/{device_id}/cmd/{command}      # 서버 → 디바이스 (명령)
aiboo/{device_id}/response/{cmd}     # 디바이스 → 서버 (응답)
```

### 메시지 형식 (JSON)

#### 텔레메트리 (생체 데이터)

```json
{
  "device_id": "DEVICE001",
  "timestamp": "2026-03-04T12:00:00Z",
  "type": "vital",
  "data": {
    "spo2": 97,
    "heart_rate": 72,
    "body_temp": 36.5
  }
}
```

#### 이벤트 (낙상 감지)

```json
{
  "device_id": "DEVICE001",
  "timestamp": "2026-03-04T12:00:00Z",
  "event_type": "fall",
  "severity": "critical",
  "data": {
    "impact_force": 2.5,
    "duration_ms": 150,
    "position": "bathroom"
  }
}
```

#### 상태/하트비트

```json
{
  "device_id": "DEVICE001",
  "timestamp": "2026-03-04T12:00:00Z",
  "status": "online",
  "firmware_version": "1.0.0",
  "uptime_seconds": 3600,
  "free_heap": 45000,
  "wifi_rssi": -45,
  "battery_level": 85,
  "sensors": {
    "spo2": "ok",
    "imu": "ok",
    "mic": "ok"
  }
}
```

#### 명령 (TTS 재생)

```json
{
  "device_id": "DEVICE001",
  "timestamp": "2026-03-04T12:00:00Z",
  "msg_id": "cmd_12345",
  "command": "speak",
  "payload": {
    "text": "약 드실 시간입니다",
    "voice": "nova"
  }
}
```

## 5. 센서 데이터 수집

### SpO2 센서 (MAX30102)

```c
// 측정 주기: 60초
// 데이터: SpO2 (%), 심박수 (bpm)

typedef struct {
    float spo2;         // 산소포화도 (%)
    float heart_rate;   // 심박수 (bpm)
    uint8_t confidence; // 신뢰도 (0-100)
} vital_data_t;
```

### IMU 센서 (MPU6050)

```c
// 측정 주기: 20ms (50Hz)
// 데이터: 가속도 (x, y, z), 자이로 (x, y, z)

typedef struct {
    float accel_x, accel_y, accel_z;  // g
    float gyro_x, gyro_y, gyro_z;     // dps
    float temperature;                 // °C
} imu_data_t;
```

### 낙상 감지 알고리즘

```
1. 자유낙하 감지: 가속도 크기 < 0.3g (200ms 이상)
2. 충격 감지: 가속도 크기 > 2.0g
3. 무동작 확인: 충격 후 60초간 큰 움직임 없음
4. 경고 발생: 음성 확인 요청
5. 무응답 시: 이벤트 전송 + 콜 트리 시작
```

## 6. 음성 인터페이스

### 웨이크워드 감지

```
- 웨이크워드: "아이부"
- 모델: TensorFlow Lite Micro
- 크기: ~50KB
- 추론 시간: ~20ms
```

### 오디오 파이프라인

```
마이크 → I2S → 버퍼 → 웨이크워드 감지 → 
                           ↓ (감지됨)
                      녹음 시작 → 
                           ↓ (발화 종료)
                      MQTT 전송 → 
                           ↓ (서버 응답)
                      TTS 수신 → I2S → 스피커
```

## 7. OTA 업데이트

### 업데이트 플로우

```
1. 디바이스: GET /device-mgmt/ota/check
2. 서버: 새 버전 정보 응답
3. 디바이스: 펌웨어 다운로드 (HTTPS)
4. 디바이스: MD5 검증
5. 디바이스: OTA 파티션에 쓰기
6. 디바이스: 재부팅
7. 디바이스: 부팅 검증 후 POST /device-mgmt/ota/status
```

### ESP32 파티션 테이블

```
# Name,   Type, SubType, Offset,  Size
nvs,      data, nvs,     0x9000,  0x6000
phy_init, data, phy,     0xf000,  0x1000
factory,  app,  factory, 0x10000, 1M
ota_0,    app,  ota_0,   0x110000, 1M
ota_1,    app,  ota_1,   0x210000, 1M
storage,  data, spiffs,  0x310000, 1M
```

## 8. 보안

### 디바이스 인증

```
1. 프로비저닝 시 토큰 발급 (시리얼 + 시크릿 해시)
2. MQTT 연결 시 토큰으로 인증
3. 토큰 30일 주기 갱신
```

### 통신 보안

```
- MQTT: TLS 1.2+
- REST API: HTTPS
- 펌웨어: MD5 무결성 검증
```

## 9. 개발 환경 설정

### ESP32-S3

```bash
# ESP-IDF 설치
git clone -b v5.1 --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
./install.sh esp32s3
source export.sh

# 프로젝트 빌드
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py flash monitor
```

### Raspberry Pi

```bash
# 의존성 설치
sudo apt update
sudo apt install -y python3-pip portaudio19-dev

# 프로젝트 설치
git clone https://github.com/futurianh1k/aiboo-device.git
cd aiboo-device
pip install -r requirements.txt

# 서비스 등록
sudo cp systemd/aiboo-device.service /etc/systemd/system/
sudo systemctl enable aiboo-device
sudo systemctl start aiboo-device
```

## 10. 참고 자료

- [ESP-IDF 문서](https://docs.espressif.com/projects/esp-idf/en/latest/)
- [MAX30102 데이터시트](https://www.maximintegrated.com/en/products/sensors/MAX30102.html)
- [MPU6050 데이터시트](https://invensense.tdk.com/products/motion-tracking/6-axis/mpu-6050/)
- [MQTT 5.0 스펙](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
