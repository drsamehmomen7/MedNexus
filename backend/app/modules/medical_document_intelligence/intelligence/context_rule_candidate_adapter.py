from __future__ import annotations

from typing import Iterable, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.schemas.detected_entity import (
    DetectedEntity,
)


class ContextRuleCandidateAdapter:
    """Adapt ContextRuleEngine detections to the Intelligence Core contract."""

    SOURCE_MAP = {
        "context_rule_engine.field": CandidateSource.MEDNEXUS_FIELD_RULE,
        "context_rule_engine.inline": CandidateSource.MEDNEXUS_INLINE_RULE,
    }

    @classmethod
    def adapt(
        cls,
        *,
        detection: DetectedEntity,
        source_text: str,
    ) -> MedNexusCandidateEntity:
        if not isinstance(detection, DetectedEntity):
            raise TypeError("detection must be a DetectedEntity.")
        if not isinstance(source_text, str):
            raise TypeError("source_text must be a string.")

        return MedNexusCandidateEntity(
            text=detection.value,
            start=detection.start,
            end=detection.end,
            source=cls.SOURCE_MAP.get(
                detection.source,
                CandidateSource.UNKNOWN,
            ),
            raw_label=detection.entity.value,
            canonical_type=CandidateEntityType.UNKNOWN,
            confidence=float(detection.confidence),
            decision=CandidateDecision.PENDING,
            normalized_label=detection.normalized_label,
            metadata={
                "adapter": "context_rule_candidate_adapter",
                "detector_source": detection.source,
                "field_label": detection.label,
                "source_span_matches": detection.matches_source_text(
                    source_text
                ),
            },
        )

    @classmethod
    def adapt_many(
        cls,
        *,
        detections: Iterable[DetectedEntity],
        source_text: str,
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        if detections is None:
            raise TypeError("detections must be an iterable.")
        if not isinstance(source_text, str):
            raise TypeError("source_text must be a string.")

        return tuple(
            cls.adapt(
                detection=detection,
                source_text=source_text,
            )
            for detection in detections
        )
