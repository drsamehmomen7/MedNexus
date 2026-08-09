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

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.vocabularies.laboratory import (
    LABORATORY_AUTHORIZATION_SECTIONS,
    build_laboratory_vocabulary,
)


def create_laboratory_service() -> ClinicalVocabularyService:
    registry = VocabularyRegistry()
    registry.register(build_laboratory_vocabulary())

    return ClinicalVocabularyService(registry)


def test_build_laboratory_vocabulary():
    profile = build_laboratory_vocabulary()

    assert profile.name == "Laboratory Medicine Vocabulary"
    assert profile.specialty == Specialty.LABORATORY_MEDICINE
    assert profile.version == "1.0"
    assert len(profile.terms) == 10


def test_laboratory_vocabulary_contains_clinical_pathologist():
    profile = build_laboratory_vocabulary()

    assert any(
        term.term == "Clinical Pathologist"
        for term in profile.terms
    )


def test_laboratory_vocabulary_contains_pathologist():
    profile = build_laboratory_vocabulary()

    assert any(
        term.term == "Pathologist"
        for term in profile.terms
    )


def test_all_laboratory_terms_are_clinical_occupations():
    profile = build_laboratory_vocabulary()

    assert all(
        term.category == ClinicalCategory.CLINICAL_OCCUPATION
        for term in profile.terms
    )


def test_all_terms_are_restricted_to_laboratory_reports():
    profile = build_laboratory_vocabulary()

    assert all(
        term.document_types == ("laboratory_report",)
        for term in profile.terms
    )


def test_all_terms_have_authorization_sections():
    profile = build_laboratory_vocabulary()

    assert all(
        term.sections == LABORATORY_AUTHORIZATION_SECTIONS
        for term in profile.terms
    )


def test_clinical_pathologist_aliases_are_configured():
    profile = build_laboratory_vocabulary()

    clinical_pathologist = next(
        term
        for term in profile.terms
        if term.term == "Clinical Pathologist"
    )

    assert "Consultant Clinical Pathologist" in clinical_pathologist.aliases
    assert "Specialist Clinical Pathologist" in clinical_pathologist.aliases


def test_service_matches_clinical_pathologist_in_authorized_by_section():
    service = create_laboratory_service()

    matches = service.find_matches(
        "Consultant Clinical Pathologist",
        section="authorized_by",
        document_type="laboratory_report",
    )

    assert len(matches) == 1
    assert matches[0].text == "Consultant Clinical Pathologist"
    assert matches[0].term.term == "Clinical Pathologist"


def test_service_matches_pathologist_in_consultant_section():
    service = create_laboratory_service()

    matches = service.find_matches(
        "Consultant Pathologist",
        section="consultant",
        document_type="laboratory_report",
    )

    assert len(matches) == 1
    assert matches[0].text == "Consultant Pathologist"
    assert matches[0].term.term == "Pathologist"


def test_service_does_not_match_in_unapproved_section():
    service = create_laboratory_service()

    matches = service.find_matches(
        "Clinical Pathologist",
        section="test_results",
        document_type="laboratory_report",
    )

    assert matches == []


def test_service_does_not_match_wrong_document_type():
    service = create_laboratory_service()

    matches = service.find_matches(
        "Clinical Pathologist",
        section="authorized_by",
        document_type="radiology_report",
    )

    assert matches == []


def test_service_matches_microbiologist_alias():
    service = create_laboratory_service()

    matches = service.find_matches(
        "Consultant Microbiologist",
        section="validated_by",
        document_type="laboratory_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Microbiologist"


def test_service_matches_medical_technologist_alias():
    service = create_laboratory_service()

    matches = service.find_matches(
        "Laboratory Technologist",
        section="verified_by",
        document_type="laboratory_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Medical Technologist"


def test_service_matches_clinical_biochemist():
    service = create_laboratory_service()

    matches = service.find_matches(
        "Consultant Clinical Biochemist",
        section="approved_by",
        document_type="laboratory_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Clinical Biochemist"