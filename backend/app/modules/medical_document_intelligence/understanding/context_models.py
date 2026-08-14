from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentDescriptor:
    document_id: str
    source_format: str
    primary_language: str
    source_name: str | None = None
    media_type: str | None = None
    ingestion_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentIdentityContext:
    healthcare_domain: str
    document_type: str
    document_subtype: str | None
    confidence: float
    confidence_band: str


@dataclass(frozen=True, slots=True)
class SemanticSection:
    section_id: str
    semantic_role: str
    original_heading: str
    start: int
    end: int
    confidence: float


@dataclass(frozen=True, slots=True)
class ClinicalContext:
    modality: str | None = None
    examination: str | None = None
    body_region: str | None = None
    contrast: str | None = None
    domain_concepts: tuple[str, ...] = ()
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PrivacyRegion:
    role: str
    section_id: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class PrivacyContext:
    regions: tuple[PrivacyRegion, ...] = ()


@dataclass(frozen=True, slots=True)
class ProcessingContext:
    privacy_profile: str
    extraction_profile: str
    terminology_profile: str
    recommended_capabilities: tuple[str, ...]
    manual_review_required: bool


@dataclass(frozen=True, slots=True)
class ContextProvenance:
    knowledge_layer_version: str
    concept_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MedNexusDocumentContext:
    document: DocumentDescriptor
    identity: DocumentIdentityContext
    structure: tuple[SemanticSection, ...]
    clinical_context: ClinicalContext
    privacy_context: PrivacyContext
    processing_context: ProcessingContext
    provenance: ContextProvenance

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
