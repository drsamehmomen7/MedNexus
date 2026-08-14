from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..models import DocumentDomain, DocumentType


class RecognitionConceptCategory(str, Enum):
    DOCUMENT_IDENTITY = "DOCUMENT_IDENTITY"
    SERVICE_CONTEXT = "SERVICE_CONTEXT"
    SECTION = "SECTION"
    MODALITY = "MODALITY"
    PROCEDURE = "PROCEDURE"
    AUTHOR_ROLE = "AUTHOR_ROLE"
    STRUCTURAL_SIGNAL = "STRUCTURAL_SIGNAL"


@dataclass(frozen=True, slots=True)
class RecognitionConcept:
    concept_id: str
    canonical_name: str
    category: RecognitionConceptCategory
    domain: DocumentDomain
    canonical_en: str | None = None
    canonical_ar: str | None = None
    aliases_en: tuple[str, ...] = ()
    aliases_ar: tuple[str, ...] = ()
    evidence_strength: float = 1.0
    allowed_contexts: tuple[str, ...] = ()
    external_references: tuple[str, ...] = ()
    notes: str | None = None

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(filter(None, (
            self.canonical_en, self.canonical_ar, *self.aliases_en, *self.aliases_ar
        ))))


@dataclass(frozen=True, slots=True)
class RecognitionSignal:
    phrase: str
    weight: float
    category: str
    concept_id: str | None = None
    reference_systems: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SignatureAssessment:
    satisfied: bool
    identity_matches: tuple[str, ...]
    structural_matches: tuple[str, ...]
    supporting_matches: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RecognitionSignature:
    signature_id: str
    domain: DocumentDomain
    document_type: DocumentType
    strong_identity_concepts: tuple[str, ...]
    structural_concepts: tuple[str, ...]
    supporting_concepts: tuple[str, ...]
    conflict_document_types: tuple[DocumentType, ...]

    def assess(self, concept_ids: set[str]) -> SignatureAssessment:
        identity = tuple(item for item in self.strong_identity_concepts if item in concept_ids)
        structural = tuple(item for item in self.structural_concepts if item in concept_ids)
        supporting = tuple(item for item in self.supporting_concepts if item in concept_ids)
        satisfied = bool(identity and (structural or supporting)) or (
            len(structural) >= 3 and bool(supporting)
        )
        return SignatureAssessment(satisfied, identity, structural, supporting)
