import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.detection_merger import (
    DetectionMerger,
)


def build_candidate(
    *,
    text="Ahmed Hassan",
    start=0,
    end=None,
    source=CandidateSource.OPENMED,
    canonical_type=CandidateEntityType.PERSON_NAME,
    decision=CandidateDecision.PENDING,
    confidence=0.90,
):
    if end is None:
        end = start + len(text)

    return MedNexusCandidateEntity(
        text=text,
        start=start,
        end=end,
        source=source,
        raw_label="test_label",
        canonical_type=canonical_type,
        decision=decision,
        confidence=confidence,
    )


def test_merge_empty_groups():
    assert DetectionMerger.merge() == ()


def test_merge_none_groups():
    assert DetectionMerger.merge(
        None,
        None,
    ) == ()


def test_merge_single_group():
    candidate = build_candidate()

    merged = DetectionMerger.merge(
        [candidate]
    )

    assert merged == (candidate,)


def test_merge_preserves_source_order():
    first = build_candidate(
        text="Phone",
        start=20,
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
    )

    second = build_candidate(
        text="Ahmed",
        start=5,
    )

    merged = DetectionMerger.merge(
        [first, second]
    )

    assert merged[0] is second
    assert merged[1] is first


def test_exact_duplicate_is_removed():
    first = build_candidate()
    second = build_candidate()

    merged = DetectionMerger.merge(
        [first],
        [second],
    )

    assert len(merged) == 1


