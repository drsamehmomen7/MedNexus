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
    # Canonical UNDERSTAND v1 identity fields. ``healthcare_domain`` and
    # ``document_subtype`` remain as compatibility projections.
    domain: str | None = None
    language: str = "UNKNOWN"


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


class MammographyStudyPurpose(str, Enum):
    SCREENING = "SCREENING"
    DIAGNOSTIC = "DIAGNOSTIC"


class MammographyAcquisitionContext(str, Enum):
    STANDARD_VIEWS = "STANDARD_VIEWS"
    TOMOSYNTHESIS = "TOMOSYNTHESIS"


class NuclearMedicineStudyFamily(str, Enum):
    PLANAR = "PLANAR"
    SPECT = "SPECT"
    PET = "PET"
    SPECT_CT = "SPECT_CT"
    PET_CT = "PET_CT"
    OTHER = "OTHER"


class FluoroscopyStudyFamily(str, Enum):
    GENERAL_DIAGNOSTIC = "GENERAL_DIAGNOSTIC"
    CONTRAST_STUDY = "CONTRAST_STUDY"
    DYNAMIC_FUNCTIONAL_STUDY = "DYNAMIC_FUNCTIONAL_STUDY"


class RadiologyOtherReason(str, Enum):
    UNSUPPORTED_FAMILY = "UNSUPPORTED_FAMILY"
    CONFLICTING_CURRENT_FAMILY = "CONFLICTING_CURRENT_FAMILY"
    INSUFFICIENT_FAMILY_EVIDENCE = "INSUFFICIENT_FAMILY_EVIDENCE"
    INTERVENTIONAL_PROCEDURE = "INTERVENTIONAL_PROCEDURE"


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


@dataclass(frozen=True, slots=True)
class MammographyClinicalContext:
    study_purpose: MammographyStudyPurpose | None = None
    laterality: StudyLaterality | None = None
    acquisition_context: tuple[MammographyAcquisitionContext, ...] = ()
    birads_assessment_present: bool | None = None


@dataclass(frozen=True, slots=True)
class NuclearMedicineClinicalContext:
    study_family: NuclearMedicineStudyFamily = NuclearMedicineStudyFamily.OTHER
    radiopharmaceutical_context_present: bool | None = None
    quantitative_uptake_context_present: bool | None = None


@dataclass(frozen=True, slots=True)
class FluoroscopyClinicalContext:
    study_family: FluoroscopyStudyFamily = FluoroscopyStudyFamily.GENERAL_DIAGNOSTIC
    body_system: str | None = None
    contrast_study_present: bool | None = None
    dynamic_functional_present: bool | None = None


@dataclass(frozen=True, slots=True)
class OtherRadiologyClinicalContext:
    resolution_reason: RadiologyOtherReason
    family_specific_context_available: bool = False


RadiologyModalityContext = (
    CTClinicalContext | MRIClinicalContext | XRayClinicalContext | UltrasoundClinicalContext
    | MammographyClinicalContext | NuclearMedicineClinicalContext
    | FluoroscopyClinicalContext | OtherRadiologyClinicalContext
)


@dataclass(frozen=True, slots=True)
class CTRadiologyLightContext:
    subdomain: str
    body_region: str | None = None
    contrast: str | None = None
    study_family: CTStudyFamily = CTStudyFamily.CT
    acquisition_summary: tuple[CTAcquisitionFeature, ...] = ()


@dataclass(frozen=True, slots=True)
class MRIRadiologyLightContext:
    subdomain: str
    body_region: str | None = None
    contrast: str | None = None
    study_family: MRIStudyFamily = MRIStudyFamily.MRI
    sequence_context: tuple[MRISequenceFamily, ...] = ()


@dataclass(frozen=True, slots=True)
class XRayRadiologyLightContext:
    subdomain: str
    body_region: str | None = None
    laterality: StudyLaterality | None = None
    views: tuple[str, ...] = ()
    view_count: int | None = None
    view_count_qualifier: str | None = None
    source_type: XRaySourceType | None = None


@dataclass(frozen=True, slots=True)
class UltrasoundRadiologyLightContext:
    subdomain: str
    body_region: str | None = None
    study_extent: UltrasoundStudyExtent | None = None
    vascular_context: VascularContext | None = None
    specialization: UltrasoundSpecialization = UltrasoundSpecialization.GENERAL
    measurement_bearing_present: bool | None = None


@dataclass(frozen=True, slots=True)
class MammographyRadiologyLightContext:
    subdomain: str
    study_purpose: MammographyStudyPurpose | None = None
    laterality: StudyLaterality | None = None
    acquisition_context: tuple[MammographyAcquisitionContext, ...] = ()
    birads_assessment_present: bool | None = None


@dataclass(frozen=True, slots=True)
class NuclearMedicineRadiologyLightContext:
    subdomain: str
    study_family: NuclearMedicineStudyFamily = NuclearMedicineStudyFamily.OTHER
    body_region: str | None = None
    radiopharmaceutical_context_present: bool | None = None
    quantitative_uptake_context_present: bool | None = None


@dataclass(frozen=True, slots=True)
class FluoroscopyRadiologyLightContext:
    subdomain: str
    study_family: FluoroscopyStudyFamily = FluoroscopyStudyFamily.GENERAL_DIAGNOSTIC
    body_system: str | None = None
    contrast_study_present: bool | None = None
    dynamic_functional_present: bool | None = None


@dataclass(frozen=True, slots=True)
class OtherRadiologyLightContext:
    subdomain: str
    review_reason: RadiologyOtherReason


RadiologyLightContext = (
    CTRadiologyLightContext | MRIRadiologyLightContext | XRayRadiologyLightContext
    | UltrasoundRadiologyLightContext | MammographyRadiologyLightContext
    | NuclearMedicineRadiologyLightContext | FluoroscopyRadiologyLightContext
    | OtherRadiologyLightContext
)


@dataclass(frozen=True, slots=True)
class CanonicalLightContext:
    domain_type: str | None = None
    family_context: RadiologyLightContext | None = None


@dataclass(frozen=True, slots=True)
class CanonicalSemanticRegion:
    region_id: str
    role: SemanticRegionRole | None
    start: int
    end: int
    confidence: float
    provenance: tuple[str, ...] = ()
    qualifiers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticRelationship:
    source_region_id: str
    relationship: str
    target_region_id: str
    provenance: tuple[str, ...] = ()


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
    protect_ready: bool = False
    extract_ready: bool = False
    document_review_required: bool = False


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
    light_context: CanonicalLightContext
    semantic_regions: tuple[CanonicalSemanticRegion, ...]
    semantic_relationships: tuple[SemanticRelationship, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
