-- TimescaleDB 확장 활성화
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- UUID 확장
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 초기화 완료 메시지
DO $$
BEGIN
    RAISE NOTICE 'AI Care Companion Database initialized with TimescaleDB';
END $$;
