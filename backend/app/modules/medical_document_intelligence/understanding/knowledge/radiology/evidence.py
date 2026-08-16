from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from ...models import DetectedSection
from ..models import RecognitionConcept, RecognitionConceptCategory
from .concepts import RADIOLOGY_CONCEPTS
from ...reference_model.runtime import build_active_reference_registry
from ...reference_model.models import ConceptFamily


@dataclass(frozen=True, slots=True)
class EvidenceSignal:
    concept_id: str
    concept_family: str
    matched_text: str
    start: int
    end: int
    strength: float
    provenance: tuple[str, ...]
    context: str
    external_mappings: tuple[tuple[str, str], ...] = ()
    relationships: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentEvidenceFrame:
    domain_signals: tuple[EvidenceSignal, ...] = ()
    modality_signals: tuple[EvidenceSignal, ...] = ()
    technique_signals: tuple[EvidenceSignal, ...] = ()
    acquisition_signals: tuple[EvidenceSignal, ...] = ()
    anatomy_signals: tuple[EvidenceSignal, ...] = ()
    procedure_signals: tuple[EvidenceSignal, ...] = ()
    contrast_signals: tuple[EvidenceSignal, ...] = ()
    structure_signals: tuple[EvidenceSignal, ...] = ()
    clinical_purpose_signals: tuple[EvidenceSignal, ...] = ()
    professional_role_signals: tuple[EvidenceSignal, ...] = ()
    conflicting_signals: tuple[EvidenceSignal, ...] = ()

    @property
    def all_signals(self) -> tuple[EvidenceSignal, ...]:
        return tuple(
            signal for field_name in self.__dataclass_fields__
            for signal in getattr(self, field_name)
        )


_FAMILY_FIELD = {
    RecognitionConceptCategory.DOCUMENT_IDENTITY: "domain_signals",
    RecognitionConceptCategory.SERVICE_CONTEXT: "domain_signals",
    RecognitionConceptCategory.MODALITY: "modality_signals",
    RecognitionConceptCategory.IMAGING_TECHNIQUE: "technique_signals",
    RecognitionConceptCategory.ACQUISITION: "acquisition_signals",
    RecognitionConceptCategory.ANATOMY: "anatomy_signals",
    RecognitionConceptCategory.PROCEDURE: "procedure_signals",
    RecognitionConceptCategory.CONTRAST: "contrast_signals",
    RecognitionConceptCategory.SECTION: "structure_signals",
    RecognitionConceptCategory.CLINICAL_PURPOSE: "clinical_purpose_signals",
    RecognitionConceptCategory.AUTHOR_ROLE: "professional_role_signals",
}

_REFERENCE_FAMILY_FIELD = {
    ConceptFamily.DOCUMENT_REPORT: "domain_signals",
    ConceptFamily.IMAGING_MODALITY: "modality_signals",
    ConceptFamily.MODALITY_SUBTYPE: "modality_signals",
    ConceptFamily.IMAGING_TECHNIQUE: "technique_signals",
    ConceptFamily.ACQUISITION: "acquisition_signals",
    ConceptFamily.BODY_REGION: "anatomy_signals",
    ConceptFamily.IMAGING_FOCUS: "anatomy_signals",
    ConceptFamily.IMAGING_PROCEDURE: "procedure_signals",
    ConceptFamily.CONTRAST: "contrast_signals",
    ConceptFamily.PHARMACEUTICAL: "contrast_signals",
    ConceptFamily.CLINICAL_PURPOSE: "clinical_purpose_signals",
    ConceptFamily.REASON_FOR_EXAM: "clinical_purpose_signals",
    ConceptFamily.PROFESSIONAL_ROLE: "professional_role_signals",
    ConceptFamily.IMAGING_OBSERVATION: "clinical_purpose_signals",
    ConceptFamily.CLINICAL_FINDING: "clinical_purpose_signals",
}


