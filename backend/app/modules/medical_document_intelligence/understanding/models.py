from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


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


class DocumentSubtype(str, Enum):
    X_RAY = "X_RAY"
    CT = "CT"
    MRI = "MRI"
    ULTRASOUND = "ULTRASOUND"
    MAMMOGRAPHY = "MAMMOGRAPHY"
    NUCLEAR_MEDICINE = "NUCLEAR_MEDICINE"
    UNKNOWN = "UNKNOWN"


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

    def to_dict(self) -> dict[str, Any]:
        return _serialize(asdict(self))


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value
