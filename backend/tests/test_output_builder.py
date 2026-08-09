import re

import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.output_builder import (
    MedNexusOutputBuilder,
    MedNexusOutputResult,
)


def build_candidate(
    source_text,
    entity_text,
    *,
    canonical_type,
    decision,
    source=CandidateSource.OPENMED,
):
    start = source_text.index(entity_text)

    return MedNexusCandidateEntity(
        text=entity_text,
        start=start,
        end=start + len(entity_text),
        source=source,
        raw_label="test",
        canonical_type=canonical_type,
        decision=decision,
        confidence=0.95,
    )


def test_build_returns_output_result():
    result = MedNexusOutputBuilder.build(
        source_text="Medical report",
        candidates=[],
    )

    assert isinstance(
        result,
        MedNexusOutputResult,
    )

    assert result.text == "Medical report"


def test_replaces_patient_name():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == (
        "Patient Name: [PATIENT_NAME]"
    )

    assert result.replaced_count == 1


def test_replaces_arabic_patient_name():
    source_text = (
        "اسم المريض: أحمد حسن"
    )

    candidate = build_candidate(
        source_text,
        "أحمد حسن",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == (
        "اسم المريض: [PATIENT_NAME]"
    )


def test_hashes_civil_id():
    source_text = (
        "Civil ID: 290020203333"
    )

    candidate = build_candidate(
        source_text,
        "290020203333",
        canonical_type=(
            CandidateEntityType.CIVIL_ID
        ),
        decision=CandidateDecision.ACCEPT,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert re.fullmatch(
        r"Civil ID: \[CIVIL_ID:[0-9a-f]{10}\]",
        result.text,
    )


def test_hash_is_deterministic():
    source_text = (
        "MRN: MRN-998122"
    )

    candidate = build_candidate(
        source_text,
        "MRN-998122",
        canonical_type=(
            CandidateEntityType.MRN
        ),
        decision=CandidateDecision.ACCEPT,
    )

    first = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    second = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert first.text == second.text


@pytest.mark.parametrize(
    ("entity_text", "entity_type", "placeholder"),
    [
        (
            "+965 52988745",
            CandidateEntityType.PHONE_NUMBER,
            "[PHONE_NUMBER]",
        ),
        (
            "patient@example.com",
            CandidateEntityType.EMAIL,
            "[EMAIL]",
        ),
        (
            "Block 5, Street 12",
            CandidateEntityType.ADDRESS,
            "[ADDRESS]",
        ),
        (
            "02/08/1990",
            CandidateEntityType.DATE_OF_BIRTH,
            "[DATE_OF_BIRTH]",
        ),
    ],
)
def test_replaces_fixed_placeholder_types(
    entity_text,
    entity_type,
    placeholder,
):
    source_text = (
        f"Value: {entity_text}"
    )

    candidate = build_candidate(
        source_text,
        entity_text,
        canonical_type=entity_type,
        decision=CandidateDecision.ACCEPT,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == (
        f"Value: {placeholder}"
    )


def test_keep_preserves_physician_name():
    source_text = (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
    )

    candidate = build_candidate(
        source_text,
        "Abdullah Al-Fahad",
        canonical_type=(
            CandidateEntityType.PHYSICIAN_NAME
        ),
        decision=CandidateDecision.KEEP,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == source_text
    assert result.kept_count == 1
    assert result.replaced_count == 0


def test_reject_preserves_radiologist_term():
    source_text = (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
    )

    candidate = build_candidate(
        source_text,
        "Radiologist",
        canonical_type=(
            CandidateEntityType.PROFESSIONAL_ROLE
        ),
        decision=CandidateDecision.REJECT,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == source_text
    assert "[occupation]" not in result.text
    assert result.rejected_count == 1


def test_reject_preserves_document_term():
    source_text = (
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    candidate = build_candidate(
        source_text,
        "DOCUMENT",
        canonical_type=(
            CandidateEntityType.UNKNOWN
        ),
        decision=CandidateDecision.REJECT,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == source_text
    assert "[bic]" not in result.text


def test_review_required_preserves_text_and_warns():
    source_text = (
        "Hospital: Al Noor Hospital"
    )

    candidate = build_candidate(
        source_text,
        "Al Noor Hospital",
        canonical_type=(
            CandidateEntityType.ORGANIZATION
        ),
        decision=(
            CandidateDecision.REVIEW_REQUIRED
        ),
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == source_text
    assert result.requires_review is True
    assert result.review_required_count == 1
    assert len(result.warnings) == 1


def test_pending_preserves_text_and_warns():
    source_text = (
        "Unknown: Possible Name"
    )

    candidate = build_candidate(
        source_text,
        "Possible Name",
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
        decision=CandidateDecision.PENDING,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    assert result.text == source_text
    assert result.pending_count == 1
    assert result.requires_review is True


def test_multiple_replacements_preserve_offsets():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Civil ID: 290020203333\n"
        "Phone: +965 52988745"
    )

    candidates = [
        build_candidate(
            source_text,
            "Ahmed Hassan",
            canonical_type=(
                CandidateEntityType.PATIENT_NAME
            ),
            decision=CandidateDecision.ACCEPT,
        ),
        build_candidate(
            source_text,
            "290020203333",
            canonical_type=(
                CandidateEntityType.CIVIL_ID
            ),
            decision=CandidateDecision.ACCEPT,
        ),
        build_candidate(
            source_text,
            "+965 52988745",
            canonical_type=(
                CandidateEntityType.PHONE_NUMBER
            ),
            decision=CandidateDecision.ACCEPT,
        ),
    ]

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=candidates,
    )

    assert (
        "Patient Name: [PATIENT_NAME]"
        in result.text
    )

    assert re.search(
        r"Civil ID: \[CIVIL_ID:[0-9a-f]{10}\]",
        result.text,
    )

    assert (
        "Phone: [PHONE_NUMBER]"
        in result.text
    )

    assert result.replaced_count == 3


def test_realistic_radiology_output():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Phone: +965 52988745\n"
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad\n"
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    candidates = [
        build_candidate(
            source_text,
            "Ahmed Hassan",
            canonical_type=(
                CandidateEntityType.PATIENT_NAME
            ),
            decision=CandidateDecision.ACCEPT,
        ),
        build_candidate(
            source_text,
            "+965 52988745",
            canonical_type=(
                CandidateEntityType.PHONE_NUMBER
            ),
            decision=CandidateDecision.ACCEPT,
        ),
        build_candidate(
            source_text,
            "Radiologist",
            canonical_type=(
                CandidateEntityType.PROFESSIONAL_ROLE
            ),
            decision=CandidateDecision.REJECT,
        ),
        build_candidate(
            source_text,
            "Abdullah Al-Fahad",
            canonical_type=(
                CandidateEntityType.PHYSICIAN_NAME
            ),
            decision=CandidateDecision.KEEP,
        ),
        build_candidate(
            source_text,
            "DOCUMENT",
            canonical_type=(
                CandidateEntityType.UNKNOWN
            ),
            decision=CandidateDecision.REJECT,
        ),
    ]

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=candidates,
    )

    assert (
        "Patient Name: [PATIENT_NAME]"
        in result.text
    )

    assert (
        "Phone: [PHONE_NUMBER]"
        in result.text
    )

    assert (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
        in result.text
    )

    assert (
        "CONFIDENTIAL MEDICAL DOCUMENT"
        in result.text
    )

    assert "[occupation]" not in result.text
    assert "[bic]" not in result.text
    assert "[first_name]" not in result.text
    assert "[last_name]" not in result.text

    assert result.replaced_count == 2
    assert result.kept_count == 1
    assert result.rejected_count == 2


def test_replacement_metadata():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    candidate = build_candidate(
        source_text,
        "Ahmed Hassan",
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    result = MedNexusOutputBuilder.build(
        source_text=source_text,
        candidates=[candidate],
    )

    replacement = result.replacements[0]

    assert replacement["original_text"] == (
        "Ahmed Hassan"
    )

    assert replacement["surrogate"] == (
        "[PATIENT_NAME]"
    )

    assert replacement["entity_type"] == (
        "patient_name"
    )

    assert replacement["decision"] == "accept"


def test_result_to_dict():
    result = MedNexusOutputBuilder.build(
        source_text="Medical report",
        candidates=[],
    )

    data = result.to_dict()

    assert data["text"] == "Medical report"
    assert data["replaced_count"] == 0
    assert data["requires_review"] is False
    assert data["warnings"] == []


def test_rejects_invalid_source_text():
    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        MedNexusOutputBuilder.build(
            source_text=123,
            candidates=[],
        )


def test_rejects_none_candidates():
    with pytest.raises(
        TypeError,
        match="candidates must be an iterable",
    ):
        MedNexusOutputBuilder.build(
            source_text="Medical report",
            candidates=None,
        )


def test_rejects_invalid_candidate_object():
    with pytest.raises(
        TypeError,
        match=(
            "All candidates must be "
            "MedNexusCandidateEntity objects"
        ),
    ):
        MedNexusOutputBuilder.build(
            source_text="Medical report",
            candidates=[
                {
                    "text": "Ahmed"
                }
            ],
        )


def test_rejects_invalid_hash_length():
    with pytest.raises(
        ValueError,
        match="hash_length must be at least 6",
    ):
        MedNexusOutputBuilder.build(
            source_text="Medical report",
            candidates=[],
            hash_length=4,
        )


def test_rejects_boolean_hash_length():
    with pytest.raises(
        TypeError,
        match="hash_length must be an integer",
    ):
        MedNexusOutputBuilder.build(
            source_text="Medical report",
            candidates=[],
            hash_length=True,
        )


def test_rejects_stale_accepted_offsets():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    candidate = MedNexusCandidateEntity(
        text="Ahmed Hassan",
        start=0,
        end=12,
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Accepted candidate offsets do not "
            "match source_text"
        ),
    ):
        MedNexusOutputBuilder.build(
            source_text=source_text,
            candidates=[candidate],
        )


def test_rejects_overlapping_accepted_spans():
    source_text = "Ahmed Hassan"

    full_name = MedNexusCandidateEntity(
        text="Ahmed Hassan",
        start=0,
        end=12,
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PATIENT_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    first_name = MedNexusCandidateEntity(
        text="Ahmed",
        start=0,
        end=5,
        source=CandidateSource.OPENMED,
        canonical_type=(
            CandidateEntityType.PERSON_NAME
        ),
        decision=CandidateDecision.ACCEPT,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Accepted candidate spans must "
            "not overlap"
        ),
    ):
        MedNexusOutputBuilder.build(
            source_text=source_text,
            candidates=[
                full_name,
                first_name,
            ],
        )