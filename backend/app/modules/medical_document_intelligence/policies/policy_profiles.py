from enum import Enum

from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)


class PolicyProfile(str, Enum):
    MEDNEXUS_DEFAULT = "mednexus_default"
    RESEARCH = "research"
    STRICT_PRIVACY = "strict_privacy"


POLICY_RULES = {
    PolicyProfile.MEDNEXUS_DEFAULT: {
        MedicalContextEntity.PATIENT_NAME: PolicyAction.REPLACE,
        MedicalContextEntity.CIVIL_ID: PolicyAction.HASH,
        MedicalContextEntity.MRN: PolicyAction.HASH,
        MedicalContextEntity.VISIT_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.LAB_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.ACCESSION_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.SPECIMEN_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.PHONE_NUMBER: PolicyAction.MASK,
        MedicalContextEntity.EMAIL: PolicyAction.MASK,
        MedicalContextEntity.ADDRESS: PolicyAction.GENERALIZE,
        MedicalContextEntity.DATE_OF_BIRTH: PolicyAction.GENERALIZE,
        MedicalContextEntity.ADMISSION_DATE: PolicyAction.SHIFT_DATE,
        MedicalContextEntity.DISCHARGE_DATE: PolicyAction.SHIFT_DATE,
        MedicalContextEntity.PHYSICIAN_NAME: PolicyAction.KEEP,
        MedicalContextEntity.HOSPITAL: PolicyAction.KEEP,
        MedicalContextEntity.UNKNOWN_PII: PolicyAction.MASK,
    },

    PolicyProfile.RESEARCH: {
        MedicalContextEntity.PATIENT_NAME: PolicyAction.REPLACE,
        MedicalContextEntity.CIVIL_ID: PolicyAction.HASH,
        MedicalContextEntity.MRN: PolicyAction.HASH,
        MedicalContextEntity.VISIT_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.LAB_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.ACCESSION_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.SPECIMEN_NUMBER: PolicyAction.HASH,
        MedicalContextEntity.PHONE_NUMBER: PolicyAction.REMOVE,
        MedicalContextEntity.EMAIL: PolicyAction.REMOVE,
        MedicalContextEntity.ADDRESS: PolicyAction.GENERALIZE,
        MedicalContextEntity.DATE_OF_BIRTH: PolicyAction.GENERALIZE,
        MedicalContextEntity.ADMISSION_DATE: PolicyAction.SHIFT_DATE,
        MedicalContextEntity.DISCHARGE_DATE: PolicyAction.SHIFT_DATE,
        MedicalContextEntity.PHYSICIAN_NAME: PolicyAction.KEEP,
        MedicalContextEntity.HOSPITAL: PolicyAction.KEEP,
        MedicalContextEntity.UNKNOWN_PII: PolicyAction.REMOVE,
    },

    PolicyProfile.STRICT_PRIVACY: {
        MedicalContextEntity.PATIENT_NAME: PolicyAction.REMOVE,
        MedicalContextEntity.PHYSICIAN_NAME: PolicyAction.REMOVE,
        MedicalContextEntity.CIVIL_ID: PolicyAction.REMOVE,
        MedicalContextEntity.MRN: PolicyAction.REMOVE,
        MedicalContextEntity.VISIT_NUMBER: PolicyAction.REMOVE,
        MedicalContextEntity.LAB_NUMBER: PolicyAction.REMOVE,
        MedicalContextEntity.ACCESSION_NUMBER: PolicyAction.REMOVE,
        MedicalContextEntity.SPECIMEN_NUMBER: PolicyAction.REMOVE,
        MedicalContextEntity.PHONE_NUMBER: PolicyAction.REMOVE,
        MedicalContextEntity.EMAIL: PolicyAction.REMOVE,
        MedicalContextEntity.ADDRESS: PolicyAction.REMOVE,
        MedicalContextEntity.DATE_OF_BIRTH: PolicyAction.GENERALIZE,
        MedicalContextEntity.ADMISSION_DATE: PolicyAction.SHIFT_DATE,
        MedicalContextEntity.DISCHARGE_DATE: PolicyAction.SHIFT_DATE,
        MedicalContextEntity.HOSPITAL: PolicyAction.GENERALIZE,
        MedicalContextEntity.UNKNOWN_PII: PolicyAction.REMOVE,
    },
}