from ..models import (
    ClinicalCategory,
    ClinicalTerm,
    Specialty,
    VocabularyProfile,
)


def build_common_vocabulary() -> VocabularyProfile:
    """
    Build the common clinical vocabulary shared across all document types.
    """

    terms = (

        ClinicalTerm(
            term="Physician",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
        ),

        ClinicalTerm(
            term="Doctor",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            aliases=("Dr", "Dr."),
        ),

        ClinicalTerm(
            term="Consultant",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
        ),

        ClinicalTerm(
            term="Specialist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
        ),

        ClinicalTerm(
            term="Resident",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
        ),

        ClinicalTerm(
            term="Registrar",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
        ),

        ClinicalTerm(
            term="Medical Officer",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
        ),

        ClinicalTerm(
            term="Surgeon",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.SURGERY,
        ),

    )

    return VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        terms=terms,
        description="Common clinical occupations and generic medical terminology.",
    )