class RadiologyEvidenceFrameBuilder:
    """Normalize Radiology concepts into exact, traceable source-coordinate signals."""

    @classmethod
    def build(cls, text: str, sections: tuple[DetectedSection, ...]) -> DocumentEvidenceFrame:
        reference_model = build_active_reference_registry()
        buckets: dict[str, list[EvidenceSignal]] = {name: [] for name in _FAMILY_FIELD.values()}
        section_by_concept = cls._section_concepts(sections)
        seen: set[tuple[str, int, int]] = set()
        for concept in RADIOLOGY_CONCEPTS:
            if concept.category is RecognitionConceptCategory.SECTION:
                matches = section_by_concept.get(concept.concept_id, ())
            else:
                matches = cls._matches(text, concept)
            for matched, start, end in matches:
                key = (concept.concept_id, start, end)
                if key in seen:
                    continue
                seen.add(key)
                resolved = next((item for item in reference_model.resolve(matched)
                                 if item.concept.mednexus_concept_id == concept.concept_id), None)
                canonical = resolved.concept if resolved else None
                signal = EvidenceSignal(
                    concept.concept_id,
                    canonical.concept_family.value if canonical else concept.category.value,
                    matched, start, end, concept.evidence_strength,
                    canonical.provenance if canonical else concept.external_references,
                    cls._context(text, start, end),
                    tuple((item.source_id, item.external_id) for item in canonical.external_mappings) if canonical else (),
                    tuple((item.relationship_type.value, item.target_concept_id)
                          for item in canonical.relationships) if canonical else (),
                )
                field_name = _FAMILY_FIELD.get(concept.category)
                if field_name:
                    buckets[field_name].append(signal)
        # Authoritative imported terms add candidates to the same Evidence Frame. Lexical
        # ambiguity is retained; downstream coherence, structure and relationships decide meaning.
        for span in reference_model.resolve_text(text):
            if len(span.normalized_term) < 3:
                continue
            for canonical in span.concepts[:8]:
                field_name = _REFERENCE_FAMILY_FIELD.get(canonical.concept_family)
                if not field_name or canonical.provenance == ("MNX_RAD_REF_V1",):
                    continue
                key = (canonical.mednexus_concept_id, span.start, span.end)
                if key in seen:
                    continue
                seen.add(key)
                existing_index = next((index for index, signal in enumerate(buckets[field_name])
                                       if signal.start == span.start and signal.end == span.end), None)
                if existing_index is not None:
                    existing = buckets[field_name][existing_index]
                    buckets[field_name][existing_index] = replace(
                        existing,
                        provenance=tuple(dict.fromkeys((*existing.provenance, *canonical.provenance))),
                        external_mappings=tuple(dict.fromkeys((*existing.external_mappings,
                            *((item.source_id, item.external_id) for item in canonical.external_mappings)))),
                        relationships=tuple(dict.fromkeys((*existing.relationships,
                            *((item.relationship_type.value, item.target_concept_id) for item in canonical.relationships)))),
                    )
                    continue
                buckets[field_name].append(EvidenceSignal(
                    canonical.mednexus_concept_id, canonical.concept_family.value,
                    span.source_text, span.start, span.end, 0.75, canonical.provenance,
                    cls._context(text, span.start, span.end),
                    tuple((item.source_id, item.external_id) for item in canonical.external_mappings),
                    tuple((item.relationship_type.value, item.target_concept_id) for item in canonical.relationships),
                ))
        return DocumentEvidenceFrame(**{key: tuple(value) for key, value in buckets.items()})

    @staticmethod
    def _matches(text: str, concept: RecognitionConcept):
        matches = []
        for alias in sorted(concept.aliases, key=len, reverse=True):
            for match in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.IGNORECASE):
                matches.append((match.group(0), match.start(), match.end()))
        return matches

    @staticmethod
    def _section_concepts(sections: tuple[DetectedSection, ...]):
        from .sections import RADIOLOGY_SECTION_ALIASES, RADIOLOGY_SECTION_CONCEPTS
        by_canonical = {
            canonical: next((concept.concept_id for concept in RADIOLOGY_SECTION_CONCEPTS
                             if any(alias in concept.aliases for alias in aliases)), None)
            for canonical, aliases in RADIOLOGY_SECTION_ALIASES.items()
        }
        result: dict[str, list[tuple[str, int, int]]] = {}
        for section in sections:
            concept_id = by_canonical.get(section.canonical_name)
            if concept_id:
                result.setdefault(concept_id, []).append(
                    (section.original_heading, section.start, section.start + len(section.original_heading))
                )
        return result

    @staticmethod
    def _context(text: str, start: int, end: int) -> str:
        left = max(0, text.rfind("\n", 0, start) + 1)
        right = text.find("\n", end)
        return text[left:len(text) if right < 0 else right].strip()
