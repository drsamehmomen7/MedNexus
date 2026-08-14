from enum import Enum


class ReferenceFamily(str, Enum):
    """Reference families used for provenance; no external code is asserted."""

    LOINC_DOCUMENT_ONTOLOGY = "LOINC Document Ontology"
    DICOM = "DICOM"
    DICOM_SR = "DICOM Structured Reporting"
    RADLEX = "RSNA RadLex"
    RADLEX_PLAYBOOK = "RSNA RadLex Playbook"
    RADREPORT = "RSNA RadReport"
    SNOMED_CT = "SNOMED CT"
    HL7_CDA = "HL7 CDA"
    HL7_C_CDA = "HL7 C-CDA"
    WHO_ICD_10 = "WHO ICD-10"
    WHO_ICD_11 = "WHO ICD-11"
