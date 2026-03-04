"""
Pre-triage (사전분류) 서비스

이벤트 발생 시 AI가 자동으로 사전분류 정보를 생성합니다.
의료기관 전달용 데이터를 FHIR 표준으로 변환합니다.

플로우:
1. 케이스 발생
2. AI가 증상 분석 및 응급도 평가
3. Pre-triage 생성
4. FHIR Bundle 변환
5. 의료기관 전송
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.event import CareCase
from app.models.telemedicine import PreTriage, TriageStatus, TriageUrgency
from app.models.user import CareUser
from app.services.encryption import PIIEncryption
from app.telemedicine.fhir import FHIRBundle, FHIRConverter


class PreTriageService:
    """Pre-triage 서비스"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.pii_encryption = PIIEncryption()
    
    async def create_from_case(
        self,
        case_id: uuid.UUID,
        ai_assessment: Optional[Dict[str, Any]] = None,
    ) -> Optional[PreTriage]:
        """케이스로부터 Pre-triage 생성
        
        Args:
            case_id: 케이스 ID
            ai_assessment: AI 분석 결과
            
        Returns:
            생성된 PreTriage 또는 None
        """
        # 케이스 조회
        result = await self.db.execute(
            select(CareCase).where(CareCase.id == case_id)
            .options(selectinload(CareCase.events))
        )
        case = result.scalar_one_or_none()
        
        if not case:
            return None
        
        # 사용자 조회
        user_result = await self.db.execute(
            select(CareUser).where(CareUser.id == case.user_id)
            .options(selectinload(CareUser.pii))
        )
        user = user_result.scalar_one_or_none()
        
        # 주호소 생성 (이벤트 기반)
        chief_complaint = self._build_chief_complaint(case)
        
        # 응급도 평가
        urgency = self._assess_urgency(case, ai_assessment)
        
        # 생체 징후 수집 (최근 데이터)
        vital_signs = await self._collect_vital_signs(case.user_id)
        
        # 증상 목록 생성
        symptoms = self._build_symptoms(case)
        
        # Pre-triage 생성
        pre_triage = PreTriage(
            id=uuid.uuid4(),
            care_user_id=case.user_id,
            case_id=case_id,
            urgency=urgency,
            status=TriageStatus.DRAFT,
            chief_complaint=chief_complaint,
            vital_signs=vital_signs,
            symptoms=symptoms,
            ai_assessment=ai_assessment,
        )
        
        self.db.add(pre_triage)
        await self.db.commit()
        await self.db.refresh(pre_triage)
        
        logger.info(
            f"Pre-triage created: id={pre_triage.id}, "
            f"case={case.case_number}, urgency={urgency.value}"
        )
        
        return pre_triage
    
    async def create_manual(
        self,
        care_user_id: uuid.UUID,
        chief_complaint: str,
        urgency: TriageUrgency = TriageUrgency.LEVEL_4,
        vital_signs: Optional[Dict[str, Any]] = None,
        symptoms: Optional[List[Dict[str, Any]]] = None,
        history_present_illness: Optional[str] = None,
        created_by_id: Optional[uuid.UUID] = None,
    ) -> PreTriage:
        """수동 Pre-triage 생성 (운영자)"""
        pre_triage = PreTriage(
            id=uuid.uuid4(),
            care_user_id=care_user_id,
            created_by_id=created_by_id,
            urgency=urgency,
            status=TriageStatus.DRAFT,
            chief_complaint=chief_complaint,
            history_present_illness=history_present_illness,
            vital_signs=vital_signs,
            symptoms=symptoms,
        )
        
        self.db.add(pre_triage)
        await self.db.commit()
        await self.db.refresh(pre_triage)
        
        return pre_triage
    
    async def get_by_id(self, triage_id: uuid.UUID) -> Optional[PreTriage]:
        """Pre-triage 조회"""
        result = await self.db.execute(
            select(PreTriage).where(
                PreTriage.id == triage_id,
                PreTriage.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_care_user(
        self,
        care_user_id: uuid.UUID,
        limit: int = 20,
    ) -> List[PreTriage]:
        """사용자별 Pre-triage 목록 조회"""
        result = await self.db.execute(
            select(PreTriage).where(
                PreTriage.care_user_id == care_user_id,
                PreTriage.deleted_at.is_(None),
            ).order_by(PreTriage.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
    
    async def update_status(
        self,
        triage_id: uuid.UUID,
        status: TriageStatus,
    ) -> Optional[PreTriage]:
        """상태 업데이트"""
        pre_triage = await self.get_by_id(triage_id)
        if not pre_triage:
            return None
        
        pre_triage.status = status
        
        if status == TriageStatus.SENT:
            pre_triage.sent_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(pre_triage)
        
        return pre_triage
    
    async def to_fhir_bundle(
        self,
        triage_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        """FHIR Bundle로 변환
        
        Args:
            triage_id: Pre-triage ID
            
        Returns:
            FHIR Bundle (dict) 또는 None
        """
        pre_triage = await self.get_by_id(triage_id)
        if not pre_triage:
            return None
        
        # 사용자 정보 조회
        user_result = await self.db.execute(
            select(CareUser).where(CareUser.id == pre_triage.care_user_id)
            .options(selectinload(CareUser.pii))
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return None
        
        # PII 복호화 (의료기관 전송용)
        name = None
        birth_date = None
        phone = None
        address = None
        
        if user.pii:
            name = self.pii_encryption.decrypt(user.pii.name_encrypted)
            if user.pii.phone_encrypted:
                phone = self.pii_encryption.decrypt(user.pii.phone_encrypted)
            if user.pii.birth_date_encrypted:
                birth_date = self.pii_encryption.decrypt(user.pii.birth_date_encrypted)
            if user.pii.address_encrypted:
                address = self.pii_encryption.decrypt(user.pii.address_encrypted)
        
        # Patient 리소스 생성
        patient = FHIRConverter.create_patient_from_care_user(
            user_id=str(pre_triage.care_user_id),
            name=name,
            birth_date=birth_date,
            phone=phone,
            address=address,
        )
        
        # Observation 리소스 생성
        observations = []
        if pre_triage.vital_signs:
            observations = FHIRConverter.create_observations_from_vitals(
                patient_id=str(pre_triage.care_user_id),
                vital_signs=pre_triage.vital_signs,
                measured_at=pre_triage.vital_signs.get("measured_at"),
            )
        
        # Condition 리소스 생성
        conditions = []
        if pre_triage.symptoms:
            conditions = FHIRConverter.create_conditions_from_symptoms(
                patient_id=str(pre_triage.care_user_id),
                symptoms=pre_triage.symptoms,
            )
        
        # Bundle 생성
        bundle = FHIRConverter.create_pretriage_bundle(
            patient=patient,
            observations=observations,
            conditions=conditions,
        )
        
        # Bundle ID 저장
        pre_triage.fhir_bundle_id = bundle.id
        await self.db.commit()
        
        return bundle.to_dict()
    
    def _build_chief_complaint(self, case: CareCase) -> str:
        """주호소 생성"""
        complaints = []
        
        for event in case.events:
            event_type = event.event_type.value
            
            if event_type == "fall":
                complaints.append("낙상 발생")
            elif event_type == "emergency_button":
                complaints.append("응급 버튼 누름")
            elif event_type == "emergency_voice":
                complaints.append("음성으로 도움 요청")
            elif event_type == "inactivity":
                complaints.append("무활동 감지")
            elif event_type == "abnormal_vital":
                complaints.append("생체 징후 이상")
            elif event_type == "low_spo2":
                complaints.append("산소포화도 저하")
        
        return ", ".join(complaints) if complaints else "케이스 발생"
    
    def _assess_urgency(
        self,
        case: CareCase,
        ai_assessment: Optional[Dict[str, Any]],
    ) -> TriageUrgency:
        """응급도 평가 (KTAS 기반)"""
        # 케이스 심각도 기반
        severity = case.max_severity.value
        
        if severity == "emergency":
            return TriageUrgency.LEVEL_1
        elif severity == "critical":
            return TriageUrgency.LEVEL_2
        elif severity == "warning":
            return TriageUrgency.LEVEL_3
        
        # AI 평가 기반
        if ai_assessment:
            risk_level = ai_assessment.get("risk_level", "").lower()
            if risk_level == "emergency":
                return TriageUrgency.LEVEL_1
            elif risk_level == "high":
                return TriageUrgency.LEVEL_2
            elif risk_level == "medium":
                return TriageUrgency.LEVEL_3
        
        return TriageUrgency.LEVEL_4
    
    async def _collect_vital_signs(
        self,
        care_user_id: uuid.UUID,
    ) -> Optional[Dict[str, Any]]:
        """최근 생체 징후 수집"""
        # TODO: 실제로는 Measurement 테이블에서 조회
        # 지금은 예시 데이터 반환
        return {
            "spo2": 95,
            "heart_rate": 80,
            "body_temperature": 36.8,
            "measured_at": datetime.now(timezone.utc).isoformat() + "Z",
        }
    
    def _build_symptoms(self, case: CareCase) -> List[Dict[str, Any]]:
        """증상 목록 생성"""
        symptoms = []
        
        for event in case.events:
            event_type = event.event_type.value
            
            if event_type == "fall":
                symptoms.append({
                    "code": "W19",
                    "display": "상세불명의 넘어짐",
                    "severity": "moderate",
                })
            elif event_type == "low_spo2":
                symptoms.append({
                    "code": "R09.0",
                    "display": "질식",
                    "severity": "severe",
                })
            elif event_type == "abnormal_vital":
                symptoms.append({
                    "code": "R00.0",
                    "display": "빈맥, 상세불명",
                    "severity": "moderate",
                })
        
        return symptoms
