import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)


def build_candidate(
    **overrides,
) -> MedNexusCandidateEntity:
    values = {
        "text": "Ahmed Hassan",
        "start": 14,
        "end": 26,
        "source": CandidateSource.OPENMED,
        "raw_label": "first_name",
        "canonical_type": CandidateEntityType.PERSON_NAME,
        "confidence": 0.94,
        "metadata": {
            "model_id": "OpenMed-Test",
        },
    }

    values.update(overrides)

    return MedNexusCandidateEntity(
        **values
    )


def test_candidate_entity_accepts_valid_data():
    candidate = build_candidate()

    assert candidate.text == "Ahmed Hassan"
    assert candidate.start == 14
    assert candidate.end == 26
    assert candidate.source == CandidateSource.OPENMED
    assert (
        candidate.canonical_type
        == CandidateEntityType.PERSON_NAME
    )
    assert candidate.confidence == 0.94
    assert (
        candidate.decision
        == CandidateDecision.PENDING
    )


def test_candidate_entity_length():
    candidate = build_candidate()

    assert candidate.length == 12


def test_candidate_entity_is_positioned():
    candidate = build_candidate()

    assert candidate.is_positioned is True


def test_candidate_entity_matches_source_text():
    source_text = "Patient Name: Ahmed Hassan"

    candidate = build_candidate(
        start=14,
        end=26,
    )

    assert candidate.matches_source_text(
        source_text
    )


def test_candidate_entity_rejects_invalid_source_offsets():
    source_text = "Patient Name: Ahmed Hassan"

    candidate = build_candidate(
        start=0,
        end=12,
    )

    assert not candidate.matches_source_text(
        source_text
    )


def test_candidate_entity_rejects_non_string_source_text():
    candidate = build_candidate()

    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        candidate.matches_source_text(
            123
        )


def test_candidate_entity_with_decision_returns_new_object():
    candidate = build_candidate()

    accepted = candidate.with_decision(
        CandidateDecision.ACCEPT,
        reason="Validated by patient field context.",
    )

    assert accepted is not candidate

    assert (
        candidate.decision
        == CandidateDecision.PENDING
    )

    assert (
        accepted.decision
        == CandidateDecision.ACCEPT
    )

    assert accepted.reason == (
        "Validated by patient field context."
    )


def test_candidate_entity_is_accepted():
    candidate = build_candidate(
        decision=CandidateDecision.ACCEPT,
    )

    assert candidate.is_accepted is True
    assert candidate.is_rejected is False


def test_candidate_entity_is_rejected():
    candidate = build_candidate(
        decision=CandidateDecision.REJECT,
    )

    assert candidate.is_rejected is True
    assert candidate.is_accepted is False


def test_candidate_entity_requires_review():
    candidate = build_candidate(
        decision=CandidateDecision.REVIEW_REQUIRED,
    )

    assert candidate.requires_review is True


def test_candidate_entity_with_canonical_type():
    candidate = build_candidate(
        canonical_type=CandidateEntityType.PERSON_NAME,
    )

    resolved = candidate.with_canonical_type(
        CandidateEntityType.PATIENT_NAME,
        normalized_label="patient_name",
        reason="Located after Patient Name field.",
    )

    assert (
        resolved.canonical_type
        == CandidateEntityType.PATIENT_NAME
    )

    assert (
        resolved.normalized_label
        == "patient_name"
    )

    assert resolved.reason == (
        "Located after Patient Name field."
    )

    assert (
        candidate.canonical_type
        == CandidateEntityType.PERSON_NAME
    )


def test_candidate_entity_metadata_is_immutable():
    candidate = build_candidate()

    with pytest.raises(
        TypeError,
    ):
        candidate.metadata[
            "model_id"
        ] = "Modified"


def test_candidate_entity_copies_input_metadata():
    source_metadata = {
        "model_id": "OpenMed-Test",
    }

    candidate = build_candidate(
        metadata=source_metadata,
    )

    source_metadata[
        "model_id"
    ] = "Changed Outside"

    assert (
        candidate.metadata["model_id"]
        == "OpenMed-Test"
    )


