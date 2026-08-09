import pytest

from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.schemas.detected_entity import (
    DetectedEntity,
)


def test_create_valid_detected_entity():
    text = "Patient Name: Ahmed Hassan"
    value = "Ahmed Hassan"
    start = text.index(value)

    detection = DetectedEntity(
        entity=MedicalContextEntity.PATIENT_NAME,
        value=value,
        start=start,
        end=start + len(value),
        source="canonical_label_detector",
        confidence=1.0,
        label="Patient Name",
        normalized_label="patient_name",
    )

    assert detection.entity == MedicalContextEntity.PATIENT_NAME
    assert detection.value == "Ahmed Hassan"
    assert detection.source == "canonical_label_detector"
    assert detection.confidence == 1.0
    assert detection.length == len(value)
    assert detection.matches_source_text(text) is True


def test_detected_entity_is_immutable():
    detection = DetectedEntity(
        entity=MedicalContextEntity.MRN,
        value="MRN-99812",
        start=0,
        end=9,
        source="pattern_detector",
    )

    with pytest.raises(AttributeError):
        detection.value = "MRN-00000"


def test_reject_empty_value():
    with pytest.raises(ValueError):
        DetectedEntity(
            entity=MedicalContextEntity.PATIENT_NAME,
            value="",
            start=0,
            end=1,
            source="canonical_label_detector",
        )


def test_reject_invalid_entity_type():
    with pytest.raises(TypeError):
        DetectedEntity(
            entity="PATIENT_NAME",
            value="Ahmed Hassan",
            start=0,
            end=12,
            source="canonical_label_detector",
        )


def test_reject_negative_start():
    with pytest.raises(ValueError):
        DetectedEntity(
            entity=MedicalContextEntity.MRN,
            value="MRN-99812",
            start=-1,
            end=8,
            source="pattern_detector",
        )


def test_reject_end_before_start():
    with pytest.raises(ValueError):
        DetectedEntity(
            entity=MedicalContextEntity.MRN,
            value="MRN-99812",
            start=10,
            end=5,
            source="pattern_detector",
        )


def test_reject_confidence_above_one():
    with pytest.raises(ValueError):
        DetectedEntity(
            entity=MedicalContextEntity.PATIENT_NAME,
            value="Ahmed Hassan",
            start=0,
            end=12,
            source="ai_detector",
            confidence=1.2,
        )


def test_reject_confidence_below_zero():
    with pytest.raises(ValueError):
        DetectedEntity(
            entity=MedicalContextEntity.PATIENT_NAME,
            value="Ahmed Hassan",
            start=0,
            end=12,
            source="ai_detector",
            confidence=-0.1,
        )


def test_matches_source_text_returns_false_for_wrong_offsets():
    text = "Patient Name: Ahmed Hassan"

    detection = DetectedEntity(
        entity=MedicalContextEntity.PATIENT_NAME,
        value="Ahmed Hassan",
        start=0,
        end=12,
        source="canonical_label_detector",
    )

    assert detection.matches_source_text(text) is False