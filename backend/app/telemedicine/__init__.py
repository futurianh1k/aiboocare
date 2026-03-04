"""
원격진료 연계 모듈

- Pre-triage: 사전분류 생성 및 관리
- FHIR: HL7 FHIR R4 표준 리소스 변환
- Clinic API: 의료기관 연동
- EMR: 전자의무기록 연계

참고:
- FHIR R4: https://www.hl7.org/fhir/R4/
- KTAS: 한국형 응급환자 분류도구
"""

from app.telemedicine.fhir import FHIRConverter
from app.telemedicine.pretriage import PreTriageService

__all__ = [
    "PreTriageService",
    "FHIRConverter",
]
