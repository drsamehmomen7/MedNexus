from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .models import SemanticRegionRole


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
    document_nature: str = "UNKNOWN"
    subdomain_or_family: str | None = None
    document_review_required: bool = False


@dataclass(frozen=True, slots=True)
class SemanticSection:
    section_id: str
    # Compatibility display label retained for existing API/frontend consumers.
    semantic_role: str
    original_heading: str
    start: int
    end: int
    confidence: float
    # Canonical frozen UNDERSTAND role and traceability are additive until the
    # compatibility display field can be retired in a later milestone.
    canonical_role: SemanticRegionRole | None = None
    qualifiers: tuple[str, ...] = ()
    evidence_concept_ids: tuple[str, ...] = ()
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TemporalContext:
    has_comparison: bool = False
    is_follow_up: bool = False
    reporting_period_hint: str | None = None


class CTStudyFamily(str, Enum):
    CT = "CT"
    CTA = "CTA"


class CTAcquisitionFeature(str, Enum):
    ANGIOGRAPHIC = "ANGIOGRAPHIC"
    MULTIPLANAR_RECONSTRUCTION = "MULTIPLANAR_RECONSTRUCTION"


class MRIStudyFamily(str, Enum):
    MRI = "MRI"
    MRA = "MRA"
    MRV = "MRV"


class MRISequenceFamily(str, Enum):
    T1_WEIGHTED = "T1_WEIGHTED"
    T2_WEIGHTED = "T2_WEIGHTED"
    FLAIR = "FLAIR"
    STIR = "STIR"
    DIFFUSION_WEIGHTED = "DIFFUSION_WEIGHTED"
    FAT_SUPPRESSED = "FAT_SUPPRESSED"


class XRaySourceType(str, Enum):
    CR = "CR"
    DX = "DX"
    XR = "XR"


class StudyLaterality(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BILATERAL = "BILATERAL"


class UltrasoundStudyExtent(str, Enum):
    COMPLETE = "COMPLETE"
    LIMITED = "LIMITED"


class UltrasoundSpecialization(str, Enum):
    GENERAL = "GENERAL"
    DOPPLER = "DOPPLER"


class VascularContext(str, Enum):
    ARTERIAL = "ARTERIAL"
    VENOUS = "VENOUS"
    MIXED = "MIXED"


@dataclass(frozen=True, slots=True)
class CTClinicalContext:
    study_family: CTStudyFamily = CTStudyFamily.CT
    acquisition_summary: tuple[CTAcquisitionFeature, ...] = ()
    # Compatibility projections retained for existing consumers.
    angiographic_context: bool = False
    multiplanar_reconstruction_present: bool = False


@dataclass(frozen=True, slots=True)
class MRIClinicalContext:
    study_family: MRIStudyFamily = MRIStudyFamily.MRI
    canonical_sequence_families: tuple[MRISequenceFamily, ...] = ()
    # Compatibility projections retained for existing consumers.
    sequence_families: tuple[str, ...] = ()
    multiplanar_acquisition_present: bool = False


@dataclass(frozen=True, slots=True)
class XRayClinicalContext:
    laterality: StudyLaterality | None = None
    source_type: XRaySourceType | None = None
    views: tuple[str, ...] = ()
    view_count: int | None = None
    view_count_qualifier: str | None = None


@dataclass(frozen=True, slots=True)
class UltrasoundClinicalContext:
    study_extent: UltrasoundStudyExtent | None = None
    specialization: UltrasoundSpecialization = UltrasoundSpecialization.GENERAL
    vascular_context: VascularContext | None = None
    measurement_bearing_present: bool | None = None
    # Compatibility projections retained for existing consumers.
    doppler_present: bool = False
    imaging_modes: tuple[str, ...] = ()


RadiologyModalityContext = (
    CTClinicalContext | MRIClinicalContext | XRayClinicalContext | UltrasoundClinicalContext
)


@dataclass(frozen=True, slots=True)
class RadiologyClinicalContext:
    modality: str | None = None
    examination: str | None = None
    body_region: str | None = None
    body_regions: tuple[str, ...] = ()
    contrast: str | None = None
    techniques: tuple[str, ...] = ()
    recognized_sections: tuple[str, ...] = ()
    authoritative_anatomy: str | None = None
    observation_narrative_present: bool = False
    # Compatibility projection retained for existing consumers.
    finding_bearing: bool = False
    modality_context: RadiologyModalityContext | None = None


DomainClinicalContext = RadiologyClinicalContext


@dataclass(frozen=True, slots=True)
class ClinicalContext:
    clinical_purpose: str | None = None
    domain_concepts: tuple[str, ...] = ()
    temporal_context: TemporalContext | None = None
    comparison_context: str | None = None
    domain_extension: DomainClinicalContext | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    # Additive compatibility surface for accepted API/frontend consumers. Values are
    # mirrored from domain_extension by DocumentContextBuilder, never recalculated.
    modality: str | None = None
    examination: str | None = None
    body_region: str | None = None
    body_regions: tuple[str, ...] = ()
    contrast: str | None = None
    techniques: tuple[str, ...] = ()


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
