import pytest

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.models import (
    ClinicalCategory,
    ClinicalTerm,
    MatchMode,
    Specialty,
    VocabularyProfile,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.registry import (
    VocabularyRegistry,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.service import (
    ClinicalVocabularyMatch,
    ClinicalVocabularyService,
)


def create_service(
    *profiles: VocabularyProfile,
) -> ClinicalVocabularyService:
    vocabulary_registry = VocabularyRegistry()

    for profile in profiles:
        vocabulary_registry.register(profile)

    return ClinicalVocabularyService(vocabulary_registry)


def test_find_matches_returns_empty_list_for_empty_text():
    service = create_service()

    assert service.find_matches("") == []


def test_find_matches_rejects_non_string_text():
    service = create_service()

    with pytest.raises(
        TypeError,
        match="Text must be a string.",
    ):
        service.find_matches(None)


def test_find_matches_primary_term():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
    )

    profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    matches = service.find_matches(
        "Consultant Clinical Pathologist"
    )

    assert len(matches) == 1
    assert isinstance(matches[0], ClinicalVocabularyMatch)
    assert matches[0].text == "Pathologist"
    assert matches[0].term == term


def test_matching_is_case_insensitive_by_default():
    term = ClinicalTerm(
        term="Radiologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.RADIOLOGY,
    )

    profile = VocabularyProfile(
        name="Radiology Vocabulary",
        specialty=Specialty.RADIOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    matches = service.find_matches(
        "CONSULTANT RADIOLOGIST"
    )

    assert len(matches) == 1
    assert matches[0].text == "RADIOLOGIST"


def test_case_sensitive_matching():
    term = ClinicalTerm(
        term="MRI",
        category=ClinicalCategory.IMAGING_TERM,
        specialty=Specialty.RADIOLOGY,
        case_sensitive=True,
    )

    profile = VocabularyProfile(
        name="Radiology Vocabulary",
        specialty=Specialty.RADIOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    assert len(service.find_matches("MRI brain")) == 1
    assert service.find_matches("mri brain") == []


def test_alias_matching():
    term = ClinicalTerm(
        term="Doctor",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        aliases=("Dr", "Dr."),
    )

    profile = VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        terms=(term,),
    )

    service = create_service(profile)

    matches = service.find_matches(
        "Reviewed by Dr. Ahmed."
    )

    assert len(matches) == 1
    assert matches[0].text == "Dr."
    assert matches[0].matched_value == "Dr."


def test_word_mode_does_not_match_inside_another_word():
    term = ClinicalTerm(
        term="Resident",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
    )

    profile = VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        terms=(term,),
    )

    service = create_service(profile)

    assert len(service.find_matches("Resident physician")) == 1
    assert service.find_matches("Residential address") == []


def test_exact_mode_requires_entire_text_match():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        match_mode=MatchMode.EXACT,
    )

    profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    assert len(service.find_matches("Pathologist")) == 1
    assert service.find_matches("Consultant Pathologist") == []


def test_section_filtering():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        sections=("authorized_by", "consultant"),
    )

    profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    assert len(
        service.find_matches(
            "Clinical Pathologist",
            section="authorized_by",
        )
    ) == 1

    assert service.find_matches(
        "Clinical Pathologist",
        section="diagnosis",
    ) == []

    assert service.find_matches(
        "Clinical Pathologist",
        section=None,
    ) == []


def test_document_type_filtering():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
        document_types=(
            "laboratory_report",
            "pathology_report",
        ),
    )

    profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    assert len(
        service.find_matches(
            "Clinical Pathologist",
            document_type="laboratory_report",
        )
    ) == 1

    assert service.find_matches(
        "Clinical Pathologist",
        document_type="radiology_report",
    ) == []


def test_specialty_filtering():
    pathology_term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
    )

    radiology_term = ClinicalTerm(
        term="Radiologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.RADIOLOGY,
    )

    pathology_profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(pathology_term,),
    )

    radiology_profile = VocabularyProfile(
        name="Radiology Vocabulary",
        specialty=Specialty.RADIOLOGY,
        terms=(radiology_term,),
    )

    service = create_service(
        pathology_profile,
        radiology_profile,
    )

    matches = service.find_matches(
        "Pathologist and Radiologist",
        specialties=(Specialty.PATHOLOGY,),
    )

    assert len(matches) == 1
    assert matches[0].term == pathology_term


def test_common_specialty_is_included_with_specialty_filter():
    common_term = ClinicalTerm(
        term="Consultant",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.COMMON,
    )

    pathology_term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
    )

    common_profile = VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        terms=(common_term,),
    )

    pathology_profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(pathology_term,),
    )

    service = create_service(
        common_profile,
        pathology_profile,
    )

    matches = service.find_matches(
        "Consultant Pathologist",
        specialties=(Specialty.PATHOLOGY,),
    )

    assert len(matches) == 2


def test_invalid_specialty_filter_raises_error():
    service = create_service()

    with pytest.raises(
        TypeError,
        match="Specialties must contain Specialty enum values.",
    ):
        service.find_matches(
            "Pathologist",
            specialties=("pathology",),
        )


def test_disabled_terms_are_not_matched():
    term = ClinicalTerm(
        term="Deprecated Clinical Term",
        category=ClinicalCategory.OTHER,
        enabled=False,
    )

    profile = VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        terms=(term,),
    )

    service = create_service(profile)

    assert service.find_matches(
        "Deprecated Clinical Term"
    ) == []


def test_matches_are_sorted_by_text_position():
    physician = ClinicalTerm(
        term="Physician",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
    )

    consultant = ClinicalTerm(
        term="Consultant",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
    )

    profile = VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        terms=(
            physician,
            consultant,
        ),
    )

    service = create_service(profile)

    matches = service.find_matches(
        "Consultant reviewed by Physician"
    )

    assert [match.text for match in matches] == [
        "Consultant",
        "Physician",
    ]


def test_longest_overlapping_match_is_retained():
    doctor = ClinicalTerm(
        term="Doctor",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
    )

    clinical_doctor = ClinicalTerm(
        term="Clinical Doctor",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
    )

    profile = VocabularyProfile(
        name="Common Vocabulary",
        specialty=Specialty.COMMON,
        terms=(
            doctor,
            clinical_doctor,
        ),
    )

    service = create_service(profile)

    matches = service.find_matches(
        "Clinical Doctor"
    )

    assert len(matches) == 1
    assert matches[0].text == "Clinical Doctor"
    assert matches[0].term == clinical_doctor


def test_contains_clinical_term():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
    )

    profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    assert service.contains_clinical_term(
        "Consultant Pathologist"
    ) is True

    assert service.contains_clinical_term(
        "No clinical occupation here"
    ) is False


def test_get_matched_terms_returns_unique_terms():
    term = ClinicalTerm(
        term="Pathologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
    )

    profile = VocabularyProfile(
        name="Pathology Vocabulary",
        specialty=Specialty.PATHOLOGY,
        terms=(term,),
    )

    service = create_service(profile)

    matched_terms = service.get_matched_terms(
        "Pathologist reviewed by another Pathologist"
    )

    assert matched_terms == [term]