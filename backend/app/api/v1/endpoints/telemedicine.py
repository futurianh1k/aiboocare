"""
원격진료 연계 API 엔드포인트

- Pre-triage 생성/조회/전송
- 원격진료 예약
- FHIR Bundle 변환
- 의료기관 연동

보안 규칙:
- Pre-triage 전송 시 PII 복호화 후 전송
- 의료기관 인증 정보는 환경변수로 관리
- 전송 로그 감사 기록
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_roles
from app.core.logging import audit_logger, logger
from app.models.telemedicine import TriageStatus, TriageUrgency
from app.models.user import UserRole
from app.telemedicine.clinic_api import ClinicAPIService, ClinicConnection, ClinicType, get_clinic_api_service
from app.telemedicine.pretriage import PreTriageService

router = APIRouter()


# ============== 요청/응답 스키마 ==============

class PreTriageCreateRequest(BaseModel):
    """Pre-triage 생성 요청"""
    care_user_id: uuid.UUID
    chief_complaint: str = Field(..., min_length=1, max_length=1000)
    urgency: str = Field("level_4", description="응급도 (level_1~5)")
    vital_signs: Optional[Dict[str, Any]] = None
    symptoms: Optional[List[Dict[str, Any]]] = None
    history_present_illness: Optional[str] = None


class PreTriageResponse(BaseModel):
    """Pre-triage 응답"""
    id: uuid.UUID
    care_user_id: uuid.UUID
    case_id: Optional[uuid.UUID]
    urgency: str
    status: str
    chief_complaint: str
    vital_signs: Optional[Dict[str, Any]]
    symptoms: Optional[List[Dict[str, Any]]]
    ai_assessment: Optional[Dict[str, Any]]
    created_at: datetime
    sent_at: Optional[datetime]
    fhir_bundle_id: Optional[str]


class PreTriageSendRequest(BaseModel):
    """Pre-triage 전송 요청"""
    clinic_id: str = Field(..., description="의료기관 ID")


class TelemedicineSessionRequest(BaseModel):
    """원격진료 세션 예약 요청"""
    clinic_id: str
    scheduled_at: datetime
    session_type: str = Field("video", pattern="^(video|phone|chat)$")
    pre_triage_id: Optional[uuid.UUID] = None


class TelemedicineSessionResponse(BaseModel):
    """원격진료 세션 응답"""
    id: uuid.UUID
    care_user_id: uuid.UUID
    clinic_id: str
    clinic_name: str
    status: str
    session_type: str
    scheduled_at: datetime
    session_url: Optional[str]


class ClinicConnectionRequest(BaseModel):
    """의료기관 연결 등록 요청"""
    id: str
    name: str
    type: str = Field(..., description="fhir_server, hospital_emr, telemedicine_platform")
    base_url: str
    auth_type: str = Field("bearer", description="basic, bearer, oauth2")
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


# ============== Pre-triage API ==============

@router.post("/pre-triage", response_model=PreTriageResponse)
async def create_pretriage(
    request: PreTriageCreateRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """Pre-triage 수동 생성 (운영자)"""
    try:
        urgency = TriageUrgency(request.urgency)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 응급도: {request.urgency}",
        )
    
    service = PreTriageService(db)
    
    pre_triage = await service.create_manual(
        care_user_id=request.care_user_id,
        chief_complaint=request.chief_complaint,
        urgency=urgency,
        vital_signs=request.vital_signs,
        symptoms=request.symptoms,
        history_present_illness=request.history_present_illness,
        created_by_id=uuid.UUID(current_user["sub"]),
    )
    
    audit_logger.log_action(
        user_id=current_user["sub"],
        action="create_pretriage",
        resource_type="pre_triage",
        resource_id=str(pre_triage.id),
    )
    
    return PreTriageResponse(
        id=pre_triage.id,
        care_user_id=pre_triage.care_user_id,
        case_id=pre_triage.case_id,
        urgency=pre_triage.urgency.value,
        status=pre_triage.status.value,
        chief_complaint=pre_triage.chief_complaint,
        vital_signs=pre_triage.vital_signs,
        symptoms=pre_triage.symptoms,
        ai_assessment=pre_triage.ai_assessment,
        created_at=pre_triage.created_at,
        sent_at=pre_triage.sent_at,
        fhir_bundle_id=pre_triage.fhir_bundle_id,
    )


@router.post("/pre-triage/from-case/{case_id}", response_model=PreTriageResponse)
async def create_pretriage_from_case(
    case_id: uuid.UUID,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """케이스로부터 Pre-triage 자동 생성"""
    service = PreTriageService(db)
    
    pre_triage = await service.create_from_case(case_id)
    
    if not pre_triage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="케이스를 찾을 수 없습니다.",
        )
    
    return PreTriageResponse(
        id=pre_triage.id,
        care_user_id=pre_triage.care_user_id,
        case_id=pre_triage.case_id,
        urgency=pre_triage.urgency.value,
        status=pre_triage.status.value,
        chief_complaint=pre_triage.chief_complaint,
        vital_signs=pre_triage.vital_signs,
        symptoms=pre_triage.symptoms,
        ai_assessment=pre_triage.ai_assessment,
        created_at=pre_triage.created_at,
        sent_at=pre_triage.sent_at,
        fhir_bundle_id=pre_triage.fhir_bundle_id,
    )


@router.get("/pre-triage/{triage_id}", response_model=PreTriageResponse)
async def get_pretriage(
    triage_id: uuid.UUID,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """Pre-triage 조회"""
    service = PreTriageService(db)
    
    pre_triage = await service.get_by_id(triage_id)
    
    if not pre_triage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pre-triage를 찾을 수 없습니다.",
        )
    
    return PreTriageResponse(
        id=pre_triage.id,
        care_user_id=pre_triage.care_user_id,
        case_id=pre_triage.case_id,
        urgency=pre_triage.urgency.value,
        status=pre_triage.status.value,
        chief_complaint=pre_triage.chief_complaint,
        vital_signs=pre_triage.vital_signs,
        symptoms=pre_triage.symptoms,
        ai_assessment=pre_triage.ai_assessment,
        created_at=pre_triage.created_at,
        sent_at=pre_triage.sent_at,
        fhir_bundle_id=pre_triage.fhir_bundle_id,
    )


@router.get("/pre-triage/user/{care_user_id}", response_model=List[PreTriageResponse])
async def list_pretriage_by_user(
    care_user_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """사용자별 Pre-triage 목록 조회"""
    service = PreTriageService(db)
    
    triages = await service.get_by_care_user(care_user_id, limit)
    
    return [
        PreTriageResponse(
            id=t.id,
            care_user_id=t.care_user_id,
            case_id=t.case_id,
            urgency=t.urgency.value,
            status=t.status.value,
            chief_complaint=t.chief_complaint,
            vital_signs=t.vital_signs,
            symptoms=t.symptoms,
            ai_assessment=t.ai_assessment,
            created_at=t.created_at,
            sent_at=t.sent_at,
            fhir_bundle_id=t.fhir_bundle_id,
        )
        for t in triages
    ]


# ============== FHIR API ==============

@router.get("/pre-triage/{triage_id}/fhir")
async def get_pretriage_fhir_bundle(
    triage_id: uuid.UUID,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """Pre-triage를 FHIR Bundle로 변환"""
    service = PreTriageService(db)
    
    bundle = await service.to_fhir_bundle(triage_id)
    
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pre-triage를 찾을 수 없습니다.",
        )
    
    return bundle


@router.post("/pre-triage/{triage_id}/send")
async def send_pretriage_to_clinic(
    triage_id: uuid.UUID,
    request: PreTriageSendRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """Pre-triage를 의료기관에 전송"""
    service = PreTriageService(db)
    
    # FHIR Bundle 생성
    bundle = await service.to_fhir_bundle(triage_id)
    
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pre-triage를 찾을 수 없습니다.",
        )
    
    # 의료기관에 전송
    clinic_service = get_clinic_api_service()
    response = await clinic_service.send_fhir_bundle(request.clinic_id, bundle)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"의료기관 전송 실패: {response.error}",
        )
    
    # 상태 업데이트
    pre_triage = await service.update_status(triage_id, TriageStatus.SENT)
    if pre_triage:
        pre_triage.sent_to_clinic_id = request.clinic_id
        await db.commit()
    
    audit_logger.log_action(
        user_id=current_user["sub"],
        action="send_pretriage",
        resource_type="pre_triage",
        resource_id=str(triage_id),
        details={"clinic_id": request.clinic_id},
    )
    
    return {
        "success": True,
        "triage_id": str(triage_id),
        "clinic_id": request.clinic_id,
        "fhir_bundle_id": bundle.get("id"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


# ============== 의료기관 연동 API ==============

@router.post("/clinics/register")
async def register_clinic_connection(
    request: ClinicConnectionRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN])),
):
    """의료기관 연결 등록 (관리자)"""
    try:
        clinic_type = ClinicType(request.type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 의료기관 종류: {request.type}",
        )
    
    connection = ClinicConnection(
        id=request.id,
        name=request.name,
        type=clinic_type,
        base_url=request.base_url,
        auth_type=request.auth_type,
        api_key=request.api_key,
        username=request.username,
        password=request.password,
    )
    
    service = get_clinic_api_service()
    service.register_connection(connection)
    
    audit_logger.log_action(
        user_id=current_user["sub"],
        action="register_clinic",
        resource_type="clinic",
        resource_id=request.id,
    )
    
    return {
        "success": True,
        "clinic_id": request.id,
        "name": request.name,
        "type": request.type,
    }


@router.post("/clinics/{clinic_id}/check-availability")
async def check_clinic_availability(
    clinic_id: str,
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
):
    """의료기관 예약 가능 여부 확인"""
    service = get_clinic_api_service()
    
    response = await service.check_clinic_availability(
        clinic_id=clinic_id,
        start_time=start_time,
        end_time=end_time,
    )
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"가용성 확인 실패: {response.error}",
        )
    
    return response.data


@router.post("/appointments")
async def create_telemedicine_appointment(
    request: TelemedicineSessionRequest,
    current_user: dict = Depends(require_roles([UserRole.ADMIN, UserRole.OPERATOR])),
    db: AsyncSession = Depends(get_db),
):
    """원격진료 예약 생성"""
    # Pre-triage에서 환자 ID 추출
    patient_id = None
    if request.pre_triage_id:
        service = PreTriageService(db)
        pre_triage = await service.get_by_id(request.pre_triage_id)
        if pre_triage:
            patient_id = str(pre_triage.care_user_id)
    
    if not patient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="환자 정보를 확인할 수 없습니다.",
        )
    
    # 의료기관에 예약 생성
    clinic_service = get_clinic_api_service()
    response = await clinic_service.create_appointment(
        clinic_id=request.clinic_id,
        patient_id=patient_id,
        scheduled_time=request.scheduled_at,
        session_type=request.session_type,
        pre_triage_id=str(request.pre_triage_id) if request.pre_triage_id else None,
    )
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"예약 생성 실패: {response.error}",
        )
    
    audit_logger.log_action(
        user_id=current_user["sub"],
        action="create_appointment",
        resource_type="appointment",
        resource_id=response.data.get("id") if response.data else "",
        details={"clinic_id": request.clinic_id, "scheduled_at": request.scheduled_at.isoformat()},
    )
    
    return {
        "success": True,
        "appointment": response.data,
    }


# ============== 문서 API ==============

@router.get("/fhir/resources")
async def get_fhir_resource_docs():
    """FHIR 리소스 문서
    
    지원하는 FHIR R4 리소스 목록을 반환합니다.
    """
    return {
        "fhir_version": "R4",
        "supported_resources": {
            "Patient": {
                "description": "환자 정보",
                "profile": "http://hl7.org/fhir/StructureDefinition/Patient",
            },
            "Observation": {
                "description": "생체 징후, 측정값",
                "profile": "http://hl7.org/fhir/StructureDefinition/Observation",
                "supported_types": [
                    {"code": "59408-5", "display": "SpO2"},
                    {"code": "8867-4", "display": "Heart rate"},
                    {"code": "8310-5", "display": "Body temperature"},
                    {"code": "9279-1", "display": "Respiratory rate"},
                    {"code": "8480-6", "display": "Systolic BP"},
                    {"code": "8462-4", "display": "Diastolic BP"},
                ],
            },
            "Condition": {
                "description": "진단, 증상, 상태",
                "profile": "http://hl7.org/fhir/StructureDefinition/Condition",
            },
            "Appointment": {
                "description": "진료 예약",
                "profile": "http://hl7.org/fhir/StructureDefinition/Appointment",
            },
            "Bundle": {
                "description": "리소스 묶음",
                "profile": "http://hl7.org/fhir/StructureDefinition/Bundle",
                "supported_types": ["collection", "transaction"],
            },
        },
        "terminology": {
            "icd10": "http://hl7.org/fhir/sid/icd-10",
            "loinc": "http://loinc.org",
            "snomed": "http://snomed.info/sct",
        },
    }


@router.get("/urgency-levels")
async def get_urgency_levels():
    """응급도 분류 기준 (KTAS)"""
    return {
        "system": "KTAS (Korean Triage and Acuity Scale)",
        "levels": {
            "level_1": {
                "name": "소생",
                "description": "즉각적인 소생술이 필요한 상태",
                "response_time": "즉시",
                "color": "blue",
                "examples": ["심정지", "심한 호흡곤란", "의식없음"],
            },
            "level_2": {
                "name": "응급",
                "description": "생명이나 사지를 위협하는 상태",
                "response_time": "10분 이내",
                "color": "red",
                "examples": ["중증 흉통", "뇌졸중 증상", "중증 외상"],
            },
            "level_3": {
                "name": "긴급",
                "description": "잠재적으로 생명을 위협할 수 있는 상태",
                "response_time": "30분 이내",
                "color": "yellow",
                "examples": ["경도 호흡곤란", "복통", "고열"],
            },
            "level_4": {
                "name": "준긴급",
                "description": "1-2시간 내에 치료가 필요한 상태",
                "response_time": "60분 이내",
                "color": "green",
                "examples": ["경미한 외상", "단순 요통", "감기 증상"],
            },
            "level_5": {
                "name": "비긴급",
                "description": "급성 상태가 아닌 경우",
                "response_time": "120분 이내",
                "color": "white",
                "examples": ["만성 질환 관리", "처방전 재발급", "건강 상담"],
            },
        },
    }
