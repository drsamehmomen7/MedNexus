import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.entity_canonicalizer import (
    EntityCanonicalizer,
)


def build_candidate(
    *,
    raw_label="first_name",
    canonical_type=CandidateEntityType.UNKNOWN,
):
    return MedNexusCandidateEntity(
        text="Ahmed",
        start=0,
        end=5,
        source=CandidateSource.OPENMED,
        raw_label=raw_label,
        canonical_type=canonical_type,
        confidence=0.92,
    )


@pytest.mark.parametrize(
    ("raw_label", "expected_type"),
    [
        (
            "first_name",
            CandidateEntityType.PERSON_NAME,
        ),
        (
            "last_name",
            CandidateEntityType.PERSON_NAME,
        ),
        (
            "user_name",
            CandidateEntityType.PERSON_NAME,
        ),
        (
            "patient_name",
            CandidateEntityType.PATIENT_NAME,
        ),
        (
            "physician_name",
            CandidateEntityType.PHYSICIAN_NAME,
        ),
        (
            "nurse_name",
            CandidateEntityType.NURSE_NAME,
        ),
        (
            "guardian_name",
            CandidateEntityType.GUARDIAN_NAME,
        ),
        (
            "civil_id",
            CandidateEntityType.CIVIL_ID,
        ),
        (
            "national_id",
            CandidateEntityType.CIVIL_ID,
        ),
        (
            "mrn",
            CandidateEntityType.MRN,
        ),
        (
            "visit_number",
            CandidateEntityType.VISIT_NUMBER,
        ),
        (
            "accession_number",
            CandidateEntityType.ACCESSION_NUMBER,
        ),
        (
            "specimen_number",
            CandidateEntityType.SPECIMEN_NUMBER,
        ),
        (
            "phone_number",
            CandidateEntityType.PHONE_NUMBER,
        ),
        (
            "email",
            CandidateEntityType.EMAIL,
        ),
        (
            "address",
            CandidateEntityType.ADDRESS,
        ),
        (
            "date_of_birth",
            CandidateEntityType.DATE_OF_BIRTH,
        ),
        (
            "admission_date",
            CandidateEntityType.ADMISSION_DATE,
        ),
        (
            "discharge_date",
            CandidateEntityType.DISCHARGE_DATE,
        ),
        (
            "date",
            CandidateEntityType.GENERAL_DATE,
        ),
        (
            "organization",
            CandidateEntityType.ORGANIZATION,
        ),
        (
            "location",
            CandidateEntityType.LOCATION,
        ),
        (
            "occupation",
            CandidateEntityType.PROFESSIONAL_ROLE,
        ),
        (
            "bic",
            CandidateEntityType.UNKNOWN,
        ),
    ],
)
def test_resolve_label(
    raw_label,
    expected_type,
):
    assert (
        EntityCanonicalizer.resolve_label(
            raw_label
        )
        == expected_type
    )


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        (" FIRST_NAME ", "first_name"),
        ("FIRST-NAME", "first_name"),
        ("Phone Number", "phone_number"),
        ("[occupation]", "occupation"),
        ("<BIC>", "bic"),
        ("medical.record.number", "medical_record_number"),
        ("  accession__number  ", "accession_number"),
    ],
)
def test_normalize_label(
    label,
    expected,
):
    assert (
        EntityCanonicalizer.normalize_label(
            label
        )
        == expected
    )


def test_canonicalize_returns_new_candidate():
    candidate = build_candidate(
        raw_label="first_name",
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert canonicalized is not candidate

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.PERSON_NAME
    )

    assert (
        canonicalized.normalized_label
        == "first_name"
    )

    assert "Mapped source label" in (
        canonicalized.reason
    )


def test_canonicalize_preserves_original_candidate():
    candidate = build_candidate(
        raw_label="first_name",
    )

    EntityCanonicalizer.canonicalize(
        candidate
    )

    assert (
        candidate.canonical_type
        == CandidateEntityType.UNKNOWN
    )

    assert candidate.reason is None


def test_canonicalize_unknown_label():
    candidate = build_candidate(
        raw_label="completely_unknown_label",
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.UNKNOWN
    )

    assert (
        canonicalized.normalized_label
        == "completely_unknown_label"
    )

    assert "could not be mapped safely" in (
        canonicalized.reason
    )


def test_bic_is_explicitly_unknown():
    candidate = build_candidate(
        raw_label="bic",
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.UNKNOWN
    )

    assert canonicalized.normalized_label == "bic"


