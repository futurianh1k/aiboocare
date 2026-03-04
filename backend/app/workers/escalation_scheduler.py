"""
콜 트리 에스컬레이션 스케줄러

케이스의 타임아웃을 모니터링하고 자동 에스컬레이션을 수행합니다.

동작 방식:
1. 주기적으로 (매 10초) 에스컬레이션 대기 중인 케이스 확인
2. 타임아웃 초과 케이스 → 다음 단계로 자동 에스컬레이션
3. 최종 단계(119) 도달 시 → 119 연계 API 호출

참고: 콜 트리 구조
- Stage 1: 보호자 1차 (60초)
- Stage 2: 보호자 2차 (90초)
- Stage 3: 요양보호사/기관 (120초)
- Stage 4: 관제센터/운영자 (60초)
- Stage 5: 119 응급
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import audit_logger, logger
from app.db.session import async_session_maker
from app.models.event import ActionType, CareCase, CaseAction, CaseStatus
from app.models.policy import EscalationPlan


class EscalationScheduler:
    """에스컬레이션 스케줄러"""
    
    # 체크 주기 (초)
    CHECK_INTERVAL_SECONDS = 10
    
    def __init__(self):
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """스케줄러 시작"""
        self.running = True
        logger.info("Escalation scheduler starting...")
        
        while self.running:
            try:
                await self._check_escalations()
            except Exception as e:
                logger.error(f"Escalation scheduler error: {e}")
            
            await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)
    
    async def stop(self):
        """스케줄러 중지"""
        self.running = False
        logger.info("Escalation scheduler stopping...")
    
    async def _check_escalations(self):
        """에스컬레이션 필요한 케이스 확인 및 처리"""
        async with async_session_maker() as session:
            # 에스컬레이션 진행 중인 케이스 조회
            result = await session.execute(
                select(CareCase).where(
                    CareCase.status.in_([
                        CaseStatus.OPEN,
                        CaseStatus.ESCALATING,
                        CaseStatus.PENDING_ACK,
                    ])
                )
            )
            cases = result.scalars().all()
            
            for case in cases:
                await self._process_case(session, case)
    
    async def _process_case(self, session: AsyncSession, case: CareCase):
        """개별 케이스 에스컬레이션 처리"""
        # 현재 단계의 에스컬레이션 플랜 조회
        plan = await self._get_escalation_plan(session, case.current_escalation_stage)
        
        if not plan:
            # 플랜이 없으면 기본 타임아웃 사용
            timeout_seconds = 60
            auto_escalate = True
        else:
            timeout_seconds = plan.timeout_seconds
            auto_escalate = plan.auto_escalate
        
        # 마지막 액션 시간 조회
        last_action_time = await self._get_last_action_time(session, case.id)
        
        if not last_action_time:
            # 액션이 없으면 케이스 생성 시간 사용
            last_action_time = case.opened_at
        
        # 타임아웃 확인
        elapsed = (datetime.now(timezone.utc) - last_action_time).total_seconds()
        
        if elapsed >= timeout_seconds and auto_escalate:
            # 다음 단계로 에스컬레이션
            await self._escalate_case(session, case, plan)
    
    async def _get_escalation_plan(
        self,
        session: AsyncSession,
        stage: int,
    ) -> Optional[EscalationPlan]:
        """현재 단계의 에스컬레이션 플랜 조회"""
        # 활성 번들의 플랜 조회
        from app.models.policy import BundleStatus, PolicyBundle
        
        result = await session.execute(
            select(EscalationPlan)
            .join(PolicyBundle)
            .where(
                PolicyBundle.status == BundleStatus.ACTIVE,
                PolicyBundle.deleted_at.is_(None),
                EscalationPlan.stage == stage,
                EscalationPlan.is_active == True,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _get_last_action_time(
        self,
        session: AsyncSession,
        case_id: uuid.UUID,
    ) -> Optional[datetime]:
        """케이스의 마지막 액션 시간 조회"""
        result = await session.execute(
            select(CaseAction.created_at)
            .where(CaseAction.case_id == case_id)
            .order_by(CaseAction.created_at.desc())
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None
    
    async def _escalate_case(
        self,
        session: AsyncSession,
        case: CareCase,
        current_plan: Optional[EscalationPlan],
    ):
        """케이스 에스컬레이션 실행"""
        old_stage = case.current_escalation_stage
        new_stage = old_stage + 1
        
        # 다음 단계 플랜 조회
        next_plan = await self._get_escalation_plan(session, new_stage)
        
        if not next_plan:
            # 더 이상 단계가 없으면 119 연계
            if case.status != CaseStatus.ESCALATED_119:
                await self._escalate_to_119(session, case)
            return
        
        # 다음 단계로 에스컬레이션
        case.current_escalation_stage = new_stage
        case.status = CaseStatus.ESCALATING
        
        # 액션 기록
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action_type=ActionType.ESCALATED,
            from_stage=old_stage,
            to_stage=new_stage,
            action_data={
                "reason": "timeout",
                "target_type": next_plan.target_type,
                "notification_channels": next_plan.notification_channels,
            },
            note=f"타임아웃으로 자동 에스컬레이션: {next_plan.name}",
        )
        
        session.add(action)
        await session.commit()
        
        logger.info(
            f"Case escalated: {case.case_number} "
            f"stage {old_stage} -> {new_stage} ({next_plan.name})"
        )
        
        # 알림 발송
        await self._send_notification(session, case, next_plan)
    
    async def _escalate_to_119(self, session: AsyncSession, case: CareCase):
        """119 에스컬레이션"""
        logger.warning(f"ESCALATING TO 119: case={case.case_number}")
        
        case.status = CaseStatus.ESCALATED_119
        case.current_escalation_stage = 5
        
        action = CaseAction(
            id=uuid.uuid4(),
            case_id=case.id,
            action_type=ActionType.ESCALATED_119,
            from_stage=case.current_escalation_stage,
            to_stage=5,
            action_data={
                "reason": "all_stages_exhausted",
            },
            note="모든 단계 타임아웃으로 119 연계",
        )
        
        session.add(action)
        await session.commit()
        
        # TODO: 119 연계 API 호출
        # TODO: 모든 보호자에게 긴급 알림 발송
        
        audit_logger.log_action(
            user_id="system",
            action="escalated_to_119",
            resource_type="care_case",
            resource_id=str(case.id),
            details={
                "case_number": case.case_number,
                "reason": "all_stages_exhausted",
            },
        )
    
    async def _send_notification(
        self,
        session: AsyncSession,
        case: CareCase,
        plan: EscalationPlan,
    ):
        """에스컬레이션 알림 발송"""
        from app.services.notification import NotificationService
        
        notification_service = NotificationService(session)
        
        await notification_service.send_escalation_notification(
            case=case,
            stage=plan.stage,
            target_type=plan.target_type,
            channels=plan.notification_channels,
        )


# 전역 스케줄러 인스턴스
escalation_scheduler = EscalationScheduler()


async def start_escalation_scheduler():
    """에스컬레이션 스케줄러 시작"""
    await escalation_scheduler.start()


async def stop_escalation_scheduler():
    """에스컬레이션 스케줄러 중지"""
    await escalation_scheduler.stop()
