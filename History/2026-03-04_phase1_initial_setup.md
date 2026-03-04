# Phase 1: 프로젝트 초기화 및 기본 구조 설정

**날짜**: 2026-03-04  
**작업자**: AI Assistant  
**브랜치**: main (초기 설정)

## 요청 내용

개발 계획 리뷰 후 Phase 1 개발 시작 요청

## 수행 내용

### 1. 프로젝트 구조 생성

```
aiboocare/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   │   ├── config.py       # 환경변수 기반 설정
│   │   │   ├── security.py     # 비밀번호, JWT, PII 암호화
│   │   │   └── logging.py      # 로깅 및 감사 로그
│   │   ├── db/
│   │   │   └── session.py      # SQLAlchemy 세션 관리
│   │   ├── models/             # SQLAlchemy ORM 모델
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── workers/
│   │   └── main.py             # FastAPI 앱 진입점
│   ├── alembic/                # DB 마이그레이션
│   ├── tests/                  # pytest 테스트
│   ├── requirements.txt
│   ├── Dockerfile
│   └── env.example
├── docker/
│   ├── docker-compose.yml
│   └── mosquitto/config/
└── History/
```

### 2. Docker Compose 환경 구성

- PostgreSQL 15 + TimescaleDB
- Redis 7
- MQTT Broker (Mosquitto)
- FastAPI Backend

### 3. SQLAlchemy 모델 생성

PRD 섹션 4에 따른 전체 DB 스키마 구현:

**사용자/기기:**
- `CareUser`: 대상자 기본 정보
- `CareUserPII`: PII 분리 저장 (AES-256-GCM 암호화)
- `Guardian`: 보호자 정보
- `AdminUser`: 관리자/운영자 계정
- `CareDevice`: IoT 기기 정보

**이벤트/시계열:**
- `Measurement`: TimescaleDB 하이퍼테이블
- `CareEvent`: 감지 이벤트 (낙상, 무활동 등)
- `CareCase`: 케이스(티켓)
- `CaseAction`: 상태 변경 이력 (Audit Log)

**알림:**
- `Alert`: 알림 트리거
- `NotificationDelivery`: 채널별 전송 상태

**정책 엔진:**
- `PolicyBundle`: 정책 버전 관리
- `PolicyThreshold`: 센서 임계치
- `EscalationPlan`: 콜 트리 단계 설정
- `PolicyRule`: JSON Schema 기반 복합 조건 룰

### 4. 보안 구현 (ISMS-P 준수)

- 비밀번호: BCrypt 해싱
- JWT: Access/Refresh Token 분리
- PII 암호화: AES-256-GCM (cryptography 라이브러리)
- Refresh Token: DB에 해시로 저장
- 로깅: 민감정보 자동 마스킹
- 감사 로그: AuditLogger 클래스

### 5. 테스트 코드 작성

- `tests/conftest.py`: pytest 픽스처 설정
- `tests/test_health.py`: 헬스체크 API 테스트
- `tests/test_security.py`: 보안 유틸리티 테스트

## 참고 자료

- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [cryptography - AESGCM](https://cryptography.io/en/latest/hazmat/primitives/aead/)
- [passlib BCrypt](https://passlib.readthedocs.io/)
- [python-jose JWT](https://python-jose.readthedocs.io/)

## 다음 단계

- [ ] Alembic 초기 마이그레이션 생성 및 실행
- [ ] Phase 2: Policy REST API 구축
- [ ] Phase 2: 인증/권한 시스템 구현

## 변경된 파일 목록

### 신규 생성
- `backend/requirements.txt`
- `backend/Dockerfile`
- `backend/env.example`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/app/core/*`
- `backend/app/db/*`
- `backend/app/models/*`
- `backend/app/api/*`
- `backend/app/schemas/__init__.py`
- `backend/app/services/__init__.py`
- `backend/app/workers/__init__.py`
- `backend/tests/*`
- `docker/docker-compose.yml`
- `docker/mosquitto/config/mosquitto.conf`

### 수정
- `README.md`: 프로젝트 문서 업데이트
