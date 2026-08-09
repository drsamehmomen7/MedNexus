from enum import Enum


class MedicalContextEntity(str, Enum):
    """
    Healthcare-aware entity types used by MedNexus
    before applying de-identification policies.
    """

    PATIENT_NAME = "patient_name"
    PHYSICIAN_NAME = "physician_name"

    CIVIL_ID = "civil_id"
    MRN = "mrn"
    VISIT_NUMBER = "visit_number"
    LAB_NUMBER = "lab_number"
    ACCESSION_NUMBER = "accession_number"
    SPECIMEN_NUMBER = "specimen_number"
    INSURANCE_NUMBER = "insurance_number"
    DOCUMENT_ID = "document_id"

    DATE_OF_BIRTH = "date_of_birth"
    ADMISSION_DATE = "admission_date"
    DISCHARGE_DATE = "discharge_date"
    EXAM_DATE = "exam_date"
    COLLECTION_DATE = "collection_date"

    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    ADDRESS = "address"
    EMERGENCY_CONTACT = "emergency_contact"

    HOSPITAL = "hospital"
    DEPARTMENT = "department"
    WARD = "ward"
    ROOM = "room"
    BED = "bed"

    NATIONALITY = "nationality"
    GENDER = "gender"
    AGE = "age"

    UNKNOWN_PII = "unknown_pii"

class IdentityCategory(str, Enum):
    """
    High-level identity categories used by MedNexus
    to apply context-aware de-identification policies.
    """

    PATIENT_IDENTITY = "patient_identity"
    PROVIDER_IDENTITY = "provider_identity"
    INSTITUTION_IDENTITY = "institution_identity"
    OPERATIONAL_IDENTITY = "operational_identity"
    DEMOGRAPHIC_IDENTITY = "demographic_identity"
    CONTACT_IDENTITY = "contact_identity"
    TEMPORAL_IDENTITY = "temporal_identity"
    UNKNOWN_IDENTITY = "unknown_identity"
ENTITY_CATEGORY_MAP = {
    MedicalContextEntity.PATIENT_NAME: IdentityCategory.PATIENT_IDENTITY,
    MedicalContextEntity.PHYSICIAN_NAME: IdentityCategory.PROVIDER_IDENTITY,

    MedicalContextEntity.CIVIL_ID: IdentityCategory.PATIENT_IDENTITY,
    MedicalContextEntity.MRN: IdentityCategory.PATIENT_IDENTITY,

    MedicalContextEntity.VISIT_NUMBER: IdentityCategory.OPERATIONAL_IDENTITY,
    MedicalContextEntity.LAB_NUMBER: IdentityCategory.OPERATIONAL_IDENTITY,
    MedicalContextEntity.ACCESSION_NUMBER: IdentityCategory.OPERATIONAL_IDENTITY,
    MedicalContextEntity.SPECIMEN_NUMBER: IdentityCategory.OPERATIONAL_IDENTITY,
    MedicalContextEntity.DOCUMENT_ID: IdentityCategory.OPERATIONAL_IDENTITY,

    MedicalContextEntity.HOSPITAL: IdentityCategory.INSTITUTION_IDENTITY,
    MedicalContextEntity.DEPARTMENT: IdentityCategory.INSTITUTION_IDENTITY,
    MedicalContextEntity.WARD: IdentityCategory.INSTITUTION_IDENTITY,
    MedicalContextEntity.ROOM: IdentityCategory.INSTITUTION_IDENTITY,
    MedicalContextEntity.BED: IdentityCategory.INSTITUTION_IDENTITY,

    MedicalContextEntity.PHONE_NUMBER: IdentityCategory.CONTACT_IDENTITY,
    MedicalContextEntity.EMAIL: IdentityCategory.CONTACT_IDENTITY,
    MedicalContextEntity.ADDRESS: IdentityCategory.CONTACT_IDENTITY,

    MedicalContextEntity.DATE_OF_BIRTH: IdentityCategory.TEMPORAL_IDENTITY,
    MedicalContextEntity.ADMISSION_DATE: IdentityCategory.TEMPORAL_IDENTITY,
    MedicalContextEntity.DISCHARGE_DATE: IdentityCategory.TEMPORAL_IDENTITY,
    MedicalContextEntity.EXAM_DATE: IdentityCategory.TEMPORAL_IDENTITY,
    MedicalContextEntity.COLLECTION_DATE: IdentityCategory.TEMPORAL_IDENTITY,

    MedicalContextEntity.NATIONALITY: IdentityCategory.DEMOGRAPHIC_IDENTITY,
    MedicalContextEntity.GENDER: IdentityCategory.DEMOGRAPHIC_IDENTITY,
    MedicalContextEntity.AGE: IdentityCategory.DEMOGRAPHIC_IDENTITY,

    MedicalContextEntity.UNKNOWN_PII: IdentityCategory.UNKNOWN_IDENTITY,
}