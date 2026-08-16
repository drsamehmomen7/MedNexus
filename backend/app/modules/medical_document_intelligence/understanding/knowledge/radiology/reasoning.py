from __future__ import annotations

from dataclasses import dataclass

from ...models import ClassificationEvidence, DetectedSection, DocumentSubtype, DocumentType
from .evidence import DocumentEvidenceFrame, RadiologyEvidenceFrameBuilder


_MODALITIES = {
    "RAD_MODALITY_MRI": DocumentSubtype.MRI,
    "RAD_MODALITY_CT": DocumentSubtype.CT,
    "RAD_MODALITY_XRAY": DocumentSubtype.X_RAY,
    "RAD_MODALITY_ULTRASOUND": DocumentSubtype.ULTRASOUND,
    "RAD_MODALITY_DOPPLER": DocumentSubtype.DOPPLER,
    "RAD_MODALITY_MAMMOGRAPHY": DocumentSubtype.MAMMOGRAPHY,
    "RAD_MODALITY_NUCLEAR_MEDICINE": DocumentSubtype.NUCLEAR_MEDICINE,
}


@dataclass(frozen=True, slots=True)
class RadiologyAssessment:
    frame: DocumentEvidenceFrame
    domain_satisfied: bool
    report_satisfied: bool
    modality: DocumentSubtype
    score: float
    evidence: tuple[ClassificationEvidence, ...]


class RadiologyReasoner:
    """MedNexus-owned compositional Radiology domain and report reasoning."""

    @classmethod
    def assess(cls, text: str, sections: tuple[DetectedSection, ...]) -> RadiologyAssessment:
        frame = RadiologyEvidenceFrameBuilder.build(text, sections)
        modality_ids = {item.concept_id for item in frame.modality_signals}
        technique_ids = {item.concept_id for item in frame.technique_signals}
        acquisition_ids = {item.concept_id for item in frame.acquisition_signals}
        structure_ids = {item.concept_id for item in frame.structure_signals}
        domain_ids = {item.concept_id for item in frame.domain_signals}
        contextual_families = sum(bool(items) for items in (
            frame.technique_signals, frame.acquisition_signals, frame.anatomy_signals,
            frame.contrast_signals, frame.structure_signals, frame.professional_role_signals,
        ))
        imaging_coherence = bool(modality_ids) and (
            len(technique_ids | acquisition_ids) >= 2 or contextual_families >= 3
        )
        explicit_context = bool(domain_ids) and contextual_families >= 1
        structural_cluster = len(structure_ids) >= 3 and bool(
            modality_ids or frame.professional_role_signals
        )
        domain_satisfied = imaging_coherence or explicit_context or structural_cluster
        report_satisfied = domain_satisfied and (
            {"RAD_SECTION_FINDINGS", "RAD_SECTION_IMPRESSION"} <= structure_ids
            or "RAD_DOC_REPORT" in domain_ids
        )
        modality = cls._modality(modality_ids, technique_ids, acquisition_ids)
        diversity = sum(bool(items) for items in (
            frame.domain_signals, frame.modality_signals, frame.technique_signals,
            frame.acquisition_signals, frame.anatomy_signals, frame.contrast_signals,
            frame.structure_signals, frame.professional_role_signals,
        ))
        all_signals = frame.all_signals
        signal_ids = {item.concept_id for item in all_signals}
        coherent_relationships = {
            (item.concept_id, target) for item in all_signals
            for _, target in item.relationships if target in signal_ids
        }
        score = round(sum(cls._unique_strength(items) for items in (
            frame.domain_signals, frame.modality_signals, frame.technique_signals,
            frame.acquisition_signals, frame.anatomy_signals, frame.contrast_signals,
            frame.structure_signals, frame.professional_role_signals,
        )) + max(0, diversity - 2) + min(2.0, len(coherent_relationships) * 0.25), 2)
        evidence = tuple(ClassificationEvidence(
            DocumentType.RADIOLOGY_REPORT, signal.matched_text,
            cls._evidence_category(field), signal.strength, signal.matched_text,
            signal.concept_id, signal.provenance,
            signal.external_mappings, signal.relationships,
        ) for field in frame.__dataclass_fields__ for signal in getattr(frame, field))
        return RadiologyAssessment(frame, domain_satisfied, report_satisfied, modality, score, evidence)

    @staticmethod
    def _unique_strength(signals) -> float:
        strengths = {}
        for signal in signals:
            strengths[signal.concept_id] = max(strengths.get(signal.concept_id, 0), signal.strength)
        return sum(strengths.values())

    @staticmethod
    def _evidence_category(field: str) -> str:
        return field.removesuffix("_signals").replace("domain", "context").replace("structure", "section")

    @staticmethod
    def _modality(modality_ids, technique_ids, acquisition_ids) -> DocumentSubtype:
        explicit = {_MODALITIES[item] for item in modality_ids if item in _MODALITIES}
        if DocumentSubtype.DOPPLER in explicit:
            explicit.discard(DocumentSubtype.ULTRASOUND)
        if len(explicit) == 1:
            return next(iter(explicit))
        if not explicit and len(technique_ids | acquisition_ids) >= 3:
            return DocumentSubtype.MRI
        return DocumentSubtype.UNKNOWN
