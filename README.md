# AI Care Companion (AI 돌봄 어시스턴트)

독거노인 돌봄을 위한 AI 어시스턴트 백엔드 시스템

## 프로젝트 개요

24시간 AI 대화, 건강 모니터링, 이상 상황(낙상/무활동) 감지, 원격 진료 연계 기능을 제공하는 독거노인 돌봄 플랫폼입니다.

## 기술 스택

- **Backend**: Python 3.11 + FastAPI
- **Database**: PostgreSQL 15 + TimescaleDB (시계열 데이터)
- **Cache**: Redis 7
- **Messaging**: MQTT (Mosquitto)
- **Container**: Docker + Docker Compose

## 프로젝트 구조

```
aiboocare/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI 라우터
│   │   ├── core/          # 설정, 보안, 의존성
│   │   ├── models/        # SQLAlchemy 모델
│   │   ├── schemas/       # Pydantic 스키마
│   │   ├── services/      # 비즈니스 로직
│   │   ├── workers/       # 백그라운드 워커
│   │   └── main.py
│   ├── alembic/           # DB 마이그레이션
│   ├── tests/             # 테스트 코드
│   └── requirements.txt
├── docker/
│   └── docker-compose.yml
├── docs/
└── History/               # 변경 이력 문서
```

## 빠른 시작

### 사전 요구사항

- Docker & Docker Compose
- Python 3.11+
- Git

### 개발 환경 설정 (Docker)

```bash
# 1. 저장소 클론
git clone <repository-url>
cd aiboocare

# 2. 환경변수 설정
cp backend/env.example backend/.env
# .env 파일을 편집하여 SECRET_KEY, DATABASE_PASSWORD 등 설정

# 3. Docker 컨테이너 시작
cd docker
docker compose up -d

# 4. 상태 확인
docker compose ps

# 5. 로그 확인
docker compose logs -f backend
```

### 개발 환경 설정 (로컬)

```bash
# 1. Python 가상환경 생성
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp env.example .env
# .env 파일 편집

# 4. 데이터베이스 마이그레이션
alembic upgrade head

# 5. 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API 문서

개발 모드에서 Swagger UI 및 ReDoc 문서에 접근할 수 있습니다:

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

## 테스트

```bash
cd backend

# 전체 테스트 실행
pytest

# 커버리지 리포트
pytest --cov=app --cov-report=html

# 특정 테스트 실행
pytest tests/test_security.py -v
```

## 데이터베이스 마이그레이션

```bash
cd backend

# 새 마이그레이션 생성
alembic revision --autogenerate -m "설명"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1
```

## 환경변수 설정

주요 환경변수 (자세한 내용은 `env.example` 참조):

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `SECRET_KEY` | JWT 서명용 비밀 키 (최소 32자) | ✅ |
| `DATABASE_PASSWORD` | PostgreSQL 비밀번호 | ✅ |
| `PII_ENCRYPTION_KEY` | PII 암호화 키 (32바이트 Base64) | ✅ |
| `DEBUG` | 디버그 모드 (true/false) | |
| `ENVIRONMENT` | 환경 (development/staging/production) | |

## 보안 가이드라인

이 프로젝트는 ISMS-P 수준의 보안 가이드라인을 준수합니다:

- 비밀번호: BCrypt 해싱
- JWT: HttpOnly + Secure + SameSite 쿠키
- PII: AES-256-GCM 암호화 저장
- 로깅: 민감정보 마스킹
- 감사: 모든 Admin 액션 기록

자세한 내용은 [개발자 지침](docs/A01.review.md)을 참조하세요.

## 라이선스

MIT License
