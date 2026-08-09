from ..models import (
    ClinicalCategory,
    ClinicalTerm,
    Specialty,
    VocabularyProfile,
)


PATHOLOGY_CLINICAL_SECTIONS = (
    "gross_description",
    "microscopic_description",
    "diagnosis",
    "final_diagnosis",
    "comment",
    "interpretation",
    "authorized_by",
    "approved_by",
    "validated_by",
    "verified_by",
    "reported_by",
    "signed_by",
    "consultant",
)


def build_pathology_vocabulary() -> VocabularyProfile:
    """
    Build the local curated vocabulary for pathology reports.

    Version 1 protects common pathology occupations, procedures,
    diagnostic terminology, and descriptive terms that may otherwise
    be incorrectly classified by external de-identification engines.
    """

    terms = (
        ClinicalTerm(
            term="Pathologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Clinical Pathologist",
                "Anatomical Pathologist",
                "Anatomic Pathologist",
                "Surgical Pathologist",
                "Consultant Pathologist",
                "Specialist Pathologist",
                "Consultant Clinical Pathologist",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Histopathologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Consultant Histopathologist",
                "Specialist Histopathologist",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Cytopathologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Consultant Cytopathologist",
                "Specialist Cytopathologist",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Histology Technician",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Histotechnologist",
                "Histotechnician",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Gross Examination",
            category=ClinicalCategory.PATHOLOGY_TERM,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Gross Description",
                "Macroscopic Examination",
                "Macroscopic Description",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Microscopic Examination",
            category=ClinicalCategory.PATHOLOGY_TERM,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Microscopic Description",
                "Histological Examination",
                "Histologic Examination",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Biopsy",
            category=ClinicalCategory.PROCEDURE,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Core Biopsy",
                "Needle Biopsy",
                "Excisional Biopsy",
                "Incisional Biopsy",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Resection",
            category=ClinicalCategory.PROCEDURE,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Surgical Resection",
                "Resection Specimen",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Carcinoma",
            category=ClinicalCategory.DIAGNOSIS,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Adenocarcinoma",
                "Squamous Cell Carcinoma",
                "Invasive Carcinoma",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Malignancy",
            category=ClinicalCategory.DIAGNOSIS,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Malignant Neoplasm",
                "Malignant Tumor",
                "Malignant Tumour",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Necrosis",
            category=ClinicalCategory.PATHOLOGY_TERM,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Tumor Necrosis",
                "Tumour Necrosis",
                "Coagulative Necrosis",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Margins",
            category=ClinicalCategory.PATHOLOGY_TERM,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Surgical Margins",
                "Resection Margins",
                "Margin Status",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Immunohistochemistry",
            category=ClinicalCategory.PROCEDURE,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Immunohistochemical Staining",
                "IHC",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Differentiation",
            category=ClinicalCategory.PATHOLOGY_TERM,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Well Differentiated",
                "Moderately Differentiated",
                "Poorly Differentiated",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
        ClinicalTerm(
            term="Lymphovascular Invasion",
            category=ClinicalCategory.PATHOLOGY_TERM,
            specialty=Specialty.PATHOLOGY,
            aliases=(
                "Lymphatic Invasion",
                "Vascular Invasion",
                "LVI",
            ),
            sections=PATHOLOGY_CLINICAL_SECTIONS,
            document_types=("pathology_report",),
        ),
    )

    return VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=terms,
        description=(
            "Local curated pathology vocabulary for protecting clinical "
            "occupations, diagnostic terminology, procedures, and pathology "
            "descriptors from false-positive de-identification."
        ),
        version="1.0",
    )