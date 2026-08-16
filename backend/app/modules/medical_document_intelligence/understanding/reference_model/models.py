from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DistributionPolicy(str, Enum):
    OPEN_DISTRIBUTABLE = "OPEN_DISTRIBUTABLE"
    EXTERNAL_DOWNLOAD_REQUIRED = "EXTERNAL_DOWNLOAD_REQUIRED"
    LICENSE_RESTRICTED = "LICENSE_RESTRICTED"
    OPTIONAL_REFERENCE = "OPTIONAL_REFERENCE"
    LOCAL_CURATED_DERIVATIVE = "LOCAL_CURATED_DERIVATIVE"


class SourceTrustLevel(str, Enum):
    AUTHORITATIVE_STANDARD = "AUTHORITATIVE_STANDARD"
    AUTHORITATIVE_ONTOLOGY = "AUTHORITATIVE_ONTOLOGY"
    MEDNEXUS_CURATED = "MEDNEXUS_CURATED"
    LEGACY_COMPATIBILITY = "LEGACY_COMPATIBILITY"


class ConceptFamily(str, Enum):
    DOCUMENT_REPORT = "DOCUMENT_REPORT"
    IMAGING_MODALITY = "IMAGING_MODALITY"
    BODY_REGION = "BODY_REGION"
    IMAGING_PROCEDURE = "IMAGING_PROCEDURE"
    IMAGING_TECHNIQUE = "IMAGING_TECHNIQUE"
    ACQUISITION = "ACQUISITION"
    CONTRAST = "CONTRAST"
    CLINICAL_PURPOSE = "CLINICAL_PURPOSE"
    RADIOLOGY_STRUCTURE = "RADIOLOGY_STRUCTURE"
    PROFESSIONAL_ROLE = "PROFESSIONAL_ROLE"
    REPORTING_FRAMEWORK = "REPORTING_FRAMEWORK"
    DOMAIN_SIGNAL = "DOMAIN_SIGNAL"
    MODALITY_SUBTYPE = "MODALITY_SUBTYPE"
    IMAGING_FOCUS = "IMAGING_FOCUS"
    LATERALITY = "LATERALITY"
    VIEW = "VIEW"
    TIMING = "TIMING"
    PHARMACEUTICAL = "PHARMACEUTICAL"
    ROUTE = "ROUTE"
    GUIDANCE = "GUIDANCE"
    MANEUVER = "MANEUVER"
    REASON_FOR_EXAM = "REASON_FOR_EXAM"
    PROCEDURE_ATTRIBUTE = "PROCEDURE_ATTRIBUTE"
    CLINICAL_FINDING = "CLINICAL_FINDING"
    IMAGING_OBSERVATION = "IMAGING_OBSERVATION"
    REPORT_COMPONENT = "REPORT_COMPONENT"
    PROPERTY = "PROPERTY"
    TEMPORAL_ENTITY = "TEMPORAL_ENTITY"


class RelationshipType(str, Enum):
    IS_A = "IS_A"
    USED_WITH = "USED_WITH"
    SUPPORTS = "SUPPORTS"
    CAN_COMPOSE = "CAN_COMPOSE"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    PART_OF = "PART_OF"
    MEMBER_OF = "MEMBER_OF"
    MAPS_TO = "MAPS_TO"


@dataclass(frozen=True, slots=True)
class ReferenceSource:
    source_id: str
    source_name: str
    authority: str
    domain: str
    reference_family: str
    version: str
    release_date: str | None
    license_name: str
    license_status: str
    distribution_policy: DistributionPolicy
    source_location: str
    retrieved_at: str | None
    last_verified_at: str
    checksum: str | None
    enabled: bool
    notes: str | None = None
    trust_level: SourceTrustLevel = SourceTrustLevel.AUTHORITATIVE_STANDARD


@dataclass(frozen=True, slots=True)
class ExternalMapping:
    source_id: str
    external_id: str
    display: str | None = None
    mapping_type: str = "EQUIVALENT"


@dataclass(frozen=True, slots=True)
class ConceptRelationship:
    relationship_type: RelationshipType
    target_concept_id: str
    source_ids: tuple[str, ...]
    source_relationship: str | None = None
    sequence_order: str | None = None
    target_external_id: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalConcept:
    mednexus_concept_id: str
    canonical_name: str
    concept_family: ConceptFamily
    domain: str
    preferred_terms: tuple[str, ...]
    synonyms: tuple[str, ...] = ()
    languages: tuple[str, ...] = ("en",)
    external_mappings: tuple[ExternalMapping, ...] = ()
    relationships: tuple[ConceptRelationship, ...] = ()
    provenance: tuple[str, ...] = ()
    status: str = "ACTIVE"
    attributes: tuple[tuple[str, str], ...] = ()

    @property
    def terms(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.preferred_terms, *self.synonyms)))


@dataclass(frozen=True, slots=True)
class ResolvedConcept:
    source_text: str
    concept: CanonicalConcept
    normalized_term: str


@dataclass(frozen=True, slots=True)
class ResolvedSpan:
    source_text: str
    start: int
    end: int
    concepts: tuple[CanonicalConcept, ...]
    normalized_term: str
