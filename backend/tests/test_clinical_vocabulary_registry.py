from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.models import (
    ClinicalCategory,
    ClinicalTerm,
    Specialty,
    VocabularyProfile,
)

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.registry import (
    VocabularyRegistry,
)


def create_term(name: str) -> ClinicalTerm:
    return ClinicalTerm(
        term=name,
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.PATHOLOGY,
    )


def create_profile(
    specialty: Specialty,
    *terms: ClinicalTerm,
) -> VocabularyProfile:
    return VocabularyProfile(
        name=f"{specialty.value} Vocabulary",
        specialty=specialty,
        terms=terms,
    )


def test_registry_is_empty_on_creation():
    registry = VocabularyRegistry()

    assert len(registry) == 0
    assert registry.list_profiles() == []
    assert registry.list_specialties() == []
    assert registry.all_terms() == []


def test_register_profile():
    registry = VocabularyRegistry()

    profile = create_profile(
        Specialty.PATHOLOGY,
        create_term("Pathologist"),
    )

    registry.register(profile)

    assert len(registry) == 1
    assert registry.has_profile(Specialty.PATHOLOGY)
    assert registry.get_profile(Specialty.PATHOLOGY) == profile


def test_register_replaces_existing_profile():
    registry = VocabularyRegistry()

    profile1 = create_profile(
        Specialty.PATHOLOGY,
        create_term("Pathologist"),
    )

    profile2 = create_profile(
        Specialty.PATHOLOGY,
        create_term("Consultant Pathologist"),
    )

    registry.register(profile1)
    registry.register(profile2)

    assert len(registry) == 1
    assert registry.get_profile(Specialty.PATHOLOGY) == profile2


def test_unregister_profile():
    registry = VocabularyRegistry()

    profile = create_profile(
        Specialty.PATHOLOGY,
        create_term("Pathologist"),
    )

    registry.register(profile)

    registry.unregister(Specialty.PATHOLOGY)

    assert len(registry) == 0
    assert registry.get_profile(Specialty.PATHOLOGY) is None
    assert registry.has_profile(Specialty.PATHOLOGY) is False


def test_clear_registry():
    registry = VocabularyRegistry()

    registry.register(
        create_profile(
            Specialty.PATHOLOGY,
            create_term("Pathologist"),
        )
    )

    registry.register(
        create_profile(
            Specialty.RADIOLOGY,
            ClinicalTerm(
                term="Radiologist",
                category=ClinicalCategory.CLINICAL_OCCUPATION,
                specialty=Specialty.RADIOLOGY,
            ),
        )
    )

    registry.clear()

    assert len(registry) == 0
    assert registry.list_profiles() == []
    assert registry.list_specialties() == []


def test_get_terms():
    registry = VocabularyRegistry()

    term1 = create_term("Pathologist")
    term2 = create_term("Clinical Pathologist")

    registry.register(
        create_profile(
            Specialty.PATHOLOGY,
            term1,
            term2,
        )
    )

    terms = registry.get_terms(Specialty.PATHOLOGY)

    assert terms == [term1, term2]


def test_get_terms_for_missing_profile_returns_empty_list():
    registry = VocabularyRegistry()

    assert registry.get_terms(Specialty.PATHOLOGY) == []


def test_all_terms_collects_every_registered_profile():
    registry = VocabularyRegistry()

    pathology_term = create_term("Pathologist")

    radiology_term = ClinicalTerm(
        term="Radiologist",
        category=ClinicalCategory.CLINICAL_OCCUPATION,
        specialty=Specialty.RADIOLOGY,
    )

    registry.register(
        create_profile(
            Specialty.PATHOLOGY,
            pathology_term,
        )
    )

    registry.register(
        create_profile(
            Specialty.RADIOLOGY,
            radiology_term,
        )
    )

    all_terms = registry.all_terms()

    assert pathology_term in all_terms
    assert radiology_term in all_terms
    assert len(all_terms) == 2


def test_contains_operator():
    registry = VocabularyRegistry()

    registry.register(
        create_profile(
            Specialty.PATHOLOGY,
            create_term("Pathologist"),
        )
    )

    assert Specialty.PATHOLOGY in registry
    assert Specialty.RADIOLOGY not in registry


def test_list_specialties():
    registry = VocabularyRegistry()

    registry.register(
        create_profile(
            Specialty.PATHOLOGY,
            create_term("Pathologist"),
        )
    )

    registry.register(
        create_profile(
            Specialty.RADIOLOGY,
            ClinicalTerm(
                term="Radiologist",
                category=ClinicalCategory.CLINICAL_OCCUPATION,
                specialty=Specialty.RADIOLOGY,
            ),
        )
    )

    specialties = registry.list_specialties()

    assert Specialty.PATHOLOGY in specialties
    assert Specialty.RADIOLOGY in specialties
    assert len(specialties) == 2


def test_list_profiles():
    registry = VocabularyRegistry()

    pathology_profile = create_profile(
        Specialty.PATHOLOGY,
        create_term("Pathologist"),
    )

    radiology_profile = create_profile(
        Specialty.RADIOLOGY,
        ClinicalTerm(
            term="Radiologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.RADIOLOGY,
        ),
    )

    registry.register(pathology_profile)
    registry.register(radiology_profile)

    profiles = registry.list_profiles()

    assert pathology_profile in profiles
    assert radiology_profile in profiles
    assert len(profiles) == 2