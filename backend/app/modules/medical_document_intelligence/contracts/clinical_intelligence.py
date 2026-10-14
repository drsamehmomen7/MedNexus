"""Versioned, descriptive questions over exact reviewed Collection members."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


InsightType = Literal["CO_DOCUMENTATION", "STRATIFIED_DOCUMENTATION", "FINDING_CONTEXT", "COVERAGE_QUALITY"]
ReferenceRole = Literal["EXAM_PROFILE_REFERENCE", "CLINICAL_RELATIONSHIP_REFERENCE", "MRJ_POLICY"]
RelationshipReferenceStatus = Literal["VERIFIED", "PENDING_VERIFICATION"]


@dataclass(frozen=True, slots=True)
class ClinicalInsightReference:
    organization: str
    title: str
    url: str
    version_or_date: str | None
    verification: str
    rationale: str
    role: ReferenceRole

    def __post_init__(self) -> None:
        if self.role not in {"EXAM_PROFILE_REFERENCE", "CLINICAL_RELATIONSHIP_REFERENCE", "MRJ_POLICY"}:
            raise ValueError("Unknown Clinical Intelligence reference role.")


@dataclass(frozen=True, slots=True)
class ClinicalInsightVariable:
    concept_id: str
    reviewed_concept_terms: tuple[str, ...]
    anatomy_terms: tuple[str, ...] = ()
    require_laterality: bool = False
    present_assertion: str = "PRESENT"
    absent_assertion: str = "ABSENT_NEGATED"
    indeterminate_assertion: str = "UNCERTAIN"
    undocumented_state: str = "NOT_DOCUMENTED"


@dataclass(frozen=True, slots=True)
class ClinicalInsightSupport:
    policy_version: str
    minimum_eligible_n: int
    minimum_group_n: int
    minimum_event_support: int
    policy_role: Literal["MRJ_POLICY"] = "MRJ_POLICY"
    policy_label: str = "MRJ V1 descriptive support policy"


@dataclass(frozen=True, slots=True)
class ClinicalInsightDefinition:
    insight_id: str
    version: str
    title: str
    question: str
    insight_type: InsightType
    rationale: str
    exposure: ClinicalInsightVariable | None
    outcome: ClinicalInsightVariable | None
    coverage_element_id: str | None
    compatible_scopes: tuple[str, ...]
    explicit_absence_comparison: bool
    same_laterality: bool
    support: ClinicalInsightSupport
    exam_profile_reference: ClinicalInsightReference
    clinical_relationship_reference: ClinicalInsightReference | None = None
    relationship_reference_status: RelationshipReferenceStatus = "PENDING_VERIFICATION"
    stratifier: ClinicalInsightVariable | None = None
    allowed_wording_class: str = "DESCRIPTIVE_REPORT_DOCUMENTATION"
    analysis_level: str = "REPORT"
    insufficient_wording: str = "Not enough eligible reviewed reports under the current MRJ support policy."
    no_pattern_wording: str = "No clear descriptive difference was observed in eligible reports in this collection."

    def __post_init__(self) -> None:
        if self.exam_profile_reference.role != "EXAM_PROFILE_REFERENCE":
            raise ValueError("An exam/profile reference cannot be a clinical relationship reference.")
        if self.support.policy_role != "MRJ_POLICY":
            raise ValueError("Insight support thresholds must be identified as MRJ policy.")
        if self.relationship_reference_status == "VERIFIED":
            reference = self.clinical_relationship_reference
            if (reference is None or reference.role != "CLINICAL_RELATIONSHIP_REFERENCE"
                    or reference.verification != "VERIFIED"):
                raise ValueError("A verified relationship requires its own verified relationship reference.")
        elif self.relationship_reference_status == "PENDING_VERIFICATION":
            if self.clinical_relationship_reference is not None:
                raise ValueError("Pending relationships cannot carry an unverified citation.")
        else:
            raise ValueError("Unknown relationship reference status.")
        if self.insight_type == "COVERAGE_QUALITY" and self.clinical_relationship_reference is not None:
            raise ValueError("Coverage-quality questions do not require a disease-relationship citation.")


@dataclass(frozen=True, slots=True)
class ClinicalIntelligenceProfile:
    intelligence_profile_id: str
    version: str
    compatible_clinical_profile_id: str
    compatible_clinical_profile_versions: tuple[str, ...]
    lifecycle: str
    definitions: tuple[ClinicalInsightDefinition, ...]


class ClinicalIntelligenceProfileRegistry:
    def __init__(self, profiles: tuple[ClinicalIntelligenceProfile, ...],
                 active_versions: dict[str, str]):
        self._profiles = {(p.intelligence_profile_id, p.version): p for p in profiles}
        self._active_versions = dict(active_versions)

    def get(self, intelligence_profile_id: str, version: str) -> ClinicalIntelligenceProfile | None:
        return self._profiles.get((intelligence_profile_id, version))

    def resolve(self, clinical_profile_id: str, clinical_profile_version: str) -> ClinicalIntelligenceProfile | None:
        for (identifier, version), profile in self._profiles.items():
            if (self._active_versions.get(identifier) == version
                    and profile.compatible_clinical_profile_id == clinical_profile_id
                    and clinical_profile_version in profile.compatible_clinical_profile_versions):
                return profile
        return None