def test_mednexus_rule_beats_openmed_duplicate():
    openmed = build_candidate(
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    mednexus = build_candidate(
        source=(
            CandidateSource.MEDNEXUS_FIELD_RULE
        ),
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    merged = DetectionMerger.merge(
        [openmed],
        [mednexus],
    )

    assert len(merged) == 1
    assert merged[0] is mednexus


def test_arabic_rule_beats_openmed_duplicate():
    openmed = build_candidate(
        text="أحمد حسن",
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
        decision=CandidateDecision.PENDING,
    )

    mednexus = build_candidate(
        text="أحمد حسن",
        source=(
            CandidateSource.MEDNEXUS_ARABIC_RULE
        ),
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    merged = DetectionMerger.merge(
        [openmed],
        [mednexus],
    )

    assert len(merged) == 1
    assert merged[0] is mednexus


def test_accepted_beats_rejected_duplicate():
    rejected = build_candidate(
        decision=CandidateDecision.REJECT,
    )

    accepted = build_candidate(
        decision=CandidateDecision.ACCEPT,
    )

    merged = DetectionMerger.merge(
        [rejected, accepted]
    )

    assert len(merged) == 1
    assert merged[0] is accepted


def test_patient_name_beats_generic_person():
    generic = build_candidate(
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
    )

    patient = build_candidate(
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
    )

    merged = DetectionMerger.merge(
        [generic, patient]
    )

    assert len(merged) == 1
    assert merged[0] is patient


def test_longer_span_wins_when_scores_equal():
    short = build_candidate(
        text="Ahmed",
        start=0,
        end=5,
    )

    long = build_candidate(
        text="Ahmed Hassan",
        start=0,
        end=12,
    )

    merged = DetectionMerger.merge(
        [short, long]
    )

    assert len(merged) == 1
    assert merged[0] is long


def test_higher_confidence_wins_when_other_scores_equal():
    low = build_candidate(
        confidence=0.70,
    )

    high = build_candidate(
        confidence=0.95,
    )

    merged = DetectionMerger.merge(
        [low, high]
    )

    assert len(merged) == 1
    assert merged[0] is high


def test_non_overlapping_candidates_are_preserved():
    patient = build_candidate(
        text="Ahmed Hassan",
        start=0,
        end=12,
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
    )

    phone = build_candidate(
        text="+965 55555555",
        start=20,
        end=33,
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
    )

    merged = DetectionMerger.merge(
        [patient, phone]
    )

    assert len(merged) == 2


def test_overlapping_mednexus_identifier_beats_openmed_name():
    openmed = build_candidate(
        text="MRN-998122",
        start=10,
        end=20,
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
        decision=CandidateDecision.PENDING,
    )

    mednexus = build_candidate(
        text="MRN-998122",
        start=10,
        end=20,
        source=(
            CandidateSource.MEDNEXUS_FIELD_RULE
        ),
        canonical_type=(
            CandidateEntityType.MRN
        ),
        decision=CandidateDecision.ACCEPT,
    )

    merged = DetectionMerger.merge(
        [openmed, mednexus]
    )

    assert len(merged) == 1
    assert merged[0] is mednexus


def test_rejected_false_positive_does_not_remove_accepted_entity():
    accepted = build_candidate(
        text="Abdullah Al-Fahad",
        start=20,
        end=38,
        canonical_type=(
            CandidateEntityType.PHYSICIAN_NAME
        ),
        decision=CandidateDecision.KEEP,
        source=(
            CandidateSource.MEDNEXUS_FIELD_RULE
        ),
    )

    rejected = build_candidate(
        text="Al-Fahad",
        start=29,
        end=38,
        canonical_type=(
            CandidateEntityType.UNKNOWN
        ),
        decision=CandidateDecision.REJECT,
        source=CandidateSource.OPENMED,
    )

    merged = DetectionMerger.merge(
        [accepted, rejected]
    )

    assert len(merged) == 1
    assert merged[0] is accepted


def test_rejected_occupation_is_preserved_as_detection_record():
    occupation = build_candidate(
        text="Radiologist",
        start=10,
        end=21,
        canonical_type=(
            CandidateEntityType.PROFESSIONAL_ROLE
        ),
        decision=CandidateDecision.REJECT,
    )

    merged = DetectionMerger.merge(
        [occupation]
    )

    assert len(merged) == 1
    assert merged[0].decision == (
        CandidateDecision.REJECT
    )


def test_merge_two():
    first = [
        build_candidate(
            text="Ahmed",
            start=0,
        )
    ]

    second = [
        build_candidate(
            text="Phone",
            start=20,
            canonical_type=(
                CandidateEntityType.PHONE_NUMBER
            ),
        )
    ]

    merged = DetectionMerger.merge_two(
        first,
        second,
    )

    assert len(merged) == 2


def test_multiple_groups_are_supported():
    first = [
        build_candidate(
            text="Ahmed",
            start=0,
        )
    ]

    second = [
        build_candidate(
            text="Phone",
            start=20,
            canonical_type=(
                CandidateEntityType.PHONE_NUMBER
            ),
        )
    ]

    third = [
        build_candidate(
            text="Email",
            start=40,
            canonical_type=(
                CandidateEntityType.EMAIL
            ),
        )
    ]

    merged = DetectionMerger.merge(
        first,
        second,
        third,
    )

    assert len(merged) == 3


def test_generator_groups_are_supported():
    candidates = (
        build_candidate(
            text=f"Name{i}",
            start=i * 10,
        )
        for i in range(3)
    )

    merged = DetectionMerger.merge(
        candidates
    )

    assert len(merged) == 3


def test_invalid_candidate_is_rejected():
    with pytest.raises(
        TypeError,
        match=(
            "All detections must be "
            "MedNexusCandidateEntity objects"
        ),
    ):
        DetectionMerger.merge(
            [
                {
                    "text": "Ahmed",
                }
            ]
        )


def test_realistic_radiology_merge():
    patient = build_candidate(
        text="Ahmed Hassan",
        start=14,
        end=26,
        source=(
            CandidateSource.MEDNEXUS_FIELD_RULE
        ),
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    phone = build_candidate(
        text="+965 52988745",
        start=50,
        end=63,
        source=(
            CandidateSource.MEDNEXUS_FIELD_RULE
        ),
        canonical_type=(
            CandidateEntityType.PHONE_NUMBER
        ),
        decision=CandidateDecision.ACCEPT,
    )

    occupation = build_candidate(
        text="Radiologist",
        start=100,
        end=111,
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PROFESSIONAL_ROLE
        ),
        decision=CandidateDecision.REJECT,
    )

    document = build_candidate(
        text="DOCUMENT",
        start=150,
        end=158,
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.UNKNOWN
        ),
        decision=CandidateDecision.REJECT,
    )

    merged = DetectionMerger.merge(
        [patient, phone],
        [occupation, document],
    )

    assert len(merged) == 4

    assert merged[0] is patient
    assert merged[1] is phone
    assert merged[2] is occupation
    assert merged[3] is document