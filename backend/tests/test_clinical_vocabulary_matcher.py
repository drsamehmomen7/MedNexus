import pytest

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.matcher import (
    ClinicalVocabularyMatcher,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.models import (
    ClinicalCategory,
    ClinicalTerm,
    Specialty,
    VocabularyProfile,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.registry import (
    VocabularyRegistry,
)


def test_default_registry_contains_expected_profiles():
    matcher = ClinicalVocabularyMatcher()

    assert matcher.registry.has_profile(Specialty.COMMON)
    assert matcher.registry.has_profile(Specialty.LABORATORY_MEDICINE)
    assert matcher.registry.has_profile(Specialty.PATHOLOGY)


def test_find_matches_common_vocabulary():
    matcher = ClinicalVocabularyMatcher()

    matches = matcher.find_matches(
        "Reviewed by Consultant Physician"
    )

    matched_texts = [
        match.text
        for match in matches
    ]

    assert "Consultant" in matched_texts
    assert "Physician" in matched_texts


def test_find_matches_laboratory_vocabulary():
    matcher = ClinicalVocabularyMatcher()

    matches = matcher.find_matches(
        "Consultant Clinical Pathologist",
        section="authorized_by",
        document_type="laboratory_report",
    )

    assert len(matches) == 1
    assert matches[0].text == "Consultant Clinical Pathologist"
    assert matches[0].term.term == "Clinical Pathologist"


def test_find_matches_pathology_vocabulary():
    matcher = ClinicalVocabularyMatcher()

    matches = matcher.find_matches(
        "Invasive Carcinoma",
        section="diagnosis",
        document_type="pathology_report",
    )

    assert len(matches) == 1
    assert matches[0].term.term == "Carcinoma"


def test_laboratory_term_is_not_used_for_wrong_document_type():
    matcher = ClinicalVocabularyMatcher()

    matches = matcher.find_matches(
        "Clinical Pathologist",
        section="authorized_by",
        document_type="radiology_report",
    )

    assert matches == []


def test_pathology_term_is_not_used_in_wrong_section():
    matcher = ClinicalVocabularyMatcher()

    matches = matcher.find_matches(
        "Invasive Carcinoma",
        section="patient_information",
        document_type="pathology_report",
    )

    assert matches == []


def test_contains_match_returns_true():
    matcher = ClinicalVocabularyMatcher()

    result = matcher.contains_match(
        "Consultant Clinical Pathologist",
        section="authorized_by",
        document_type="laboratory_report",
    )

    assert result is True


def test_contains_match_returns_false():
    matcher = ClinicalVocabularyMatcher()

    result = matcher.contains_match(
        "No protected clinical vocabulary exists here.",
        section="authorized_by",
        document_type="laboratory_report",
    )

    assert result is False


def test_custom_registry_can_be_supplied():
    custom_registry = VocabularyRegistry()

    custom_term = ClinicalTerm(
        term="Custom Clinical Term",
        category=ClinicalCategory.OTHER,
        specialty=Specialty.COMMON,
    )

    custom_profile = VocabularyProfile(
        name="Custom Vocabulary",
        specialty=Specialty.COMMON,
        terms=(custom_term,),
    )

    custom_registry.register(custom_profile)

    matcher = ClinicalVocabularyMatcher(custom_registry)

    matches = matcher.find_matches(
        "Custom Clinical Term"
    )

    assert len(matches) == 1
    assert matches[0].term == custom_term


def test_protect_matches_replaces_clinical_term():
    matcher = ClinicalVocabularyMatcher()

    protected_text, mapping, next_number = matcher.protect_matches(
        "Consultant Clinical Pathologist",
        section="authorized_by",
        document_type="laboratory_report",
    )

    assert protected_text == "__CVE_0001__"
    assert mapping == {
        "__CVE_0001__": "Consultant Clinical Pathologist",
    }
    assert next_number == 2


def test_protect_matches_preserves_surrounding_text():
    matcher = ClinicalVocabularyMatcher()

    protected_text, mapping, next_number = matcher.protect_matches(
        "Authorized by Consultant Clinical Pathologist today.",
        section="authorized_by",
        document_type="laboratory_report",
    )

    assert protected_text == "Authorized by __CVE_0001__ today."
    assert mapping["__CVE_0001__"] == "Consultant Clinical Pathologist"
    assert next_number == 2


def test_protect_matches_supports_multiple_terms():
    matcher = ClinicalVocabularyMatcher()

    protected_text, mapping, next_number = matcher.protect_matches(
        "Consultant and Physician",
    )

    assert protected_text == "__CVE_0001__ and __CVE_0002__"

    assert mapping == {
        "__CVE_0001__": "Consultant",
        "__CVE_0002__": "Physician",
    }

    assert next_number == 3


def test_protect_matches_supports_custom_starting_number():
    matcher = ClinicalVocabularyMatcher()

    protected_text, mapping, next_number = matcher.protect_matches(
        "Consultant",
        starting_number=7,
    )

    assert protected_text == "__CVE_0007__"
    assert mapping == {
        "__CVE_0007__": "Consultant",
    }
    assert next_number == 8


def test_protect_matches_returns_original_text_when_no_match_exists():
    matcher = ClinicalVocabularyMatcher()

    protected_text, mapping, next_number = matcher.protect_matches(
        "No matching vocabulary.",
        starting_number=5,
    )

    assert protected_text == "No matching vocabulary."
    assert mapping == {}
    assert next_number == 5


def test_protect_matches_rejects_non_string_text():
    matcher = ClinicalVocabularyMatcher()

    with pytest.raises(
        TypeError,
        match="Text must be a string.",
    ):
        matcher.protect_matches(None)


def test_protect_matches_rejects_invalid_starting_number_type():
    matcher = ClinicalVocabularyMatcher()

    with pytest.raises(
        TypeError,
        match="Starting number must be an integer.",
    ):
        matcher.protect_matches(
            "Consultant",
            starting_number="1",
        )


def test_protect_matches_rejects_starting_number_below_one():
    matcher = ClinicalVocabularyMatcher()

    with pytest.raises(
        ValueError,
        match="Starting number must be greater than zero.",
    ):
        matcher.protect_matches(
            "Consultant",
            starting_number=0,
        )


def test_protect_matches_rejects_empty_token_prefix():
    matcher = ClinicalVocabularyMatcher()

    with pytest.raises(
        ValueError,
        match="Token prefix must not be empty.",
    ):
        matcher.protect_matches(
            "Consultant",
            token_prefix="",
        )