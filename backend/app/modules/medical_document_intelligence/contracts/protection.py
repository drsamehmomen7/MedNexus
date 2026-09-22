from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)
from backend.app.modules.medical_document_intelligence.policies.policy_engine import (
    PolicyEngine,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
    get_policy_definition,
)


class AnalyticFieldState(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    RESTRICTED = "RESTRICTED"


@dataclass(frozen=True, slots=True)
class PatientAnalyticField:
    state: AnalyticFieldState
    value: Any | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "value": self.value,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class PatientAnalyticContext:
    """Policy-safe patient context owned by PROTECT.

    R1 establishes the contract without pretending that derivation,
    generalization, date shifting, or pseudonymization is implemented.
    """

    pseudonymous_subject_key: PatientAnalyticField
    age: PatientAnalyticField
    age_band: PatientAnalyticField
    sex: PatientAnalyticField
    safe_time_context: PatientAnalyticField
    generalized_geography: PatientAnalyticField
    facility_context: PatientAnalyticField

    @classmethod
    def unavailable(cls) -> "PatientAnalyticContext":
        unavailable = PatientAnalyticField(AnalyticFieldState.NOT_AVAILABLE)
        return cls(
            pseudonymous_subject_key=unavailable,
            age=unavailable,
            age_band=unavailable,
            sex=unavailable,
            safe_time_context=unavailable,
            generalized_geography=unavailable,
            facility_context=unavailable,
        )

    @property
    def populated_fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for name, value in (
                ("pseudonymous_subject_key", self.pseudonymous_subject_key),
                ("age", self.age),
                ("age_band", self.age_band),
                ("sex", self.sex),
                ("safe_time_context", self.safe_time_context),
                ("generalized_geography", self.generalized_geography),
                ("facility_context", self.facility_context),
            )
            if value.state is AnalyticFieldState.KNOWN
        )

    def to_dict(self) -> dict[str, Any]:
        values = {
            name: value.to_dict()
            for name, value in (
                ("pseudonymous_subject_key", self.pseudonymous_subject_key),
                ("age", self.age),
                ("age_band", self.age_band),
                ("sex", self.sex),
                ("safe_time_context", self.safe_time_context),
                ("generalized_geography", self.generalized_geography),
                ("facility_context", self.facility_context),
            )
        }
        return {
            "fields": values,
            "populated_fields": list(self.populated_fields),
        }


@dataclass(frozen=True, slots=True)
class ProtectedDocument:
    report_id: str
    protected_text: str
    output_version: str
    selected_policy_id: str
    selected_policy_version: str | None
    transformations_applied: tuple[str, ...]
    warnings: tuple[str, ...]
    integrity_sha256: str
    artifact: "ProtectedArtifact | None" = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifact"] = self.artifact.to_dict() if self.artifact else None
        return payload


@dataclass(frozen=True, slots=True)
class ProtectedArtifact:
    filename: str
    media_type: str
    availability: bool
    page_count: int
    generated_at: str
    integrity_sha256: str
    provenance: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "media_type": self.media_type,
            "availability": self.availability,
            "page_count": self.page_count,
            "generated_at": self.generated_at,
            "integrity_sha256": self.integrity_sha256,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class ProtectionDecision:
    entity_type: str
    category: str
    action: str
    decision: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewSignalSummary:
    """Presentation-safe description of unresolved privacy evidence."""

    category: str
    human_label: str
    count: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProtectionResult:
    status: str
    policy_id: str
    policy_version: str | None
    policy_display_name: str
    accepted_decisions: tuple[ProtectionDecision, ...]
    protected_entity_category_summary: Mapping[str, int]
    review_signal_summary: tuple[ReviewSignalSummary, ...]
    review_required: bool
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_display_name": self.policy_display_name,
            "accepted_decisions": [item.to_dict() for item in self.accepted_decisions],
            "protected_entity_category_summary": dict(
                self.protected_entity_category_summary
            ),
            "review_signal_summary": [
                item.to_dict() for item in self.review_signal_summary
            ],
            "review_required": self.review_required,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class ProtectionProvenance:
    output_owner: str
    external_engine_role: str
    privacy_decision_path: str
    engine_name: str
    engine_version: str
    processing_time: float | None
    candidate_counts: Mapping[str, int]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_owner": self.output_owner,
            "external_engine_role": self.external_engine_role,
            "privacy_decision_path": self.privacy_decision_path,
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "processing_time": self.processing_time,
            "candidate_counts": dict(self.candidate_counts),
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class ProtectOutput:
    protected_document: ProtectedDocument
    patient_analytic_context: PatientAnalyticContext
    protection_result: ProtectionResult
    protection_provenance: ProtectionProvenance

    def to_dict(self) -> dict[str, Any]:
        return {
            "protected_document": self.protected_document.to_dict(),
            "patient_analytic_context": self.patient_analytic_context.to_dict(),
            "protection_result": self.protection_result.to_dict(),
            "protection_provenance": self.protection_provenance.to_dict(),
        }


