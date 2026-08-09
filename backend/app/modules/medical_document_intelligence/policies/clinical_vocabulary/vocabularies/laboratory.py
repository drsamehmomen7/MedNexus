from ..models import (
    ClinicalCategory,
    ClinicalTerm,
    Specialty,
    VocabularyProfile,
)


LABORATORY_AUTHORIZATION_SECTIONS = (
    "authorized_by",
    "approved_by",
    "validated_by",
    "verified_by",
    "reported_by",
    "signed_by",
    "consultant",
)


def build_laboratory_vocabulary() -> VocabularyProfile:
    """
    Build the local curated vocabulary for laboratory medicine.

    Version 1 focuses on clinical occupations and specialties that may be
    incorrectly classified as personal occupations by external
    de-identification engines.

    The vocabulary is intentionally structured so it can later be extended
    with document-type profiles, MedCAT, scispaCy, UMLS, and SNOMED CT.
    """

    terms = (
        ClinicalTerm(
            term="Clinical Pathologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Consultant Clinical Pathologist",
                "Specialist Clinical Pathologist",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Pathologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Consultant Pathologist",
                "Specialist Pathologist",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Laboratory Physician",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.LABORATORY_MEDICINE,
            aliases=(
                "Lab Physician",
                "Clinical Laboratory Physician",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Laboratory Consultant",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.LABORATORY_MEDICINE,
            aliases=(
                "Lab Consultant",
                "Consultant Laboratory Medicine",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Medical Laboratory Scientist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.LABORATORY_MEDICINE,
            aliases=(
                "Clinical Laboratory Scientist",
                "Biomedical Scientist",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Medical Technologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.LABORATORY_MEDICINE,
            aliases=(
                "Laboratory Technologist",
                "Lab Technologist",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Laboratory Technician",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.LABORATORY_MEDICINE,
            aliases=(
                "Lab Technician",
                "Medical Laboratory Technician",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Microbiologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.MICROBIOLOGY,
            aliases=(
                "Clinical Microbiologist",
                "Consultant Microbiologist",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Hematologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.LABORATORY_MEDICINE,
            aliases=(
                "Clinical Hematologist",
                "Consultant Hematologist",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
        ClinicalTerm(
            term="Clinical Biochemist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.LABORATORY_MEDICINE,
            aliases=(
                "Medical Biochemist",
                "Consultant Clinical Biochemist",
            ),
            sections=LABORATORY_AUTHORIZATION_SECTIONS,
            document_types=("laboratory_report",),
        ),
    )

    return VocabularyProfile(
        name="Laboratory Medicine Vocabulary",
        specialty=Specialty.LABORATORY_MEDICINE,
        terms=terms,
        description=(
            "Local curated laboratory medicine vocabulary for protecting "
            "clinical occupations and specialty titles from false-positive "
            "de-identification."
        ),
        version="1.0",
    )