def test_occupation_maps_to_professional_role():
    candidate = build_candidate(
        raw_label="occupation",
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.PROFESSIONAL_ROLE
    )


def test_existing_mednexus_type_is_preserved():
    candidate = build_candidate(
        raw_label="first_name",
        canonical_type=CandidateEntityType.PATIENT_NAME,
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert canonicalized is candidate

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.PATIENT_NAME
    )


def test_existing_type_can_be_overwritten():
    candidate = build_candidate(
        raw_label="first_name",
        canonical_type=CandidateEntityType.PATIENT_NAME,
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate,
            overwrite_existing=True,
        )
    )

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.PERSON_NAME
    )


def test_canonicalize_preserves_decision():
    candidate = MedNexusCandidateEntity(
        text="Ahmed",
        start=0,
        end=5,
        source=CandidateSource.OPENMED,
        raw_label="first_name",
        canonical_type=CandidateEntityType.UNKNOWN,
        decision=CandidateDecision.ACCEPT,
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert (
        canonicalized.decision
        == CandidateDecision.ACCEPT
    )


def test_canonicalize_many_preserves_order():
    candidates = [
        build_candidate(
            raw_label="first_name",
        ),
        MedNexusCandidateEntity(
            text="+965 55555555",
            start=10,
            end=23,
            source=CandidateSource.OPENMED,
            raw_label="phone_number",
        ),
        MedNexusCandidateEntity(
            text="Document",
            start=30,
            end=38,
            source=CandidateSource.OPENMED,
            raw_label="bic",
        ),
    ]

    canonicalized = (
        EntityCanonicalizer.canonicalize_many(
            candidates
        )
    )

    assert isinstance(
        canonicalized,
        tuple,
    )

    assert len(canonicalized) == 3

    assert (
        canonicalized[0].canonical_type
        == CandidateEntityType.PERSON_NAME
    )

    assert (
        canonicalized[1].canonical_type
        == CandidateEntityType.PHONE_NUMBER
    )

    assert (
        canonicalized[2].canonical_type
        == CandidateEntityType.UNKNOWN
    )


def test_canonicalize_many_accepts_generator():
    candidates = (
        build_candidate(
            raw_label=label
        )
        for label in [
            "first_name",
            "email",
            "occupation",
        ]
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize_many(
            candidates
        )
    )

    assert len(canonicalized) == 3


def test_canonicalize_rejects_invalid_candidate():
    with pytest.raises(
        TypeError,
        match=(
            "candidate must be "
            "a MedNexusCandidateEntity"
        ),
    ):
        EntityCanonicalizer.canonicalize(
            {"raw_label": "first_name"}
        )


def test_canonicalize_many_rejects_none():
    with pytest.raises(
        TypeError,
        match="candidates must be an iterable",
    ):
        EntityCanonicalizer.canonicalize_many(
            None
        )


def test_normalize_label_rejects_non_string():
    with pytest.raises(
        TypeError,
        match="label must be a string",
    ):
        EntityCanonicalizer.normalize_label(
            123
        )


def test_is_known_label():
    assert (
        EntityCanonicalizer.is_known_label(
            "first_name"
        )
        is True
    )

    assert (
        EntityCanonicalizer.is_known_label(
            "[occupation]"
        )
        is True
    )

    assert (
        EntityCanonicalizer.is_known_label(
            "unknown_medical_label"
        )
        is False
    )


def test_medical_document_bic_example():
    candidate = MedNexusCandidateEntity(
        text="Document",
        start=21,
        end=29,
        source=CandidateSource.OPENMED,
        raw_label="bic",
        surrogate="[bic]",
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.UNKNOWN
    )

    assert canonicalized.raw_label == "bic"

    assert canonicalized.surrogate == "[bic]"

    assert (
        canonicalized.decision
        == CandidateDecision.PENDING
    )


def test_reporting_radiologist_occupation_example():
    candidate = MedNexusCandidateEntity(
        text="Radiologist",
        start=10,
        end=21,
        source=CandidateSource.OPENMED,
        raw_label="occupation",
        surrogate="[occupation]",
    )

    canonicalized = (
        EntityCanonicalizer.canonicalize(
            candidate
        )
    )

    assert (
        canonicalized.canonical_type
        == CandidateEntityType.PROFESSIONAL_ROLE
    )

    assert canonicalized.raw_label == "occupation"

    assert (
        canonicalized.decision
        == CandidateDecision.PENDING
    )