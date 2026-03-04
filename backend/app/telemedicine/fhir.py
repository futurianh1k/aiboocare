"""
FHIR (Fast Healthcare Interoperability Resources) 리소스 변환

HL7 FHIR R4 표준에 따라 데이터를 변환합니다.

지원 리소스:
- Patient: 환자 정보
- Observation: 생체 징후, 측정값
- Condition: 진단, 증상
- Encounter: 진료 기록
- Bundle: 리소스 묶음

참고: https://www.hl7.org/fhir/R4/
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.logging import logger


class FHIRResource:
    """FHIR 리소스 기본 클래스"""
    
    resource_type: str = "Resource"
    
    def __init__(self, resource_id: Optional[str] = None):
        self.id = resource_id or str(uuid.uuid4())
        self.meta = {
            "versionId": "1",
            "lastUpdated": datetime.utcnow().isoformat() + "Z",
        }
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resourceType": self.resource_type,
            "id": self.id,
            "meta": self.meta,
        }


class FHIRPatient(FHIRResource):
    """FHIR Patient 리소스
    
    환자의 인구통계학적 정보를 담습니다.
    """
    
    resource_type = "Patient"
    
    def __init__(
        self,
        resource_id: Optional[str] = None,
        identifier: Optional[str] = None,
        name: Optional[str] = None,
        birth_date: Optional[str] = None,
        gender: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
    ):
        super().__init__(resource_id)
        self.identifier = identifier
        self.name = name
        self.birth_date = birth_date
        self.gender = gender
        self.phone = phone
        self.address = address
    
    def to_dict(self) -> Dict[str, Any]:
        resource = super().to_dict()
        
        if self.identifier:
            resource["identifier"] = [{
                "system": "urn:oid:aiboocare",
                "value": self.identifier,
            }]
        
        if self.name:
            resource["name"] = [{
                "use": "official",
                "text": self.name,
            }]
        
        if self.birth_date:
            resource["birthDate"] = self.birth_date
        
        if self.gender:
            resource["gender"] = self.gender
        
        if self.phone:
            resource["telecom"] = [{
                "system": "phone",
                "value": self.phone,
                "use": "mobile",
            }]
        
        if self.address:
            resource["address"] = [{
                "use": "home",
                "text": self.address,
            }]
        
        return resource


class FHIRObservation(FHIRResource):
    """FHIR Observation 리소스
    
    생체 징후, 측정값 등을 담습니다.
    """
    
    resource_type = "Observation"
    
    # LOINC 코드 매핑
    LOINC_CODES = {
        "spo2": {"code": "59408-5", "display": "Oxygen saturation in Arterial blood by Pulse oximetry"},
        "heart_rate": {"code": "8867-4", "display": "Heart rate"},
        "respiratory_rate": {"code": "9279-1", "display": "Respiratory rate"},
        "body_temperature": {"code": "8310-5", "display": "Body temperature"},
        "blood_pressure_systolic": {"code": "8480-6", "display": "Systolic blood pressure"},
        "blood_pressure_diastolic": {"code": "8462-4", "display": "Diastolic blood pressure"},
    }
    
    # 단위 매핑
    UNITS = {
        "spo2": "%",
        "heart_rate": "/min",
        "respiratory_rate": "/min",
        "body_temperature": "Cel",
        "blood_pressure_systolic": "mm[Hg]",
        "blood_pressure_diastolic": "mm[Hg]",
    }
    
    def __init__(
        self,
        resource_id: Optional[str] = None,
        patient_reference: Optional[str] = None,
        observation_type: str = "",
        value: Optional[float] = None,
        effective_datetime: Optional[str] = None,
        status: str = "final",
    ):
        super().__init__(resource_id)
        self.patient_reference = patient_reference
        self.observation_type = observation_type
        self.value = value
        self.effective_datetime = effective_datetime or datetime.utcnow().isoformat() + "Z"
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        resource = super().to_dict()
        
        resource["status"] = self.status
        
        # 코드 설정
        loinc = self.LOINC_CODES.get(self.observation_type, {})
        resource["code"] = {
            "coding": [{
                "system": "http://loinc.org",
                "code": loinc.get("code", ""),
                "display": loinc.get("display", self.observation_type),
            }],
        }
        
        # 환자 참조
        if self.patient_reference:
            resource["subject"] = {
                "reference": f"Patient/{self.patient_reference}",
            }
        
        # 측정 시간
        resource["effectiveDateTime"] = self.effective_datetime
        
        # 값
        if self.value is not None:
            unit = self.UNITS.get(self.observation_type, "")
            resource["valueQuantity"] = {
                "value": self.value,
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": unit,
            }
        
        return resource


class FHIRCondition(FHIRResource):
    """FHIR Condition 리소스
    
    진단, 증상, 상태를 담습니다.
    """
    
    resource_type = "Condition"
    
    def __init__(
        self,
        resource_id: Optional[str] = None,
        patient_reference: Optional[str] = None,
        code: Optional[str] = None,
        display: Optional[str] = None,
        clinical_status: str = "active",
        severity: Optional[str] = None,
        onset_datetime: Optional[str] = None,
    ):
        super().__init__(resource_id)
        self.patient_reference = patient_reference
        self.code = code
        self.display = display
        self.clinical_status = clinical_status
        self.severity = severity
        self.onset_datetime = onset_datetime
    
    def to_dict(self) -> Dict[str, Any]:
        resource = super().to_dict()
        
        # 임상 상태
        resource["clinicalStatus"] = {
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                "code": self.clinical_status,
            }],
        }
        
        # 코드 (ICD-10)
        resource["code"] = {
            "coding": [{
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": self.code or "",
                "display": self.display or "",
            }],
            "text": self.display or "",
        }
        
        # 환자 참조
        if self.patient_reference:
            resource["subject"] = {
                "reference": f"Patient/{self.patient_reference}",
            }
        
        # 심각도
        if self.severity:
            severity_map = {
                "mild": {"code": "255604002", "display": "Mild"},
                "moderate": {"code": "6736007", "display": "Moderate"},
                "severe": {"code": "24484000", "display": "Severe"},
            }
            sev = severity_map.get(self.severity.lower(), {})
            if sev:
                resource["severity"] = {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": sev["code"],
                        "display": sev["display"],
                    }],
                }
        
        # 발생 시간
        if self.onset_datetime:
            resource["onsetDateTime"] = self.onset_datetime
        
        return resource


class FHIRBundle(FHIRResource):
    """FHIR Bundle 리소스
    
    여러 리소스를 묶어서 전송합니다.
    """
    
    resource_type = "Bundle"
    
    def __init__(
        self,
        resource_id: Optional[str] = None,
        bundle_type: str = "collection",
    ):
        super().__init__(resource_id)
        self.bundle_type = bundle_type
        self.entries: List[FHIRResource] = []
    
    def add_entry(self, resource: FHIRResource):
        """리소스 추가"""
        self.entries.append(resource)
    
    def to_dict(self) -> Dict[str, Any]:
        resource = super().to_dict()
        
        resource["type"] = self.bundle_type
        resource["timestamp"] = datetime.utcnow().isoformat() + "Z"
        resource["entry"] = [
            {
                "fullUrl": f"urn:uuid:{entry.id}",
                "resource": entry.to_dict(),
            }
            for entry in self.entries
        ]
        
        return resource


class FHIRConverter:
    """FHIR 리소스 변환기"""
    
    @staticmethod
    def create_patient_from_care_user(
        user_id: str,
        name: Optional[str] = None,
        birth_date: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
    ) -> FHIRPatient:
        """CareUser를 FHIR Patient로 변환"""
        return FHIRPatient(
            resource_id=user_id,
            identifier=user_id,
            name=name,
            birth_date=birth_date,
            phone=phone,
            address=address,
        )
    
    @staticmethod
    def create_observations_from_vitals(
        patient_id: str,
        vital_signs: Dict[str, Any],
        measured_at: Optional[str] = None,
    ) -> List[FHIRObservation]:
        """생체 징후를 FHIR Observation 목록으로 변환"""
        observations = []
        
        # SpO2
        if "spo2" in vital_signs:
            observations.append(FHIRObservation(
                patient_reference=patient_id,
                observation_type="spo2",
                value=vital_signs["spo2"],
                effective_datetime=measured_at,
            ))
        
        # 심박수
        if "heart_rate" in vital_signs:
            observations.append(FHIRObservation(
                patient_reference=patient_id,
                observation_type="heart_rate",
                value=vital_signs["heart_rate"],
                effective_datetime=measured_at,
            ))
        
        # 체온
        if "body_temperature" in vital_signs or "body_temp" in vital_signs:
            temp = vital_signs.get("body_temperature") or vital_signs.get("body_temp")
            observations.append(FHIRObservation(
                patient_reference=patient_id,
                observation_type="body_temperature",
                value=temp,
                effective_datetime=measured_at,
            ))
        
        # 호흡수
        if "respiratory_rate" in vital_signs:
            observations.append(FHIRObservation(
                patient_reference=patient_id,
                observation_type="respiratory_rate",
                value=vital_signs["respiratory_rate"],
                effective_datetime=measured_at,
            ))
        
        # 혈압
        if "blood_pressure" in vital_signs:
            bp = vital_signs["blood_pressure"]
            if isinstance(bp, dict):
                if "systolic" in bp:
                    observations.append(FHIRObservation(
                        patient_reference=patient_id,
                        observation_type="blood_pressure_systolic",
                        value=bp["systolic"],
                        effective_datetime=measured_at,
                    ))
                if "diastolic" in bp:
                    observations.append(FHIRObservation(
                        patient_reference=patient_id,
                        observation_type="blood_pressure_diastolic",
                        value=bp["diastolic"],
                        effective_datetime=measured_at,
                    ))
        
        return observations
    
    @staticmethod
    def create_conditions_from_symptoms(
        patient_id: str,
        symptoms: List[Dict[str, Any]],
    ) -> List[FHIRCondition]:
        """증상을 FHIR Condition 목록으로 변환"""
        conditions = []
        
        for symptom in symptoms:
            conditions.append(FHIRCondition(
                patient_reference=patient_id,
                code=symptom.get("code"),
                display=symptom.get("display"),
                severity=symptom.get("severity"),
                onset_datetime=symptom.get("onset"),
            ))
        
        return conditions
    
    @staticmethod
    def create_pretriage_bundle(
        patient: FHIRPatient,
        observations: List[FHIRObservation],
        conditions: List[FHIRCondition],
    ) -> FHIRBundle:
        """Pre-triage Bundle 생성"""
        bundle = FHIRBundle(bundle_type="collection")
        
        # Patient 추가
        bundle.add_entry(patient)
        
        # Observations 추가
        for obs in observations:
            bundle.add_entry(obs)
        
        # Conditions 추가
        for cond in conditions:
            bundle.add_entry(cond)
        
        return bundle
