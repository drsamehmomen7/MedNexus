from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .knowledge.radiology import RadiologyUnderstandingDecision


class DocumentDomain(str, Enum):
    RADIOLOGY = "RADIOLOGY"
    PATHOLOGY = "PATHOLOGY"
    LABORATORY = "LABORATORY"
    EMERGENCY = "EMERGENCY"
    ADMISSION_DISCHARGE = "ADMISSION_DISCHARGE"
    PUBLIC_HEALTH = "PUBLIC_HEALTH"
    UNKNOWN = "UNKNOWN"


class DocumentType(str, Enum):
    RADIOLOGY_REPORT = "RADIOLOGY_REPORT"
    PATHOLOGY_REPORT = "PATHOLOGY_REPORT"
    LABORATORY_REPORT = "LABORATORY_REPORT"
    EMERGENCY_REPORT = "EMERGENCY_REPORT"
    ADMISSION_NOTE = "ADMISSION_NOTE"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    PUBLIC_HEALTH_DOCUMENT = "PUBLIC_HEALTH_DOCUMENT"
    UNKNOWN = "UNKNOWN"


class RadiologySubdomain(str, Enum):
    """Frozen UNDERSTAND v1 Radiology subdomain contract."""

    CT = "CT"
    MRI = "MRI"
    X_RAY = "X_RAY"
    ULTRASOUND = "ULTRASOUND"
    MAMMOGRAPHY = "MAMMOGRAPHY"
    NUCLEAR_MEDICINE = "NUCLEAR_MEDICINE"
    FLUOROSCOPY = "FLUOROSCOPY"
    OTHER = "OTHER"


class DocumentSubtype(str, Enum):
    """Legacy compatibility subtype; canonical Radiology uses RadiologySubdomain."""

    X_RAY = "X_RAY"
    CT = "CT"
    MRI = "MRI"
    ULTRASOUND = "ULTRASOUND"
    DOPPLER = "DOPPLER"
    MAMMOGRAPHY = "MAMMOGRAPHY"
    NUCLEAR_MEDICINE = "NUCLEAR_MEDICINE"
    UNKNOWN = "UNKNOWN"


def canonical_radiology_subdomain_from_legacy(
    domain: DocumentDomain,
    subtype: DocumentSubtype,
) -> RadiologySubdomain | None:
    """Project an existing decision into the canonical Radiology contract.

    UNKNOWN is context-sensitive: it becomes OTHER only when the domain is
    already known to be Radiology. An unknown domain has no Radiology subdomain.
    """

    if not isinstance(domain, DocumentDomain):
        raise TypeError("domain must be a DocumentDomain.")
    if not isinstance(subtype, DocumentSubtype):
        raise TypeError("subtype must be a DocumentSubtype.")
    if domain is not DocumentDomain.RADIOLOGY:
        return None
    if subtype is DocumentSubtype.UNKNOWN:
        return RadiologySubdomain.OTHER
    return {
        DocumentSubtype.CT: RadiologySubdomain.CT,
        DocumentSubtype.MRI: RadiologySubdomain.MRI,
        DocumentSubtype.X_RAY: RadiologySubdomain.X_RAY,
        DocumentSubtype.ULTRASOUND: RadiologySubdomain.ULTRASOUND,
        DocumentSubtype.DOPPLER: RadiologySubdomain.ULTRASOUND,
        DocumentSubtype.MAMMOGRAPHY: RadiologySubdomain.MAMMOGRAPHY,
        DocumentSubtype.NUCLEAR_MEDICINE: RadiologySubdomain.NUCLEAR_MEDICINE,
    }[subtype]


class DocumentLanguage(str, Enum):
    ENGLISH = "ENGLISH"
    ARABIC = "ARABIC"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class ConfidenceBand(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class DocumentNature(str, Enum):
    COMPLETED_REPORT = "COMPLETED_REPORT"
    STRUCTURED_TEMPLATE = "STRUCTURED_TEMPLATE"
    PARTIAL_REPORT = "PARTIAL_REPORT"
    UNKNOWN = "UNKNOWN"


class SemanticRegionRole(str, Enum):
    """Shared frozen semantic-region vocabulary for UNDERSTAND output."""

    STUDY_OR_EVENT_IDENTITY = "STUDY_OR_EVENT_IDENTITY"
    CLINICAL_OR_REPORTING_INDICATION = "CLINICAL_OR_REPORTING_INDICATION"
    TECHNIQUE_OR_ACQUISITION = "TECHNIQUE_OR_ACQUISITION"
    OBSERVATION_NARRATIVE = "OBSERVATION_NARRATIVE"
    CONCLUSION_OR_STATUS = "CONCLUSION_OR_STATUS"
    COMPARISON_OR_PRIOR_CONTEXT = "COMPARISON_OR_PRIOR_CONTEXT"
    RECOMMENDATION_OR_FUTURE_ACTION = "RECOMMENDATION_OR_FUTURE_ACTION"
    PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION = "PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION"


@dataclass(frozen=True, slots=True)
class DetectedSection:
    canonical_name: str
    original_heading: str
    start: int
    end: int
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class ClassificationEvidence:
    candidate: DocumentType
    signal: str
    category: str
    weight: float
    reference: str | None = None
    concept_id: str | None = None
    reference_systems: tuple[str, ...] = ()
    external_mappings: tuple[tuple[str, str], ...] = ()
    relationships: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class RecognitionExplanation:
    code: str
    message: str
    category: str
    concept_id: str | None = None
    semantic_role: str | None = None


@dataclass(frozen=True, slots=True)
class UnderstandingRoute:
    """Symbolic downstream recommendation; it does not execute a capability."""

    privacy_profile_candidate: str
    extraction_profile: str
    terminology_profile: str
    processing_capabilities: tuple[str, ...]
    manual_review_required: bool


@dataclass(frozen=True, slots=True)
class DocumentUnderstandingResult:
    domain: DocumentDomain
    document_type: DocumentType
    document_subtype: DocumentSubtype
    language: DocumentLanguage
    sections: tuple[DetectedSection, ...]
    confidence: float
    confidence_band: ConfidenceBand
    evidence: tuple[ClassificationEvidence, ...]
    routing: UnderstandingRoute
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    document_nature: DocumentNature = DocumentNature.UNKNOWN
    recognition_explanations: tuple[RecognitionExplanation, ...] = ()
    radiology_decision: RadiologyUnderstandingDecision | None = field(
        default=None, repr=False, compare=False
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            item.name: _serialize(getattr(self, item.name))
            for item in fields(self)
            if item.name != "radiology_decision"
        }


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: _serialize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value
