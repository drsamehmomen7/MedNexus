from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from ...models import DetectedSection, SemanticRegionRole
from .evidence import DocumentEvidenceFrame, EvidenceSignal


class RadiologySemanticRole(str, Enum):
    PERFORMED_STUDY = "PERFORMED_STUDY"
    CLINICAL_INDICATION = "CLINICAL_INDICATION"
    TECHNIQUE_ACQUISITION = "TECHNIQUE_ACQUISITION"
    FINDINGS_CONTEXT = "FINDINGS_CONTEXT"
    IMPRESSION_CONTEXT = "IMPRESSION_CONTEXT"
    COMPARISON_STUDY = "COMPARISON_STUDY"
    RECOMMENDED_FUTURE_STUDY = "RECOMMENDED_FUTURE_STUDY"
    HISTORICAL_STUDY = "HISTORICAL_STUDY"
    PROFESSIONAL_ATTRIBUTION = "PROFESSIONAL_ATTRIBUTION"
    UNKNOWN_OR_UNRESOLVED = "UNKNOWN_OR_UNRESOLVED"


class RadiologyEvidenceEligibility(str, Enum):
    """How detected evidence may support the authoritative document decision."""

    CURRENT_IDENTITY_SUPPORT = "CURRENT_IDENTITY_SUPPORT"
    DOCUMENT_COMPOSITION_SUPPORT = "DOCUMENT_COMPOSITION_SUPPORT"
    CONTEXT_ONLY = "CONTEXT_ONLY"
    NON_AUTHORITATIVE = "NON_AUTHORITATIVE"


@dataclass(frozen=True, slots=True)
class SemanticRoleAdaptation:
    """Explicit compatibility projection into the frozen shared role contract."""

    canonical_role: SemanticRegionRole | None
    qualifier: str | None = None

    @property
    def authoritative(self) -> bool:
        return self.canonical_role is not None


_CANONICAL_ROLE_BY_RADIOLOGY_ROLE = {
    RadiologySemanticRole.PERFORMED_STUDY: SemanticRoleAdaptation(
        SemanticRegionRole.STUDY_OR_EVENT_IDENTITY
    ),
    RadiologySemanticRole.CLINICAL_INDICATION: SemanticRoleAdaptation(
        SemanticRegionRole.CLINICAL_OR_REPORTING_INDICATION
    ),
    RadiologySemanticRole.TECHNIQUE_ACQUISITION: SemanticRoleAdaptation(
        SemanticRegionRole.TECHNIQUE_OR_ACQUISITION
    ),
    RadiologySemanticRole.FINDINGS_CONTEXT: SemanticRoleAdaptation(
        SemanticRegionRole.OBSERVATION_NARRATIVE
    ),
    RadiologySemanticRole.IMPRESSION_CONTEXT: SemanticRoleAdaptation(
        SemanticRegionRole.CONCLUSION_OR_STATUS
    ),
    RadiologySemanticRole.COMPARISON_STUDY: SemanticRoleAdaptation(
        SemanticRegionRole.COMPARISON_OR_PRIOR_CONTEXT
    ),
    RadiologySemanticRole.HISTORICAL_STUDY: SemanticRoleAdaptation(
        SemanticRegionRole.COMPARISON_OR_PRIOR_CONTEXT, "HISTORICAL"
    ),
    RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY: SemanticRoleAdaptation(
        SemanticRegionRole.RECOMMENDATION_OR_FUTURE_ACTION
    ),
    RadiologySemanticRole.PROFESSIONAL_ATTRIBUTION: SemanticRoleAdaptation(
        SemanticRegionRole.PROFESSIONAL_OR_AUTHORITY_AUTHENTICATION
    ),
    RadiologySemanticRole.UNKNOWN_OR_UNRESOLVED: SemanticRoleAdaptation(
        None, "UNRESOLVED"
    ),
}


def adapt_radiology_semantic_role(role: RadiologySemanticRole) -> SemanticRoleAdaptation:
    if not isinstance(role, RadiologySemanticRole):
        raise TypeError("role must be a RadiologySemanticRole.")
    return _CANONICAL_ROLE_BY_RADIOLOGY_ROLE[role]


@dataclass(frozen=True, slots=True)
class RoleQualifiedEvidence:
    signal: EvidenceSignal
    role: RadiologySemanticRole
    section_id: str | None


@dataclass(frozen=True, slots=True)
class RadiologyRoleResolution:
    evidence: tuple[RoleQualifiedEvidence, ...]

    def signals(self, source: tuple[EvidenceSignal, ...], *roles: RadiologySemanticRole):
        allowed = set(roles)
        source_ids = {id(item) for item in source}
        return tuple(item.signal for item in self.evidence if id(item.signal) in source_ids and item.role in allowed)


