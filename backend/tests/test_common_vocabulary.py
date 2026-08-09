from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.models import (
    ClinicalCategory,
    Specialty,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.vocabularies.common import (
    build_common_vocabulary,
)


def test_build_common_vocabulary():
    profile = build_common_vocabulary()

    assert profile.name == "Common Vocabulary"
    assert profile.specialty == Specialty.COMMON
    assert len(profile.terms) > 0


def test_common_vocabulary_contains_physician():
    profile = build_common_vocabulary()

    assert any(
        term.term == "Physician"
        for term in profile.terms
    )


def test_common_vocabulary_contains_doctor():
    profile = build_common_vocabulary()

    assert any(
        term.term == "Doctor"
        for term in profile.terms
    )


def test_doctor_has_aliases():
    profile = build_common_vocabulary()

    doctor = next(
        term
        for term in profile.terms
        if term.term == "Doctor"
    )

    assert "Dr" in doctor.aliases
    assert "Dr." in doctor.aliases


def test_all_terms_are_clinical_occupations():
    profile = build_common_vocabulary()

    assert all(
        term.category == ClinicalCategory.CLINICAL_OCCUPATION
        for term in profile.terms
    )


def test_surgeon_is_mapped_to_surgery_specialty():
    profile = build_common_vocabulary()

    surgeon = next(
        term
        for term in profile.terms
        if term.term == "Surgeon"
    )

    assert surgeon.specialty == Specialty.SURGERY