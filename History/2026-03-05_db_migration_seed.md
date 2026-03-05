# 데이터베이스 마이그레이션 및 시드 완료

## 작업 일시
2026-03-05

## 완료 작업

### 1. Alembic 마이그레이션 실행
- 마이그레이션 파일 생성: `alembic/versions/20260305_1434_057a32160791_initial_schema.py`
- 19개 테이블 생성 완료

### 2. 생성된 테이블 목록
```
admin_user, alert, care_case, care_device, care_event, care_user, 
care_user_pii, case_action, escalation_plan, guardian, measurement, 
medical_record_sync, notification_delivery, policy_bundle, policy_rule, 
policy_threshold, pre_triage, telemedicine_session
```

### 3. 초기 데이터 시드
| 테이블 | 생성 수 | 설명 |
|--------|---------|------|
| admin_user | 2 | Admin, Operator 계정 |
| care_user | 1 | 테스트 돌봄 대상자 |
| guardian | 1 | 테스트 보호자 |
| care_device | 1 | ESP32-S3 테스트 디바이스 |
| policy_bundle | 1 | 기본 정책 번들 |
| policy_threshold | 7 | 센서 임계값 설정 |
| escalation_plan | 5 | 5단계 콜 트리 |

### 4. 테스트 계정 정보
| 계정 유형 | 이메일/ID | 비밀번호 |
|-----------|-----------|----------|
| Admin | admin@aiboocare.local | admin1234! |
| Operator | operator@aiboocare.local | operator1234! |
| Guardian (앱) | - | guardian1234! |

## 수정된 파일
- `backend/alembic/env.py` - 동기 방식으로 변경 (asyncpg → psycopg2)
- `backend/app/services/encryption.py` - encrypt_pii, decrypt_pii 헬퍼 함수 추가
- `backend/scripts/seed_data.py` - 초기 데이터 시드 스크립트 생성
- `backend/.env` - 환경변수 설정 파일 생성

## 환경 설정
- bcrypt 4.1.2로 다운그레이드 (passlib 호환성)
- PII_ENCRYPTION_KEY 32바이트 키 생성

## 미완료 (취소)
- **TimescaleDB 하이퍼테이블**: 기본 키 구조 변경 필요 (추후 진행)

## 다음 단계
1. 프론트엔드 API 연동
2. 백엔드 API 테스트
3. 서비스 실행 확인