@dataclass(frozen=True, slots=True)
class EvidenceEligibilityDecision:
    signal: EvidenceSignal
    field_name: str
    semantic_role: RadiologySemanticRole
    eligibility: RadiologyEvidenceEligibility


@dataclass(frozen=True, slots=True)
class RadiologyEvidenceEligibilityResolution:
    evidence: tuple[EvidenceEligibilityDecision, ...]

    def signals(
        self,
        eligibility: RadiologyEvidenceEligibility,
        *field_names: str,
    ) -> tuple[EvidenceSignal, ...]:
        allowed_fields = set(field_names)
        return tuple(
            item.signal for item in self.evidence
            if item.eligibility is eligibility
            and (not allowed_fields or item.field_name in allowed_fields)
        )

    def decisions_for(
        self, eligibility: RadiologyEvidenceEligibility
    ) -> tuple[EvidenceEligibilityDecision, ...]:
        return tuple(item for item in self.evidence if item.eligibility is eligibility)


class RadiologyEvidenceEligibilityResolver:
    """Central role-aware boundary between detection and confidence support."""

    _CURRENT_ROLES = {
        RadiologySemanticRole.PERFORMED_STUDY,
        RadiologySemanticRole.TECHNIQUE_ACQUISITION,
    }
    _CONTEXT_ONLY_ROLES = {
        RadiologySemanticRole.COMPARISON_STUDY,
        RadiologySemanticRole.HISTORICAL_STUDY,
        RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY,
    }
    _CURRENT_IDENTITY_FIELDS = {
        "modality_signals", "technique_signals", "acquisition_signals",
        "anatomy_signals", "procedure_signals", "contrast_signals",
        "laterality_signals", "study_extent_signals", "view_signals",
        "view_count_signals",
    }
    _DOCUMENT_COMPOSITION_FIELDS = {
        "domain_signals", "structure_signals", "observation_signals",
        "professional_role_signals",
    }

    @classmethod
    def resolve(
        cls,
        frame: DocumentEvidenceFrame,
        roles: RadiologyRoleResolution,
    ) -> RadiologyEvidenceEligibilityResolution:
        role_by_signal = {id(item.signal): item.role for item in roles.evidence}
        decisions = []
        for field_name in frame.__dataclass_fields__:
            for signal in getattr(frame, field_name):
                role = role_by_signal.get(
                    id(signal), RadiologySemanticRole.UNKNOWN_OR_UNRESOLVED
                )
                decisions.append(EvidenceEligibilityDecision(
                    signal,
                    field_name,
                    role,
                    cls._eligibility(field_name, role),
                ))
        return RadiologyEvidenceEligibilityResolution(tuple(decisions))

    @classmethod
    def _eligibility(
        cls, field_name: str, role: RadiologySemanticRole
    ) -> RadiologyEvidenceEligibility:
        if role is RadiologySemanticRole.UNKNOWN_OR_UNRESOLVED:
            return RadiologyEvidenceEligibility.NON_AUTHORITATIVE
        if role in cls._CONTEXT_ONLY_ROLES:
            return RadiologyEvidenceEligibility.CONTEXT_ONLY
        if field_name in cls._DOCUMENT_COMPOSITION_FIELDS:
            return RadiologyEvidenceEligibility.DOCUMENT_COMPOSITION_SUPPORT
        if role in cls._CURRENT_ROLES and field_name in cls._CURRENT_IDENTITY_FIELDS:
            return RadiologyEvidenceEligibility.CURRENT_IDENTITY_SUPPORT
        return RadiologyEvidenceEligibility.CONTEXT_ONLY


