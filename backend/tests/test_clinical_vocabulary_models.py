import pytest

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.models import (
    ClinicalCategory,
    ClinicalTerm,
    MatchMode,
    Specialty,
    VocabularyProfile,
)


def test_clinical_term_creation():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        sections=("consultant",),
    )

    assert term.term == "Pathologist"
    assert term.category == ClinicalCategory.CLINICAL_OCCUPATION
    assert term.specialty == Specialty.PATHOLOGY
    assert term.sections == ("consultant",)
    assert term.match_mode == MatchMode.WORD
    assert term.enabled is True
    assert term.source == "mednexus_local"


def test_clinical_term_rejects_empty_term():
    with pytest.raises(
        ValueError,
        match="Clinical term must not be empty.",
    ):
        ClinicalTerm(
            term="   ",
            category=ClinicalCategory.OTHER,
        )


def test_clinical_term_normalizes_term():
    term = ClinicalTerm(
        term="  Radiologist  ",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.RADIOLOGY,
    )

    assert term.term == "Radiologist"


def test_clinical_term_normalizes_aliases():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        aliases=(
            "Clinical Pathologist",
            " clinical pathologist ",
            "",
            "Consultant Pathologist",
        ),
    )

    assert term.aliases == (
        "Clinical Pathologist",
        "Consultant Pathologist",
    )


def test_clinical_term_normalizes_sections():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        sections=(
            "consultant",
            " Consultant ",
            "",
            "authorized_by",
        ),
    )

    assert term.sections == (
        "consultant",
        "authorized_by",
    )


def test_clinical_term_normalizes_document_types():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        document_types=(
            "laboratory_report",
            " Laboratory_Report ",
            "",
            "pathology_report",
        ),
    )

    assert term.document_types == (
        "laboratory_report",
        "pathology_report",
    )


def test_all_terms_returns_primary_term_and_aliases():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        aliases=(
            "Clinical Pathologist",
            "Consultant Pathologist",
        ),
    )

    assert term.all_terms() == (
        "Pathologist",
        "Clinical Pathologist",
        "Consultant Pathologist",
    )


def test_term_without_sections_applies_globally():
    term = ClinicalTerm(
        term="Hemoglobin",
        category=ClinicalCategory.LABORATORY_TEST,
        specialty=Specialty.LABORATORY_MEDICINE,
    )

    assert term.applies_to_section(None) is True
    assert term.applies_to_section("cbc") is True
    assert term.applies_to_section("consultant") is True


def test_term_with_sections_requires_matching_section():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        sections=("consultant",),
    )

    assert term.applies_to_section("consultant") is True
    assert term.applies_to_section(" Consultant ") is True
    assert term.applies_to_section("diagnosis") is False
    assert term.applies_to_section(None) is False


def test_term_without_document_types_applies_globally():
    term = ClinicalTerm(
        term="Creatinine",
        category=ClinicalCategory.LABORATORY_TEST,
        specialty=Specialty.LABORATORY_MEDICINE,
    )

    assert term.applies_to_document_type(None) is True
    assert term.applies_to_document_type("laboratory_report") is True
    assert term.applies_to_document_type("discharge_summary") is True


def test_term_with_document_types_requires_matching_document_type():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        document_types=(
            "laboratory_report",
            "pathology_report",
        ),
    )

    assert term.applies_to_document_type("laboratory_report") is True
    assert term.applies_to_document_type(" Pathology_Report ") is True
    assert term.applies_to_document_type("radiology_report") is False
    assert term.applies_to_document_type(None) is False


def test_optional_terminology_codes_are_normalized():
    term = ClinicalTerm(
        term="Carcinoma",
        category=ClinicalCategory.DIAGNOSIS,
        specialty=Specialty.ONCOLOGY,
        snomed_code=" 68453008 ",
        umls_cui=" C0007097 ",
    )

    assert term.snomed_code == "68453008"
    assert term.umls_cui == "C0007097"


def test_empty_optional_terminology_codes_become_none():
    term = ClinicalTerm(
        term="Carcinoma",
        category=ClinicalCategory.DIAGNOSIS,
        specialty=Specialty.ONCOLOGY,
        snomed_code="   ",
        umls_cui="",
    )

    assert term.snomed_code is None
    assert term.umls_cui is None


def test_empty_source_defaults_to_mednexus_local():
    term = ClinicalTerm(
        term="Radiologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.RADIOLOGY,
        source="   ",
    )

    assert term.source == "mednexus_local"


def test_vocabulary_profile_creation():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
    )

    profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(term,),
        description="Local pathology vocabulary.",
        version="1.0",
    )

    assert profile.name == "Pathology Vocabulary"
    assert profile.specialty == Specialty.PATHOLOGY
    assert profile.terms == (term,)
    assert profile.description == "Local pathology vocabulary."
    assert profile.version == "1.0"


def test_vocabulary_profile_rejects_empty_name():
    with pytest.raises(
        ValueError,
        match="Vocabulary profile name must not be empty.",
    ):
        VocabularyProfile(
            name="   ",
            specialty=Specialty.COMMON,
        )


def test_vocabulary_profile_normalizes_name_and_version():
    profile = VocabularyProfile(
        name="  Common Vocabulary  ",
        specialty=Specialty.COMMON,
        version=" 1.1 ",
    )

    assert profile.name == "Common Vocabulary"
    assert profile.version == "1.1"


def test_vocabulary_profile_defaults_empty_version_to_1_0():
    profile = VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        version="   ",
    )

    assert profile.version == "1.0"


def test_enabled_terms_returns_only_enabled_terms():
    enabled_term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        enabled=True,
    )

    disabled_term = ClinicalTerm(
        term="Deprecated Term",
        category=ClinicalCategory.OTHER,
        specialty=Specialty.COMMON,
        enabled=False,
    )

    profile = VocabularyProfile(
        name="Test Vocabulary",
        specialty=Specialty.COMMON,
        terms=(
            enabled_term,
            disabled_term,
        ),
    )

    assert profile.enabled_terms() == (enabled_term,)


def test_dataclasses_are_immutable():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
    )

    profile = VocabularyProfile(
        name="Test Vocabulary",
        specialty=Specialty.COMMON,
        terms=(term,),
    )

    with pytest.raises(Exception):
        term.term = "Radiologist"

    with pytest.raises(Exception):
        profile.name = "Modified Vocabulary"