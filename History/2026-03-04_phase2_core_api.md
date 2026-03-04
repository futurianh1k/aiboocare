# Phase 2: Core REST API 완료

**날짜**: 2026-03-04  
**작업자**: AI Assistant

## 완료된 작업

### 1. 인증 API (`/api/v1/auth`)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/login` | POST | JWT 로그인 (HttpOnly 쿠키) |
| `/logout` | POST | 로그아웃 (토큰 무효화) |
| `/refresh` | POST | 토큰 갱신 |
| `/me` | GET | 현재 사용자 정보 |
| `/change-password` | POST | 비밀번호 변경 |

**보안 특징:**
- Access/Refresh Token을 HttpOnly + Secure + SameSite 쿠키로 전달
- Refresh Token DB 해시 저장 (토큰 재사용 공격 방지)
- 비밀번호 변경 시 모든 세션 무효화

### 2. 사용자 관리 API (`/api/v1/users`)

#### AdminUser (관리자)
| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/users/admin` | GET | Admin | 관리자 목록 조회 |
| `/users/admin/{id}` | GET | Admin | 관리자 상세 조회 |
| `/users/admin` | POST | Admin | 관리자 생성 |
| `/users/admin/{id}` | PATCH | Admin | 관리자 수정 |
| `/users/admin/{id}` | DELETE | Admin | 관리자 삭제 |

#### CareUser (대상자)
| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/users/care` | GET | Operator+ | 대상자 목록 조회 |
| `/users/care/{id}` | GET | Operator+ | 대상자 기본 정보 (PII 제외) |
| `/users/care/{id}/detail` | GET | Operator+ | 대상자 상세 (PII 포함, 감사 기록) |
| `/users/care` | POST | Operator+ | 대상자 등록 |
| `/users/care/{id}` | PATCH | Operator+ | 대상자 수정 |
| `/users/care/{id}` | DELETE | Admin | 대상자 삭제 |

**PII 처리:**
- 모든 PII는 AES-256-GCM으로 암호화하여 `care_user_pii` 테이블에 저장
- 목록/기본 조회 시 PII 제외
- 상세 조회 시 복호화하여 반환 + Audit Log 기록

### 3. 보호자 API (`/api/v1/guardians`)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/users/care/{id}/guardians` | GET | Operator+ | 보호자 목록 (PII 마스킹) |
| `/guardians/{id}` | GET | Operator+ | 보호자 상세 (PII 포함) |
| `/guardians` | POST | Operator+ | 보호자 등록 |
| `/guardians/{id}` | PATCH | Operator+ | 보호자 수정 |
| `/guardians/{id}` | DELETE | Operator+ | 보호자 삭제 |
| `/guardians/{id}/priority` | PATCH | Operator+ | 콜 트리 우선순위 변경 |

**PII 마스킹:**
- 이름: `홍길동` → `홍*동`
- 전화번호: `010-1234-5678` → `010-****-5678`

### 4. 기기 관리 API (`/api/v1/devices`)

| 엔드포인트 | 메서드 | 권한 | 설명 |
|-----------|--------|------|------|
| `/devices` | GET | Operator+ | 기기 목록 조회 |
| `/devices/{id}` | GET | Operator+ | 기기 상세 조회 |
| `/devices` | POST | Operator+ | 기기 등록 |
| `/devices/{id}` | PATCH | Operator+ | 기기 수정 |
| `/devices/{id}` | DELETE | Operator+ | 기기 삭제 |
| `/devices/{id}/assign/{user_id}` | POST | Operator+ | 기기 할당 |
| `/devices/{id}/unassign` | POST | Operator+ | 기기 할당 해제 |
| `/devices/heartbeat/{serial}` | POST | Device | Heartbeat |

## 생성된 파일

### 스키마 (`app/schemas/`)
- `auth.py` - 인증 관련 Pydantic 스키마
- `user.py` - 사용자/보호자 스키마
- `device.py` - 기기 스키마

### 서비스 (`app/services/`)
- `auth.py` - 인증 서비스 (로그인/토큰 관리)
- `user.py` - 사용자/보호자 서비스
- `device.py` - 기기 관리 서비스

### API 엔드포인트 (`app/api/v1/endpoints/`)
- `auth.py` - 인증 API
- `users.py` - 사용자 API
- `guardians.py` - 보호자 API
- `devices.py` - 기기 API

### 테스트 (`tests/`)
- `conftest.py` - pytest 픽스처
- `test_auth.py` - 인증 API 테스트

## 권한 체계

| Role | 설명 | 권한 범위 |
|------|------|----------|
| `admin` | 시스템 관리자 | 전체 접근 |
| `operator` | 관제센터 운영자 | 사용자/기기 관리 |
| `guardian` | 보호자 | 자신의 대상자만 조회 (향후 구현) |
| `caregiver` | 요양보호사 | 담당 대상자만 조회 (향후 구현) |

## 다음 단계

- **Phase 3**: Event Receiver 및 Workflow Engine
  - MQTT 이벤트 수신 워커
  - Rule Evaluator 서비스
  - Case Merger 로직