_NAME_TYPES = {
    CandidateEntityType.PERSON_NAME,
    CandidateEntityType.PATIENT_NAME,
    CandidateEntityType.PHYSICIAN_NAME,
    CandidateEntityType.NURSE_NAME,
    CandidateEntityType.GUARDIAN_NAME,
    CandidateEntityType.RELATIVE_NAME,
    CandidateEntityType.EMPLOYEE_NAME,
    CandidateEntityType.STUDENT_NAME,
}
_IDENTIFIER_TYPES = {
    CandidateEntityType.CIVIL_ID,
    CandidateEntityType.MRN,
    CandidateEntityType.VISIT_NUMBER,
    CandidateEntityType.ACCESSION_NUMBER,
    CandidateEntityType.SPECIMEN_NUMBER,
    CandidateEntityType.LAB_NUMBER,
    CandidateEntityType.DOCUMENT_ID,
    CandidateEntityType.INSURANCE_NUMBER,
    CandidateEntityType.EMPLOYEE_NUMBER,
    CandidateEntityType.STUDENT_NUMBER,
}
_DATE_TYPES = {
    CandidateEntityType.DATE_OF_BIRTH,
    CandidateEntityType.ADMISSION_DATE,
    CandidateEntityType.DISCHARGE_DATE,
    CandidateEntityType.COLLECTION_DATE,
    CandidateEntityType.EXAM_DATE,
    CandidateEntityType.GENERAL_DATE,
}
_CONTACT_TYPES = {
    CandidateEntityType.PHONE_NUMBER,
    CandidateEntityType.EMAIL,
    CandidateEntityType.ADDRESS,
}
_LOCATION_TYPES = {
    CandidateEntityType.LOCATION,
    CandidateEntityType.ORGANIZATION,
}


def _category(entity_type: CandidateEntityType) -> str:
    if entity_type in _NAME_TYPES:
        return "Names"
    if entity_type in _IDENTIFIER_TYPES:
        return "Identifiers"
    if entity_type in _DATE_TYPES:
        return "Dates"
    if entity_type in _CONTACT_TYPES:
        return "Contact Details"
    if entity_type in _LOCATION_TYPES:
        return "Locations and Facilities"
    return "Other Identity Signals"


def _review_signal_identity(entity_type: object) -> tuple[str, str]:
    """Map an unresolved type to a bounded, non-PHI presentation label."""

    try:
        canonical_type = CandidateEntityType(str(entity_type))
    except ValueError:
        canonical_type = CandidateEntityType.UNKNOWN

    if canonical_type is CandidateEntityType.PERSON_NAME:
        return "clinical_person_ambiguity", "Clinical-term/person ambiguity"
    if canonical_type in _NAME_TYPES:
        return "possible_person_name", "Possible person-name signal"
    if canonical_type in _DATE_TYPES:
        return "ambiguous_date_time", "Ambiguous date/time signal"
    if canonical_type in _IDENTIFIER_TYPES:
        return "ambiguous_identifier", "Ambiguous identifier signal"
    if canonical_type in _CONTACT_TYPES:
        return "ambiguous_contact", "Ambiguous contact signal"
    if canonical_type in _LOCATION_TYPES:
        return (
            "ambiguous_location_or_facility",
            "Ambiguous location or facility signal",
        )
    if canonical_type is CandidateEntityType.PROFESSIONAL_ROLE:
        return "clinical_person_ambiguity", "Clinical-term/person ambiguity"
    return "unclassified_identity_like", "Unclassified identity-like signal"


