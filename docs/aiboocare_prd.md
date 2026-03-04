PRD: AI Care Companion & Policy Engine (for Cursor)
1. 프로젝트 개요 (Project Overview)
본 프로젝트는 단순한 AI 장난감을 넘어, 독거노인 돌봄 및 원격의료 플랫폼으로 확장 가능한 **'AI 돌봄 어시스턴트 디바이스(AI Care Companion)'**와 이를 관리하는 **'백엔드/관제 시스템'**을 구축하는 것입니다.
+2


핵심 목표: 24시간 AI 대화, 건강 모니터링, 이상 상황(낙상/무활동) 감지, 원격 진료 연계.
+2


주요 특징: 엣지(디바이스) 로컬 판단과 클라우드 AI의 결합, 동적 정책 룰 엔진(Policy Engine) 도입, 단계별 알림 에스컬레이션(Call Tree).
+4

2. 기술 스택 (Tech Stack Requirements)
Cursor가 프로젝트 셋업 시 참고할 주요 기술 스택입니다.

Backend / API: Python (FastAPI) - 비동기 처리 및 OpenAPI(Swagger) 자동 생성 활용.


Database: PostgreSQL + TimescaleDB (시계열 데이터용).


IoT Messaging: MQTT Broker.


AI Models: Whisper (STT), Qwen/Gemma (LLM), VITS (TTS).

Infrastructure: Ubuntu 24.04 기반 Docker 컨테이너 환경 배포 최적화.

3. 시스템 아키텍처 (System Architecture)
Cursor는 다음 계층(Layer) 구조를 바탕으로 코드를 모듈화해야 합니다.


Home Device Layer (Edge): ESP32-S3 또는 Raspberry Pi 기반. 마이크, 스피커, IMU, 레이더 센서 및 BLE 연동 기능을 포함합니다. Wake Word 엔진, Safety Rule Engine(1차 판단), 오프라인 Fallback 기능이 로컬에서 동작합니다.
+4


Connectivity Layer: MQTT(상태/이벤트/Heartbeat), HTTPS/REST(설정/정책/리포트), WebRTC(음성/영상) 통신을 담당합니다.


Cloud AI Layer: 실시간 STT 스트리밍, LLM 기반 의도 분류 및 NLU, TTS 기능을 수행하며, 증상 및 패턴 기반 위험도 분류기(Risk Classifier)를 포함합니다.
+2


Care Service Layer: 이벤트 수신 시 Workflow Engine을 통해 알림 단계를 제어(Call Tree)하고, 관제 콘솔용 대시보드 API를 제공합니다.
+2

4. 데이터베이스 스키마 (Database Schema)
PostgreSQL DDL 작성을 위한 핵심 스키마 요약입니다. Cursor에게 SQLAlchemy 또는 Prisma 모델 생성을 지시할 때 사용하세요.

사용자 및 기기:


care_user: 대상자 기본 정보 및 동의 상태 플래그. PII(개인식별정보)는 care_user_pii 테이블로 분리합니다.
+1


care_device: 기기 모델, 시리얼, 하드웨어 스펙, 상태 정보.

이벤트 및 시계열 데이터:


measurement: 혈압, SpO2, 활동량 등 생체/센서 시계열 데이터 (TimescaleDB 권장).
+1


care_event: 낙상, 무활동, 응급 버튼 등 감지된 사건의 상태(open, resolved 등) 및 심각도.
+2

워크플로우 및 알림:


care_case: 이벤트를 처리 관점으로 묶은 티켓 단위. 동일 사용자의 연속된 이벤트는 병합 처리합니다.
+2


alert & notification_delivery: 발송 논리와 채널별 전송 상태를 분리하여 관리합니다.
+1


case_action: 보호자 확인, 조치, 119 연락 등 상태 변경 이력을 기록합니다.

정책 룰 엔진 (Policy Engine):


policy_bundle: 정책 버전 관리 패키지.


policy_threshold: 센서 임계치 (예: SpO2 < 90% 지속).


escalation_plan: 콜 트리 단계별 타임아웃 및 타겟 설정.


policy_rule: 즉시 119 출동과 같은 복합 조건 룰. JSON Schema 기반으로 룰과 액션을 정의합니다.
+2

5. 핵심 로직: 콜 트리 및 워크플로우 (Core Workflows)
Cursor가 구현해야 할 상태 전이 및 알림 에스컬레이션 로직입니다.


이벤트 발생: 센서나 음성으로 이상이 감지되면 care_event가 'open' 상태로 생성됩니다.


케이스 병합: 30분 내 동일 그룹의 이벤트가 발생하면 기존 케이스에 병합(Merge)합니다.
+1


즉시 119 에스컬레이션 (Hard Rule): 응급 키워드 발화, SpO2 90% 미만 지속 + 호흡곤란, 혹은 낙상 후 60초 무동작 시 중간 단계를 생략하고 즉시 119 연계 케이스로 승격합니다.
+2

단계적 콜 트리 (Call Tree Escalation):

Stage 1: 보호자 1 (타임아웃 60초).

Stage 2: 보호자 2 (타임아웃 90초).

Stage 3: 요양보호사/기관 (타임아웃 120초).

Stage 4: 관제센터/운영자 (타임아웃 60초).

각 Stage에서 응답(ACK)이 없으면 다음 단계로 새로운 알림을 발송하며, 이 모든 과정은 case_action 테이블에 기록됩니다.
+2

6. Cursor 개발 페이즈 (Implementation Plan)
이 섹션을 복사하여 Cursor의 프롬프트 창에 입력하여 단계별로 개발을 지시하세요.

Phase 1: Database Initialization

Prompt for Cursor: "PRD의 섹션 4를 참조하여 PostgreSQL용 DDL 스크립트를 작성해 줘. PII 데이터 분리, TimescaleDB 기반의 measurement 테이블 설계, 그리고 UUID를 기본 키로 사용하는 구조를 반영해."

Phase 2: Policy REST API 구축

Prompt for Cursor: "FastAPI를 사용하여 PRD의 Policy Engine 관련 테이블(policy_bundle, policy_threshold, escalation_plan, policy_rule)에 대한 CRUD 엔드포인트를 구현해 줘. rule_json과 action_json은 Pydantic을 활용해 JSON Schema 검증 로직을 포함해야 해."

Phase 3: Event & Workflow Engine (평가 엔진)

Prompt for Cursor: "MQTT 또는 API를 통해 들어오는 measurement 및 care_event 데이터를 평가하는 백그라운드 워커를 파이썬으로 작성해. PRD 섹션 5의 '케이스 병합' 및 '즉시 119 에스컬레이션' 단락(Short-circuit) 로직을 필수로 구현해."

Phase 4: Escalation Scheduler

Prompt for Cursor: "콜 트리(Call Tree) 타임아웃을 관리하는 스케줄러를 작성해. 특정 Stage의 타임아웃 시간이 지나면 alert 상태를 확인하고, 미응답 시 다음 Stage로 넘어가며 case_action을 기록하는 로직을 만들어 줘."