def test_candidate_entity_to_dict():
    candidate = build_candidate(
        normalized_label="person_name",
        surrogate="[first_name]",
    )

    result = candidate.to_dict()

    assert result["text"] == "Ahmed Hassan"
    assert result["source"] == "openmed"
    assert result["raw_label"] == "first_name"
    assert result["canonical_type"] == "person_name"
    assert result["decision"] == "pending"
    assert result["normalized_label"] == "person_name"
    assert result["surrogate"] == "[first_name]"
    assert result["metadata"] == {
        "model_id": "OpenMed-Test",
    }


def test_candidate_entity_rejects_empty_text():
    with pytest.raises(
        ValueError,
        match="text cannot be empty",
    ):
        build_candidate(
            text="",
        )


def test_candidate_entity_rejects_non_string_text():
    with pytest.raises(
        TypeError,
        match="text must be a string",
    ):
        build_candidate(
            text=123,
        )


def test_candidate_entity_rejects_negative_start():
    with pytest.raises(
        ValueError,
        match="start cannot be negative",
    ):
        build_candidate(
            start=-1,
        )


def test_candidate_entity_rejects_end_equal_to_start():
    with pytest.raises(
        ValueError,
        match="end must be greater than start",
    ):
        build_candidate(
            start=10,
            end=10,
        )


def test_candidate_entity_rejects_end_before_start():
    with pytest.raises(
        ValueError,
        match="end must be greater than start",
    ):
        build_candidate(
            start=10,
            end=5,
        )


def test_candidate_entity_rejects_invalid_confidence_type():
    with pytest.raises(
        TypeError,
        match="confidence must be a numeric value",
    ):
        build_candidate(
            confidence="high",
        )


def test_candidate_entity_rejects_confidence_below_zero():
    with pytest.raises(
        ValueError,
        match="confidence must be between",
    ):
        build_candidate(
            confidence=-0.01,
        )


def test_candidate_entity_rejects_confidence_above_one():
    with pytest.raises(
        ValueError,
        match="confidence must be between",
    ):
        build_candidate(
            confidence=1.01,
        )


def test_candidate_entity_accepts_integer_confidence():
    candidate = build_candidate(
        confidence=1,
    )

    assert candidate.confidence == 1.0


def test_candidate_entity_rejects_boolean_confidence():
    with pytest.raises(
        TypeError,
        match="confidence must be a numeric value",
    ):
        build_candidate(
            confidence=True,
        )


def test_candidate_entity_rejects_invalid_source():
    with pytest.raises(
        TypeError,
        match="source must be a CandidateSource",
    ):
        build_candidate(
            source="openmed",
        )


def test_candidate_entity_rejects_invalid_canonical_type():
    with pytest.raises(
        TypeError,
        match=(
            "canonical_type must be "
            "a CandidateEntityType"
        ),
    ):
        build_candidate(
            canonical_type="patient_name",
        )


def test_candidate_entity_rejects_invalid_decision():
    with pytest.raises(
        TypeError,
        match="decision must be a CandidateDecision",
    ):
        build_candidate(
            decision="accept",
        )


def test_candidate_entity_rejects_non_mapping_metadata():
    with pytest.raises(
        TypeError,
        match="metadata must be a mapping",
    ):
        build_candidate(
            metadata=["invalid"],
        )


def test_candidate_entity_normalizes_labels():
    candidate = build_candidate(
        raw_label="  FIRST_NAME  ",
        normalized_label="  PERSON_NAME  ",
    )

    assert candidate.raw_label == "FIRST_NAME"
    assert candidate.normalized_label == "person_name"


def test_candidate_entity_serializes_rejected_candidate():
    candidate = build_candidate(
        text="Radiologist",
        start=10,
        end=21,
        raw_label="occupation",
        canonical_type=(
            CandidateEntityType.PROFESSIONAL_ROLE
        ),
        decision=CandidateDecision.REJECT,
        reason=(
            "Medical professional role is not "
            "patient-identifying information."
        ),
    )

    result = candidate.to_dict()

    assert result["raw_label"] == "occupation"

    assert (
        result["canonical_type"]
        == "professional_role"
    )

    assert result["decision"] == "reject"

    assert result["reason"] == (
        "Medical professional role is not "
        "patient-identifying information."
    )
