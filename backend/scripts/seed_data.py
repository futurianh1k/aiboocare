"""
초기 데이터 시드 스크립트

사용법:
    cd backend
    source venv/bin/activate
    export PYTHONPATH=/mnt/8tb01/cursorworks/aiboocare/backend
    python scripts/seed_data.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env", override=True)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import async_session_maker
from app.models import (
    AdminUser,
    BundleStatus,
    CareDevice,
    CareUser,
    ConsentStatus,
    DeviceStatus,
    EscalationPlan,
    Guardian,
    PolicyBundle,
    PolicyThreshold,
    UserRole,
)
from app.services.encryption import encrypt_pii


async def seed_admin_user(session: AsyncSession) -> AdminUser:
    """관리자 계정 생성"""
    # 이미 존재하는지 확인
    result = await session.execute(
        select(AdminUser).where(AdminUser.email == "admin@aiboocare.local")
    )
    existing = result.scalar_one_or_none()
    if existing:
        print("✓ Admin 계정이 이미 존재합니다.")
        return existing

    admin = AdminUser(
        email="admin@aiboocare.local",
        name="관리자",
        password_hash=hash_password("admin1234!"),  # 개발용 비밀번호
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(admin)
    await session.flush()
    print("✓ Admin 계정 생성 완료 (email: admin@aiboocare.local, password: admin1234!)")
    return admin


async def seed_operator_user(session: AsyncSession) -> AdminUser:
    """운영자 계정 생성"""
    result = await session.execute(
        select(AdminUser).where(AdminUser.email == "operator@aiboocare.local")
    )
    existing = result.scalar_one_or_none()
    if existing:
        print("✓ Operator 계정이 이미 존재합니다.")
        return existing

    operator = AdminUser(
        email="operator@aiboocare.local",
        name="운영자",
        password_hash=hash_password("operator1234!"),
        role=UserRole.OPERATOR,
        is_active=True,
    )
    session.add(operator)
    await session.flush()
    print("✓ Operator 계정 생성 완료 (email: operator@aiboocare.local, password: operator1234!)")
    return operator


async def seed_test_care_user(session: AsyncSession) -> CareUser:
    """테스트 돌봄 대상자 생성"""
    result = await session.execute(
        select(CareUser).limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        print("✓ 테스트 돌봄 대상자가 이미 존재합니다.")
        return existing

    from datetime import date as date_type
    care_user = CareUser(
        code="TEST-001",
        consent_status=ConsentStatus.CONSENTED,
        consent_date=date_type(2026, 3, 4),
        notes="테스트 사용자",
    )
    session.add(care_user)
    await session.flush()
    print(f"✓ 테스트 돌봄 대상자 생성 완료 (ID: {care_user.id})")
    return care_user


async def seed_test_guardian(session: AsyncSession, care_user: CareUser) -> Guardian:
    """테스트 보호자 생성"""
    result = await session.execute(
        select(Guardian).where(Guardian.care_user_id == care_user.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        print("✓ 테스트 보호자가 이미 존재합니다.")
        return existing

    guardian = Guardian(
        care_user_id=care_user.id,
        relationship_type="자녀",
        priority=1,
        name_encrypted=encrypt_pii("홍길동"),
        phone_encrypted=encrypt_pii("010-1234-5678"),
        email_encrypted=encrypt_pii("guardian@example.com"),
        receive_notifications=True,
        app_enabled=True,
        password_hash=hash_password("guardian1234!"),
    )
    session.add(guardian)
    await session.flush()
    print("✓ 테스트 보호자 생성 완료 (비밀번호: guardian1234!)")
    return guardian


async def seed_test_device(session: AsyncSession, care_user: CareUser) -> CareDevice:
    """테스트 디바이스 생성"""
    result = await session.execute(
        select(CareDevice).where(CareDevice.user_id == care_user.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        print("✓ 테스트 디바이스가 이미 존재합니다.")
        return existing

    from app.models.device import DeviceModel
    device = CareDevice(
        user_id=care_user.id,
        serial_number="ABC-TEST-001",
        device_model=DeviceModel.ESP32_S3,
        firmware_version="0.1.0",
        status=DeviceStatus.ACTIVE,
    )
    session.add(device)
    await session.flush()
    print(f"✓ 테스트 디바이스 생성 완료 (시리얼: ABC-TEST-001)")
    return device


async def seed_default_policy_bundle(session: AsyncSession) -> PolicyBundle:
    """기본 정책 번들 생성"""
    result = await session.execute(
        select(PolicyBundle).where(PolicyBundle.name == "기본 정책")
    )
    existing = result.scalar_one_or_none()
    if existing:
        print("✓ 기본 정책 번들이 이미 존재합니다.")
        return existing

    bundle = PolicyBundle(
        name="기본 정책",
        version="1.0.0",
        description="AI BooCare 기본 돌봄 정책",
        status=BundleStatus.ACTIVE,
    )
    session.add(bundle)
    await session.flush()
    print(f"✓ 기본 정책 번들 생성 완료 (ID: {bundle.id})")
    return bundle


async def seed_default_thresholds(session: AsyncSession, bundle: PolicyBundle):
    """기본 임계값 설정"""
    result = await session.execute(
        select(PolicyThreshold).where(PolicyThreshold.bundle_id == bundle.id)
    )
    existing = result.scalars().all()
    if existing:
        print(f"✓ 임계값 {len(existing)}개가 이미 존재합니다.")
        return

    thresholds = [
        # 심박수
        PolicyThreshold(
            bundle_id=bundle.id,
            measurement_type="heart_rate",
            warning_min=50.0,
            warning_max=100.0,
            critical_min=40.0,
            critical_max=120.0,
        ),
        # 산소포화도
        PolicyThreshold(
            bundle_id=bundle.id,
            measurement_type="spo2",
            warning_min=94.0,
            warning_max=100.0,
            critical_min=90.0,
            critical_max=100.0,
        ),
        # 혈압 (수축기)
        PolicyThreshold(
            bundle_id=bundle.id,
            measurement_type="blood_pressure_systolic",
            warning_min=90.0,
            warning_max=140.0,
            critical_min=80.0,
            critical_max=180.0,
        ),
        # 혈압 (이완기)
        PolicyThreshold(
            bundle_id=bundle.id,
            measurement_type="blood_pressure_diastolic",
            warning_min=60.0,
            warning_max=90.0,
            critical_min=50.0,
            critical_max=120.0,
        ),
        # 체온
        PolicyThreshold(
            bundle_id=bundle.id,
            measurement_type="temperature",
            warning_min=36.0,
            warning_max=37.5,
            critical_min=35.0,
            critical_max=39.0,
        ),
        # 혈당
        PolicyThreshold(
            bundle_id=bundle.id,
            measurement_type="blood_glucose",
            warning_min=70.0,
            warning_max=140.0,
            critical_min=54.0,
            critical_max=250.0,
        ),
        # 무활동 시간
        PolicyThreshold(
            bundle_id=bundle.id,
            measurement_type="inactivity_duration",
            warning_min=0.0,
            warning_max=120.0,  # 2시간
            critical_min=0.0,
            critical_max=180.0,  # 3시간
        ),
    ]
    session.add_all(thresholds)
    await session.flush()
    print(f"✓ 기본 임계값 {len(thresholds)}개 생성 완료")


async def seed_default_escalation_plan(session: AsyncSession, bundle: PolicyBundle):
    """기본 에스컬레이션 플랜 생성"""
    result = await session.execute(
        select(EscalationPlan).where(EscalationPlan.bundle_id == bundle.id)
    )
    existing = result.scalars().all()
    if existing:
        print(f"✓ 에스컬레이션 플랜 {len(existing)}개가 이미 존재합니다.")
        return

    plans = [
        EscalationPlan(
            bundle_id=bundle.id,
            stage=1,
            name="보호자 1차",
            target_type="guardian",
            timeout_seconds=60,
            notification_channels=["push", "sms"],
        ),
        EscalationPlan(
            bundle_id=bundle.id,
            stage=2,
            name="보호자 2차",
            target_type="guardian",
            timeout_seconds=90,
            notification_channels=["push", "sms", "voice"],
        ),
        EscalationPlan(
            bundle_id=bundle.id,
            stage=3,
            name="요양보호사/기관",
            target_type="caregiver",
            timeout_seconds=120,
            notification_channels=["voice", "push"],
        ),
        EscalationPlan(
            bundle_id=bundle.id,
            stage=4,
            name="관제센터/운영자",
            target_type="operator",
            timeout_seconds=60,
            notification_channels=["voice", "push"],
        ),
        EscalationPlan(
            bundle_id=bundle.id,
            stage=5,
            name="119 응급",
            target_type="emergency",
            timeout_seconds=0,  # 즉시
            notification_channels=["voice", "api"],
            auto_escalate=False,
        ),
    ]
    session.add_all(plans)
    await session.flush()
    print(f"✓ 에스컬레이션 플랜 {len(plans)}개 생성 완료 (5단계 콜 트리)")


async def main():
    """메인 시드 함수"""
    print("\n" + "=" * 50)
    print("AI BooCare 초기 데이터 시드")
    print("=" * 50 + "\n")

    async with async_session_maker() as session:
        try:
            # 1. Admin/Operator 계정
            print("\n[1/6] 관리자 계정 생성")
            await seed_admin_user(session)
            await seed_operator_user(session)

            # 2. 테스트 돌봄 대상자
            print("\n[2/6] 테스트 돌봄 대상자 생성")
            care_user = await seed_test_care_user(session)

            # 3. 테스트 보호자
            print("\n[3/6] 테스트 보호자 생성")
            await seed_test_guardian(session, care_user)

            # 4. 테스트 디바이스
            print("\n[4/6] 테스트 디바이스 생성")
            await seed_test_device(session, care_user)

            # 5. 기본 정책 번들
            print("\n[5/6] 기본 정책 번들 생성")
            bundle = await seed_default_policy_bundle(session)

            # 6. 기본 임계값 및 에스컬레이션 플랜
            print("\n[6/6] 임계값 및 에스컬레이션 플랜 생성")
            await seed_default_thresholds(session, bundle)
            await seed_default_escalation_plan(session, bundle)

            # 커밋
            await session.commit()

            print("\n" + "=" * 50)
            print("✅ 모든 초기 데이터 시드 완료!")
            print("=" * 50)
            print("\n📋 생성된 테스트 계정:")
            print("  - Admin: admin / admin1234!")
            print("  - Operator: operator / operator1234!")
            print("  - Guardian App: 01012345678 / guardian1234!")
            print()

        except Exception as e:
            await session.rollback()
            print(f"\n❌ 에러 발생: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