def _safe_review_signal_summary(
    metadata: Mapping[str, Any],
) -> tuple[ReviewSignalSummary, ...]:
    """Aggregate unresolved candidates without exposing text or engine details."""

    intelligence = metadata.get("intelligence_result", {})
    candidates: list[Mapping[str, Any]] = []
    if isinstance(intelligence, Mapping):
        for decision_group in ("review_required", "pending"):
            values = intelligence.get(decision_group, ())
            if isinstance(values, (list, tuple)):
                candidates.extend(
                    value for value in values if isinstance(value, Mapping)
                )

    counts: Counter[tuple[str, str]] = Counter(
        _review_signal_identity(candidate.get("canonical_type"))
        for candidate in candidates
    )
    if not counts:
        candidate_counts = metadata.get("candidate_counts", {})
        unresolved_count = 0
        if isinstance(candidate_counts, Mapping):
            for key in ("review_required", "pending"):
                value = candidate_counts.get(key, 0)
                if isinstance(value, int) and not isinstance(value, bool):
                    unresolved_count += max(value, 0)
        if unresolved_count:
            counts[
                ("unclassified_identity_like", "Unclassified identity-like signal")
            ] = unresolved_count
        elif metadata.get("requires_review"):
            counts[("privacy_review_condition", "Privacy review condition")] = 1

    return tuple(
        ReviewSignalSummary(category, human_label, count)
        for (category, human_label), count in sorted(counts.items())
    )


def _safe_decisions(
    metadata: Mapping[str, Any], policy: PolicyProfile
) -> tuple[ProtectionDecision, ...]:
    candidates = metadata.get("intelligence_result", {}).get("accepted", ())
    decisions: list[ProtectionDecision] = []
    for candidate in candidates:
        try:
            entity_type = CandidateEntityType(candidate["canonical_type"])
            action = PolicyEngine.get_action(
                entity_type,
                policy,
                require_mapping=True,
            )
        except (KeyError, TypeError, ValueError):
            continue
        decisions.append(
            ProtectionDecision(
                entity_type=entity_type.value,
                category=_category(entity_type),
                action=action.value,
                decision=CandidateDecision.ACCEPT.value,
            )
        )
    return tuple(decisions)


def build_protect_output(
    *,
    report_id: str,
    response: Any,
    policy: PolicyProfile,
    artifact: ProtectedArtifact | None = None,
) -> ProtectOutput:
    """Adapt an authoritative privacy response into a PHI-safe R1 envelope."""

    protected_text = response.data.deidentified_text
    metadata = response.metadata or {}
    definition = get_policy_definition(policy)
    review_required = bool(metadata.get("requires_review"))
    protection_complete = metadata.get("protection_complete", True) is not False
    if not protection_complete:
        warnings = (
            "Protection incomplete: a known high-risk identity field remains unprotected.",
        )
    elif review_required:
        warnings = ("One or more privacy candidates require review.",)
    else:
        warnings = ()
    decisions = _safe_decisions(metadata, policy)
    review_signal_summary = _safe_review_signal_summary(metadata)
    transformed = tuple(
        item for item in decisions if item.action != PolicyAction.KEEP.value
    )
    category_summary = Counter(item.category for item in transformed)
    transformations = tuple(sorted({item.action for item in transformed}))
    candidate_counts = {
        str(key): int(value)
        for key, value in metadata.get("candidate_counts", {}).items()
        if isinstance(value, int) and not isinstance(value, bool)
    }

    return ProtectOutput(
        protected_document=ProtectedDocument(
            report_id=report_id,
            protected_text=protected_text,
            output_version="1.0",
            selected_policy_id=policy.value,
            selected_policy_version=None,
            transformations_applied=transformations,
            warnings=warnings,
            integrity_sha256=hashlib.sha256(protected_text.encode("utf-8")).hexdigest(),
            artifact=artifact if protection_complete else None,
        ),
        patient_analytic_context=PatientAnalyticContext.unavailable(),
        protection_result=ProtectionResult(
            status=(
                "BLOCKED"
                if not protection_complete
                else "NEEDS_REVIEW" if review_required else "COMPLETE"
            ),
            policy_id=policy.value,
            policy_version=None,
            policy_display_name=definition.display_name,
            accepted_decisions=decisions,
            protected_entity_category_summary=dict(sorted(category_summary.items())),
            review_signal_summary=review_signal_summary,
            review_required=review_required or not protection_complete,
            warnings=warnings,
        ),
        protection_provenance=ProtectionProvenance(
            output_owner=str(metadata.get("output_owner", "MedNexus")),
            external_engine_role=str(
                metadata.get("external_engine_role", "candidate_detector")
            ),
            privacy_decision_path=str(
                metadata.get("privacy_decision_path", "unified")
            ),
            engine_name=str(response.engine_name or ""),
            engine_version=str(response.engine_version or ""),
            processing_time=response.processing_time,
            candidate_counts=candidate_counts,
            created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        ),
    )
