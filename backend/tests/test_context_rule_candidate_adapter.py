import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
)
from backend.app.modules.medical_document_intelligence.intelligence.context_rule_candidate_adapter import (
    ContextRuleCandidateAdapter,
)
from backend.app.modules.medical_document_intelligence.intelligence.entity_canonicalizer import (
    EntityCanonicalizer,
)
from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.schemas.detected_entity import (
    DetectedEntity,
)


def test_adapts_context_detection_without_losing_offsets():
    source_text = "Patient Name: Ahmed Hassan"
    value = "Ahmed Hassan"
    start = source_text.index(value)
    detection = DetectedEntity(
        entity=MedicalContextEntity.PATIENT_NAME,
        value=value,
        start=start,
        end=start + len(value),
        source="context_rule_engine.field",
        confidence=1.0,
        label="Patient Name",
        normalized_label="patient_name",
    )

    candidate = ContextRuleCandidateAdapter.adapt(
        detection=detection,
        source_text=source_text,
    )

    assert candidate.text == value
    assert candidate.start == start
    assert candidate.end == start + len(value)
    assert candidate.matches_source_text(source_text)
    assert candidate.source == CandidateSource.MEDNEXUS_FIELD_RULE
    assert candidate.decision == CandidateDecision.PENDING
    assert candidate.canonical_type == CandidateEntityType.UNKNOWN
    assert candidate.metadata["source_span_matches"] is True
    assert (
        EntityCanonicalizer.canonicalize(candidate).canonical_type
        == CandidateEntityType.PATIENT_NAME
    )


def test_adapts_inline_detection_source():
    source_text = "MRN-123456"
    detection = DetectedEntity(
        entity=MedicalContextEntity.MRN,
        value=source_text,
        start=0,
        end=len(source_text),
        source="context_rule_engine.inline",
    )

    candidate = ContextRuleCandidateAdapter.adapt(
        detection=detection,
        source_text=source_text,
    )

    assert candidate.source == CandidateSource.MEDNEXUS_INLINE_RULE


def test_adapter_rejects_invalid_detection_object():
    with pytest.raises(TypeError, match="DetectedEntity"):
        ContextRuleCandidateAdapter.adapt(
            detection=object(),
            source_text="Medical report",
        )
