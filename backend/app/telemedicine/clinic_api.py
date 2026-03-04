"""
의료기관 연동 API 서비스

외부 의료기관 시스템과의 연동을 담당합니다.

지원 연동:
- FHIR Server: HL7 FHIR R4 표준 API
- 병원 EMR: 개별 병원 EMR 연동
- 원격진료 플랫폼: 화상 진료 플랫폼 연동

참고:
- 의료기관별 인증 정보는 환경변수/Secret Manager로 관리
- 민감 데이터 전송 시 TLS 필수
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging import logger


class ClinicType(str, Enum):
    """의료기관 종류"""
    FHIR_SERVER = "fhir_server"
    HOSPITAL_EMR = "hospital_emr"
    TELEMEDICINE_PLATFORM = "telemedicine_platform"
    PHARMACY = "pharmacy"


@dataclass
class ClinicConnection:
    """의료기관 연결 정보"""
    id: str
    name: str
    type: ClinicType
    base_url: str
    auth_type: str  # basic, bearer, oauth2
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: bool = True


@dataclass
class ClinicAPIResponse:
    """API 응답"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ClinicAPIService:
    """의료기관 API 서비스"""
    
    # 등록된 의료기관 연결 정보 (실제로는 DB에서 로드)
    _connections: Dict[str, ClinicConnection] = {}
    
    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
    
    def register_connection(self, connection: ClinicConnection):
        """의료기관 연결 등록"""
        self._connections[connection.id] = connection
        logger.info(f"Clinic connection registered: {connection.id} ({connection.name})")
    
    def get_connection(self, clinic_id: str) -> Optional[ClinicConnection]:
        """의료기관 연결 정보 조회"""
        return self._connections.get(clinic_id)
    
    async def send_fhir_bundle(
        self,
        clinic_id: str,
        bundle: Dict[str, Any],
    ) -> ClinicAPIResponse:
        """FHIR Bundle 전송
        
        Args:
            clinic_id: 의료기관 ID
            bundle: FHIR Bundle (dict)
            
        Returns:
            API 응답
        """
        conn = self.get_connection(clinic_id)
        if not conn or not conn.is_active:
            return ClinicAPIResponse(
                success=False,
                status_code=404,
                error="의료기관 연결을 찾을 수 없습니다.",
            )
        
        try:
            headers = self._build_headers(conn)
            headers["Content-Type"] = "application/fhir+json"
            
            response = await self.http_client.post(
                f"{conn.base_url}/Bundle",
                json=bundle,
                headers=headers,
            )
            
            if response.status_code in [200, 201]:
                logger.info(
                    f"FHIR Bundle sent: clinic={clinic_id}, "
                    f"bundle_id={bundle.get('id')}"
                )
                return ClinicAPIResponse(
                    success=True,
                    status_code=response.status_code,
                    data=response.json() if response.text else None,
                )
            else:
                logger.warning(
                    f"FHIR Bundle send failed: clinic={clinic_id}, "
                    f"status={response.status_code}"
                )
                return ClinicAPIResponse(
                    success=False,
                    status_code=response.status_code,
                    error=response.text,
                )
        
        except Exception as e:
            logger.error(f"FHIR API error: {e}")
            return ClinicAPIResponse(
                success=False,
                status_code=500,
                error=str(e),
            )
    
    async def create_appointment(
        self,
        clinic_id: str,
        patient_id: str,
        scheduled_time: datetime,
        session_type: str = "video",
        pre_triage_id: Optional[str] = None,
    ) -> ClinicAPIResponse:
        """진료 예약 생성
        
        Args:
            clinic_id: 의료기관 ID
            patient_id: 환자 ID
            scheduled_time: 예약 시간
            session_type: 진료 종류 (video, phone, chat)
            pre_triage_id: Pre-triage ID
            
        Returns:
            API 응답
        """
        conn = self.get_connection(clinic_id)
        if not conn or not conn.is_active:
            return ClinicAPIResponse(
                success=False,
                status_code=404,
                error="의료기관 연결을 찾을 수 없습니다.",
            )
        
        try:
            headers = self._build_headers(conn)
            
            # FHIR Appointment 리소스
            appointment = {
                "resourceType": "Appointment",
                "id": str(uuid.uuid4()),
                "status": "booked",
                "serviceType": [{
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "448337001" if session_type == "video" else "185317003",
                        "display": "Telemedicine consultation" if session_type == "video" else "Telephone consultation",
                    }],
                }],
                "start": scheduled_time.isoformat(),
                "end": (scheduled_time.replace(minute=scheduled_time.minute + 30)).isoformat(),
                "participant": [{
                    "actor": {
                        "reference": f"Patient/{patient_id}",
                    },
                    "status": "accepted",
                }],
            }
            
            if pre_triage_id:
                appointment["supportingInformation"] = [{
                    "reference": f"DocumentReference/{pre_triage_id}",
                }]
            
            response = await self.http_client.post(
                f"{conn.base_url}/Appointment",
                json=appointment,
                headers=headers,
            )
            
            if response.status_code in [200, 201]:
                logger.info(
                    f"Appointment created: clinic={clinic_id}, "
                    f"patient={patient_id}, time={scheduled_time}"
                )
                return ClinicAPIResponse(
                    success=True,
                    status_code=response.status_code,
                    data=response.json() if response.text else None,
                )
            else:
                return ClinicAPIResponse(
                    success=False,
                    status_code=response.status_code,
                    error=response.text,
                )
        
        except Exception as e:
            logger.error(f"Appointment API error: {e}")
            return ClinicAPIResponse(
                success=False,
                status_code=500,
                error=str(e),
            )
    
    async def get_session_url(
        self,
        clinic_id: str,
        appointment_id: str,
    ) -> ClinicAPIResponse:
        """화상 진료 세션 URL 조회
        
        Args:
            clinic_id: 의료기관 ID
            appointment_id: 예약 ID
            
        Returns:
            세션 URL 포함 응답
        """
        conn = self.get_connection(clinic_id)
        if not conn or not conn.is_active:
            return ClinicAPIResponse(
                success=False,
                status_code=404,
                error="의료기관 연결을 찾을 수 없습니다.",
            )
        
        try:
            headers = self._build_headers(conn)
            
            # 원격진료 플랫폼 API 호출
            response = await self.http_client.get(
                f"{conn.base_url}/session/{appointment_id}",
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                return ClinicAPIResponse(
                    success=True,
                    status_code=200,
                    data={
                        "session_url": data.get("url"),
                        "expires_at": data.get("expires_at"),
                    },
                )
            else:
                return ClinicAPIResponse(
                    success=False,
                    status_code=response.status_code,
                    error=response.text,
                )
        
        except Exception as e:
            logger.error(f"Session URL API error: {e}")
            return ClinicAPIResponse(
                success=False,
                status_code=500,
                error=str(e),
            )
    
    async def check_clinic_availability(
        self,
        clinic_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> ClinicAPIResponse:
        """의료기관 예약 가능 여부 확인"""
        conn = self.get_connection(clinic_id)
        if not conn or not conn.is_active:
            return ClinicAPIResponse(
                success=False,
                status_code=404,
                error="의료기관 연결을 찾을 수 없습니다.",
            )
        
        try:
            headers = self._build_headers(conn)
            
            # Slot 검색 (FHIR)
            params = {
                "start": f"ge{start_time.isoformat()}",
                "end": f"le{end_time.isoformat()}",
                "status": "free",
            }
            
            response = await self.http_client.get(
                f"{conn.base_url}/Slot",
                params=params,
                headers=headers,
            )
            
            if response.status_code == 200:
                data = response.json()
                slots = data.get("entry", [])
                return ClinicAPIResponse(
                    success=True,
                    status_code=200,
                    data={
                        "available": len(slots) > 0,
                        "slots": slots,
                    },
                )
            else:
                return ClinicAPIResponse(
                    success=False,
                    status_code=response.status_code,
                    error=response.text,
                )
        
        except Exception as e:
            logger.error(f"Availability check error: {e}")
            return ClinicAPIResponse(
                success=False,
                status_code=500,
                error=str(e),
            )
    
    def _build_headers(self, conn: ClinicConnection) -> Dict[str, str]:
        """인증 헤더 생성"""
        headers = {
            "Accept": "application/fhir+json",
        }
        
        if conn.auth_type == "bearer" and conn.api_key:
            headers["Authorization"] = f"Bearer {conn.api_key}"
        elif conn.auth_type == "basic" and conn.username and conn.password:
            import base64
            credentials = base64.b64encode(
                f"{conn.username}:{conn.password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        return headers


# 전역 인스턴스
_clinic_api_service: Optional[ClinicAPIService] = None


def get_clinic_api_service() -> ClinicAPIService:
    """의료기관 API 서비스 인스턴스 반환"""
    global _clinic_api_service
    if _clinic_api_service is None:
        _clinic_api_service = ClinicAPIService()
    return _clinic_api_service