class RadiologySemanticRoleResolver:
    """Assign document-composition roles without changing raw evidence or extracting facts."""

    _RECOMMENDATION = re.compile(
        r"\b(?:recommend(?:ed|ation)?|consider|suggest(?:ed|ion)?|advise[ds]?|follow[- ]?up\s+(?:with|by|using))\b",
        re.IGNORECASE,
    )
    _HISTORICAL = re.compile(
        r"\b(?:prior|previous|historical|history\s+of|formerly|earlier)\b",
        re.IGNORECASE,
    )
    _PERFORMED = re.compile(
        r"\b(?:performed|obtained|acquired|completed|exam(?:ination)?|study|images?|views?|technique|using)\b",
        re.IGNORECASE,
    )
    _CURRENT_SECTIONS = {"procedure_information", "radiology_examination", "technique"}
    _INDICATION_SECTIONS = {"clinical_history", "clinical_information", "follow_up"}
    _CURRENT_EVIDENCE_FAMILIES = {
        "MODALITY", "IMAGING_MODALITY", "MODALITY_SUBTYPE", "IMAGING_PROCEDURE",
        "ANATOMY", "BODY_REGION", "IMAGING_FOCUS", "CONTRAST", "PHARMACEUTICAL",
        "VIEW_COUNT",
    }

    @classmethod
    def resolve(
        cls, text: str, sections: tuple[DetectedSection, ...], frame: DocumentEvidenceFrame
    ) -> RadiologyRoleResolution:
        first_section_start = min((item.start for item in sections), default=len(text))
        resolved = []
        for signal in frame.all_signals:
            section = next((item for item in sections if item.start <= signal.start < item.end), None)
            section_id = section.canonical_name if section else None
            clause = cls._clause(text, signal.start, signal.end)
            role = cls._role(signal, section_id, clause, first_section_start)
            resolved.append(RoleQualifiedEvidence(signal, role, section_id))
        return RadiologyRoleResolution(tuple(resolved))

    @classmethod
    def _role(
        cls, signal: EvidenceSignal, section_id: str | None, clause: str, first_section_start: int
    ) -> RadiologySemanticRole:
        if cls._RECOMMENDATION.search(clause) or section_id == "recommendation":
            return RadiologySemanticRole.RECOMMENDED_FUTURE_STUDY
        if section_id == "comparison":
            return RadiologySemanticRole.COMPARISON_STUDY
        if cls._HISTORICAL.search(clause):
            return RadiologySemanticRole.HISTORICAL_STUDY
        if signal.concept_family in {"AUTHOR_ROLE", "PROFESSIONAL_ROLE"}:
            return RadiologySemanticRole.PROFESSIONAL_ATTRIBUTION
        if signal.concept_family in {"IMAGING_TECHNIQUE", "ACQUISITION"} \
                and section_id not in {"findings", "impression", "comparison"}:
            return RadiologySemanticRole.TECHNIQUE_ACQUISITION
        if signal.concept_family == "PROCEDURE_ATTRIBUTE" \
                and section_id not in {"findings", "impression", "comparison"}:
            return RadiologySemanticRole.TECHNIQUE_ACQUISITION
        if signal.concept_family == "VIEW_COUNT" \
                and section_id not in {"findings", "impression", "comparison"}:
            return RadiologySemanticRole.TECHNIQUE_ACQUISITION
        if signal.concept_family in cls._CURRENT_EVIDENCE_FAMILIES \
                and cls._title_like(clause):
            return RadiologySemanticRole.PERFORMED_STUDY
        if section_id not in {"findings", "impression", "comparison"} \
                and signal.concept_family in cls._CURRENT_EVIDENCE_FAMILIES \
                and cls._PERFORMED.search(clause):
            return RadiologySemanticRole.PERFORMED_STUDY
        if section_id in cls._CURRENT_SECTIONS:
            return (
                RadiologySemanticRole.TECHNIQUE_ACQUISITION
                if section_id == "technique"
                else RadiologySemanticRole.PERFORMED_STUDY
            )
        if section_id in cls._INDICATION_SECTIONS:
            return RadiologySemanticRole.CLINICAL_INDICATION
        if section_id == "findings":
            return RadiologySemanticRole.FINDINGS_CONTEXT
        if section_id == "impression":
            return RadiologySemanticRole.IMPRESSION_CONTEXT
        if signal.start < first_section_start or cls._title_like(clause):
            return RadiologySemanticRole.PERFORMED_STUDY
        if cls._PERFORMED.search(clause):
            return RadiologySemanticRole.TECHNIQUE_ACQUISITION
        if section_id == "comment":
            return RadiologySemanticRole.FINDINGS_CONTEXT
        return RadiologySemanticRole.UNKNOWN_OR_UNRESOLVED

    @staticmethod
    def _clause(text: str, start: int, end: int) -> str:
        left = max(text.rfind(mark, 0, start) for mark in ("\n", ".", ";", "?", "!")) + 1
        right_candidates = [position for mark in ("\n", ".", ";", "?", "!")
                            if (position := text.find(mark, end)) >= 0]
        right = min(right_candidates) if right_candidates else len(text)
        return text[left:right].strip()

    @staticmethod
    def _title_like(clause: str) -> bool:
        letters = [item for item in clause if item.isalpha()]
        return bool(letters) and len(clause.split()) <= 14 and clause == clause.upper()
