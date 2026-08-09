from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.models import (
    ClinicalCategory,
    Specialty,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.registry import (
    VocabularyRegistry,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.service import (
    ClinicalVocabularyService,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.vocabularies.pathology import (
    PATHOLOGY_CLINICAL_SECTIONS,
    build_pathology_vocabulary,
)


def create_pathology_service() -> ClinicalVocabularyService:
    registry = VocabularyRegistry()
    registry.register(build_pathology_vocabulary())

    return ClinicalVocabularyService(registry)


def test_build_pathology_vocabulary():
    profile = build_pathology_vocabulary()

    assert profile.name == "Pathology Vocabulary"
    assert profile.specialty == Specialty.PATHOLOGY
    assert profile.version == "1.0"
    assert len(profile.terms) == 15


def test_pathology_vocabulary_contains_pathologist():
    profile = build_pathology_vocabulary()

    assert any(
        term.term == "Pathologist"
        for term in profile.terms
    )


def test_pathology_vocabulary_contains_histopathologist():
    profile = build_pathology_vocabulary()

    assert any(
        term.term == "Histopathologist"
        for term in profile.terms
    )


def test_pathologist_is_clinical_occupation():
    profile = build_pathology_vocabulary()

    pathologist = next(
        term
        for term in profile.terms
        if term.term == "Pathologist"
    )

    assert pathologist.category == ClinicalCategory.CLINICAL_OCCUPATION
    assert pathologist.specialty == Specialty.PATHOLOGY


def test_all_terms_are_restricted_to_pathology_reports():
    profile = build_pathology_vocabulary()

    assert all(
        term.document_types == ("pathology_report",)
        for term in profile.terms
    )


def test_all_terms_use_pathology_sections():
    profile = build_pathology_vocabulary()

    assert all(
        term.sections == PATHOLOGY_CLINICAL_SECTIONS
        for term in profile.terms
    )


def test_pathologist_aliases_are_configured():
    profile = build_pathology_vocabulary()

    pathologist = next(
        term
        for term in profile.terms
        if term.term == "Pathologist"
    )

    assert "Clinical Pathologist" in pathologist.aliases
    assert "Consultant Pathologist" in pathologist.aliases
    assert "Surgical Pathologist" in pathologist.aliases


def test_service_matches_consultant_pathologist():
    service = create_pathology_service()

    matches = service.find_matches(
        "Consultant Pathologist",
        section="authorized_by",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].text == "Consultant Pathologist"
    assert matches[0].term.term == "Pathologist"


def test_service_matches_histopathologist():
    service = create_pathology_service()

    matches = service.find_matches(
        "Consultant Histopathologist",
        section="signed_by",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Histopathologist"


def test_service_matches_gross_description_alias():
    service = create_pathology_service()

    matches = service.find_matches(
        "Gross Description",
        section="gross_description",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Gross Examination"


def test_service_matches_microscopic_description_alias():
    service = create_pathology_service()

    matches = service.find_matches(
        "Microscopic Description",
        section="microscopic_description",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Microscopic Examination"


def test_service_matches_carcinoma_alias():
    service = create_pathology_service()

    matches = service.find_matches(
        "Invasive Carcinoma",
        section="diagnosis",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Carcinoma"


def test_service_matches_immunohistochemistry_alias():
    service = create_pathology_service()

    matches = service.find_matches(
        "Immunohistochemical Staining",
        section="microscopic_description",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Immunohistochemistry"


def test_service_matches_lymphovascular_invasion():
    service = create_pathology_service()

    matches = service.find_matches(
        "Lymphovascular Invasion is identified.",
        section="diagnosis",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Lymphovascular Invasion"


def test_service_does_not_match_wrong_document_type():
    service = create_pathology_service()

    matches = service.find_matches(
        "Consultant Pathologist",
        section="authorized_by",
        document_type="laboratory_report",
    )

    assert matches == []


def test_service_does_not_match_unapproved_section():
    service = create_pathology_service()

    matches = service.find_matches(
        "Carcinoma",
        section="patient_information",
        document_type="pathology_report",
    )

    assert matches == []