from dataclasses import dataclass, field

import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
)
from backend.app.modules.medical_document_intelligence.intelligence.openmed_candidate_adapter import (
    OpenMedCandidateAdapter,
)


@dataclass
class FakeOpenMedEntity:
    text: str
    start: int
    end: int
    raw_label: str

    canonical_label: str | None = None
    confidence: float | None = 0.91
    surrogate: str | None = None

    sources: list[str] = field(
        default_factory=lambda: ["ml"]
    )

    evidence: dict = field(
        default_factory=dict
    )

    model_id: str = (
        "OpenMed/OpenMed-PII-Test"
    )

    threshold: float = 0.7
    action: str = "mask"


@dataclass
class FakeOpenMedResult:
    pii_entities: list


def test_adapt_first_name_entity():
    source_text = (
        "Patient Name: Ahmed Hassan"
    )

    entity = FakeOpenMedEntity(
        text="Ahmed",
        start=14,
        end=19,
        raw_label="first_name",
        canonical_label="FIRST_NAME",
        surrogate="[first_name]",
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    assert candidate is not None

    assert candidate.text == "Ahmed"
    assert candidate.start == 14
    assert candidate.end == 19

    assert (
        candidate.source
        == CandidateSource.OPENMED
    )

    assert (
        candidate.canonical_type
        == CandidateEntityType.PERSON_NAME
    )

    assert candidate.raw_label == "first_name"

    assert (
        candidate.surrogate
        == "[first_name]"
    )

    assert (
        candidate.decision
        == CandidateDecision.PENDING
    )


def test_adapt_occupation_entity():
    source_text = (
        "Reporting Radiologist: "
        "Dr. Abdullah Al-Fahad"
    )

    entity = FakeOpenMedEntity(
        text="Radiologist",
        start=10,
        end=21,
        raw_label="occupation",
        canonical_label="OCCUPATION",
        surrogate="[occupation]",
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    assert candidate is not None

    assert candidate.text == "Radiologist"

    assert (
        candidate.canonical_type
        == CandidateEntityType.PROFESSIONAL_ROLE
    )

    assert (
        candidate.normalized_label
        == "occupation"
    )


def test_adapt_bic_entity():
    source_text = (
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    entity = FakeOpenMedEntity(
        text="DOCUMENT",
        start=21,
        end=29,
        raw_label="bic",
        canonical_label="BIC",
        surrogate="[bic]",
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    assert candidate is not None

    assert candidate.text == "DOCUMENT"

    assert (
        candidate.canonical_type
        == CandidateEntityType.UNKNOWN
    )

    assert candidate.raw_label == "bic"

    assert candidate.surrogate == "[bic]"


def test_source_offsets_override_wrong_entity_text():
    source_text = "Phone: +965 52988745"

    entity = FakeOpenMedEntity(
        text="incorrect",
        start=7,
        end=20,
        raw_label="phone_number",
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    assert candidate is not None

    assert (
        candidate.text
        == "+965 52988745"
    )


def test_missing_offsets_use_evidence_offsets():
    source_text = "Email: person@example.com"

    entity = {
        "text": "person@example.com",
        "raw_label": "email",
        "canonical_label": "EMAIL",
        "confidence": 0.95,
        "evidence": {
            "normalized_start": 7,
            "normalized_end": 25,
        },
    }

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    assert candidate is not None

    assert candidate.start == 7
    assert candidate.end == 25

    assert (
        candidate.canonical_type
        == CandidateEntityType.EMAIL
    )


def test_invalid_offsets_are_ignored():
    entity = FakeOpenMedEntity(
        text="Ahmed",
        start=100,
        end=105,
        raw_label="first_name",
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text="Patient Name: Ahmed",
        )
    )

    assert candidate is None


def test_missing_offsets_are_ignored():
    entity = {
        "text": "Ahmed",
        "raw_label": "first_name",
    }

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text="Patient Name: Ahmed",
        )
    )

    assert candidate is None


def test_invalid_confidence_becomes_none():
    source_text = "Patient Name: Ahmed"

    entity = FakeOpenMedEntity(
        text="Ahmed",
        start=14,
        end=19,
        raw_label="first_name",
        confidence=4.8,
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    assert candidate is not None
    assert candidate.confidence is None


def test_metadata_is_preserved_safely():
    source_text = (
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    entity = FakeOpenMedEntity(
        text="DOCUMENT",
        start=21,
        end=29,
        raw_label="bic",
        canonical_label="BIC",
        evidence={
            "raw_label": "bic",
            "normalized_start": 21,
            "normalized_end": 29,
            "semantic_merge": {
                "source_labels": ["bic"],
            },
        },
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    metadata = dict(
        candidate.metadata
    )

    assert (
        metadata[
            "openmed_canonical_label"
        ]
        == "BIC"
    )

    assert metadata["model_id"] == (
        "OpenMed/OpenMed-PII-Test"
    )

    assert metadata["threshold"] == 0.7

    assert metadata["action"] == "mask"

    assert metadata["sources"] == ["ml"]

    assert metadata["evidence"][
        "raw_label"
    ] == "bic"


def test_adapt_result():
    source_text = (
        "Patient Name: Ahmed Hassan\n"
        "Phone: +965 52988745"
    )

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="Ahmed",
                start=14,
                end=19,
                raw_label="first_name",
            ),
            FakeOpenMedEntity(
                text="+965 52988745",
                start=34,
                end=47,
                raw_label="phone_number",
            ),
        ]
    )

    candidates = (
        OpenMedCandidateAdapter.adapt_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert isinstance(candidates, tuple)

    assert len(candidates) == 2

    assert (
        candidates[0].canonical_type
        == CandidateEntityType.PERSON_NAME
    )

    assert (
        candidates[1].canonical_type
        == CandidateEntityType.PHONE_NUMBER
    )


def test_adapt_result_preserves_entity_order():
    source_text = "Ahmed Hassan"

    result = FakeOpenMedResult(
        pii_entities=[
            FakeOpenMedEntity(
                text="Ahmed",
                start=0,
                end=5,
                raw_label="first_name",
            ),
            FakeOpenMedEntity(
                text="Hassan",
                start=6,
                end=12,
                raw_label="last_name",
            ),
        ]
    )

    candidates = (
        OpenMedCandidateAdapter.adapt_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert candidates[0].text == "Ahmed"
    assert candidates[1].text == "Hassan"


def test_adapt_result_ignores_invalid_entities():
    source_text = "Patient Name: Ahmed"

    result = FakeOpenMedResult(
        pii_entities=[
            None,
            FakeOpenMedEntity(
                text="Ahmed",
                start=100,
                end=105,
                raw_label="first_name",
            ),
            FakeOpenMedEntity(
                text="Ahmed",
                start=14,
                end=19,
                raw_label="first_name",
            ),
        ]
    )

    candidates = (
        OpenMedCandidateAdapter.adapt_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert len(candidates) == 1
    assert candidates[0].text == "Ahmed"


def test_adapt_result_without_pii_entities():
    class EmptyResult:
        pass

    candidates = (
        OpenMedCandidateAdapter.adapt_result(
            engine_result=EmptyResult(),
            source_text="Medical report",
        )
    )

    assert candidates == ()


def test_adapt_result_with_none_pii_entities():
    result = FakeOpenMedResult(
        pii_entities=None
    )

    candidates = (
        OpenMedCandidateAdapter.adapt_result(
            engine_result=result,
            source_text="Medical report",
        )
    )

    assert candidates == ()


def test_adapt_result_rejects_none_engine_result():
    with pytest.raises(
        TypeError,
        match="engine_result cannot be None",
    ):
        OpenMedCandidateAdapter.adapt_result(
            engine_result=None,
            source_text="Medical report",
        )


def test_adapt_result_rejects_non_string_source():
    result = FakeOpenMedResult(
        pii_entities=[]
    )

    with pytest.raises(
        TypeError,
        match="source_text must be a string",
    ):
        OpenMedCandidateAdapter.adapt_result(
            engine_result=result,
            source_text=123,
        )


def test_adapt_result_rejects_mapping_as_entity_collection():
    result = FakeOpenMedResult(
        pii_entities={
            "entity": "invalid",
        }
    )

    with pytest.raises(
        TypeError,
        match=(
            "pii_entities must be an iterable "
            "of entity objects"
        ),
    ):
        OpenMedCandidateAdapter.adapt_result(
            engine_result=result,
            source_text="Medical report",
        )


def test_adapt_result_accepts_generator():
    source_text = "Ahmed Hassan"

    result = FakeOpenMedResult(
        pii_entities=(
            entity
            for entity in [
                FakeOpenMedEntity(
                    text="Ahmed",
                    start=0,
                    end=5,
                    raw_label="first_name",
                ),
                FakeOpenMedEntity(
                    text="Hassan",
                    start=6,
                    end=12,
                    raw_label="last_name",
                ),
            ]
        )
    )

    candidates = (
        OpenMedCandidateAdapter.adapt_result(
            engine_result=result,
            source_text=source_text,
        )
    )

    assert len(candidates) == 2


def test_openmed_result_objects_do_not_escape_adapter():
    source_text = "Patient Name: Ahmed"

    raw_entity = FakeOpenMedEntity(
        text="Ahmed",
        start=14,
        end=19,
        raw_label="first_name",
    )

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=raw_entity,
            source_text=source_text,
        )
    )

    assert (
        candidate.__class__.__name__
        == "MedNexusCandidateEntity"
    )

    assert (
        candidate.__class__
        is not raw_entity.__class__
    )


def test_realistic_openmed_bic_structure():
    source_text = (
        "CONFIDENTIAL MEDICAL DOCUMENT"
    )

    entity = {
        "text": "DOCUMENT",
        "start": 21,
        "end": 29,
        "raw_label": "bic",
        "canonical_label": "BIC",
        "sources": ["ml"],
        "confidence": 0.82,
        "threshold": 0.7,
        "action": "mask",
        "surrogate": "[bic]",
        "evidence": {
            "raw_label": "bic",
            "language": "en",
            "normalized_start": 21,
            "normalized_end": 29,
            "semantic_merge": {
                "mixed_label_union": False,
                "source_labels": ["bic"],
            },
        },
        "model_id": (
            "OpenMed/"
            "OpenMed-PII-SuperClinical"
        ),
    }

    candidate = (
        OpenMedCandidateAdapter.adapt_entity(
            raw_entity=entity,
            source_text=source_text,
        )
    )

    assert candidate is not None

    assert (
        candidate.canonical_type
        == CandidateEntityType.UNKNOWN
    )

    assert candidate.surrogate == "[bic]"

    assert (
        candidate.metadata[
            "openmed_canonical_label"
        ]
        == "BIC"
    )

    assert (
        candidate.metadata[
            "evidence"
        ][
            "semantic_merge"
        ][
            "source_labels"
        ]
        == ["bic"]
    )