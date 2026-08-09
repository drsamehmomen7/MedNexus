from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Optional


class CandidateSource(str, Enum):
    """
    Identifies the component that produced a candidate entity.

    MedNexus treats all external and internal detections as candidates
    until they are validated by the Intelligence Core.
    """

    MEDNEXUS_FIELD_RULE = "mednexus_field_rule"
    MEDNEXUS_INLINE_RULE = "mednexus_inline_rule"
    MEDNEXUS_ARABIC_RULE = "mednexus_arabic_rule"
    OPENMED = "openmed"
    EXTERNAL_ENGINE = "external_engine"
    UNKNOWN = "unknown"


class CandidateDecision(str, Enum):
    """
    Current MedNexus decision regarding a candidate entity.

    A candidate must not be transformed merely because an external
    engine detected it.

    PENDING:
        The candidate has not yet been evaluated.

    ACCEPT:
        The candidate is considered valid and may continue to policy
        evaluation.

    REJECT:
        The detection is considered a false positive and must not alter
        the document.

    KEEP:
        The entity is valid but the selected policy or medical context
        requires preserving its original value.

    REVIEW_REQUIRED:
        MedNexus could not safely resolve the entity automatically.
    """

    PENDING = "pending"
    ACCEPT = "accept"
    REJECT = "reject"
    KEEP = "keep"
    REVIEW_REQUIRED = "review_required"


class CandidateEntityType(str, Enum):
    """
    Engine-independent entity taxonomy used by MedNexus Intelligence.

    These values are candidate classifications only. RoleResolver and
    ContextValidator may refine them later.
    """

    PERSON_NAME = "person_name"
    PATIENT_NAME = "patient_name"
    PHYSICIAN_NAME = "physician_name"
    NURSE_NAME = "nurse_name"
    GUARDIAN_NAME = "guardian_name"
    RELATIVE_NAME = "relative_name"
    EMPLOYEE_NAME = "employee_name"
    STUDENT_NAME = "student_name"

    CIVIL_ID = "civil_id"
    MRN = "mrn"
    VISIT_NUMBER = "visit_number"
    ACCESSION_NUMBER = "accession_number"
    SPECIMEN_NUMBER = "specimen_number"
    LAB_NUMBER = "lab_number"
    DOCUMENT_ID = "document_id"
    INSURANCE_NUMBER = "insurance_number"
    EMPLOYEE_NUMBER = "employee_number"
    STUDENT_NUMBER = "student_number"

    PHONE_NUMBER = "phone_number"
    EMAIL = "email"
    ADDRESS = "address"

    DATE_OF_BIRTH = "date_of_birth"
    ADMISSION_DATE = "admission_date"
    DISCHARGE_DATE = "discharge_date"
    COLLECTION_DATE = "collection_date"
    EXAM_DATE = "exam_date"
    GENERAL_DATE = "general_date"

    ORGANIZATION = "organization"
    LOCATION = "location"
    PROFESSIONAL_ROLE = "professional_role"

    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MedNexusCandidateEntity:
    """
    Unified candidate entity contract for MedNexus Intelligence Core.

    This contract separates external engine output from MedNexus
    decision-making.

    External engines may suggest:
        - raw labels
        - spans
        - confidence scores
        - surrogate values

    MedNexus remains responsible for:
        - canonical entity type
        - clinical role resolution
        - context validation
        - false-positive rejection
        - privacy-policy application
        - final output safety

    The class is immutable to prevent accidental modification after a
    candidate has entered the intelligence pipeline.
    """

    text: str
    start: int
    end: int

    source: CandidateSource = CandidateSource.UNKNOWN
    raw_label: Optional[str] = None
    canonical_type: CandidateEntityType = CandidateEntityType.UNKNOWN

    confidence: Optional[float] = None
    decision: CandidateDecision = CandidateDecision.PENDING

    normalized_label: Optional[str] = None
    surrogate: Optional[str] = None
    reason: Optional[str] = None

    metadata: Mapping[str, Any] = field(
        default_factory=dict,
        repr=False,
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize the immutable candidate.
        """

        if not isinstance(self.text, str):
            raise TypeError(
                "text must be a string."
            )

        if not self.text:
            raise ValueError(
                "text cannot be empty."
            )

        if not isinstance(self.start, int):
            raise TypeError(
                "start must be an integer."
            )

        if not isinstance(self.end, int):
            raise TypeError(
                "end must be an integer."
            )

        if self.start < 0:
            raise ValueError(
                "start cannot be negative."
            )

        if self.end <= self.start:
            raise ValueError(
                "end must be greater than start."
            )

        if not isinstance(
            self.source,
            CandidateSource,
        ):
            raise TypeError(
                "source must be a CandidateSource."
            )

        if not isinstance(
            self.canonical_type,
            CandidateEntityType,
        ):
            raise TypeError(
                "canonical_type must be a CandidateEntityType."
            )

        if not isinstance(
            self.decision,
            CandidateDecision,
        ):
            raise TypeError(
                "decision must be a CandidateDecision."
            )

        if self.confidence is not None:
            if isinstance(self.confidence, bool):
                raise TypeError(
                    "confidence must be a numeric value or None."
                )

            if not isinstance(
                self.confidence,
                (int, float),
            ):
                raise TypeError(
                    "confidence must be a numeric value or None."
                )

            if not 0.0 <= float(self.confidence) <= 1.0:
                raise ValueError(
                    "confidence must be between 0.0 and 1.0."
                )

            object.__setattr__(
                self,
                "confidence",
                float(self.confidence),
            )

        if self.raw_label is not None:
            normalized_raw_label = (
                str(self.raw_label).strip()
            )

            object.__setattr__(
                self,
                "raw_label",
                normalized_raw_label or None,
            )

        if self.normalized_label is not None:
            normalized_label = (
                str(self.normalized_label)
                .strip()
                .lower()
            )

            object.__setattr__(
                self,
                "normalized_label",
                normalized_label or None,
            )

        if self.surrogate is not None:
            normalized_surrogate = (
                str(self.surrogate).strip()
            )

            object.__setattr__(
                self,
                "surrogate",
                normalized_surrogate or None,
            )

        if self.reason is not None:
            normalized_reason = (
                str(self.reason).strip()
            )

            object.__setattr__(
                self,
                "reason",
                normalized_reason or None,
            )

        if not isinstance(
            self.metadata,
            Mapping,
        ):
            raise TypeError(
                "metadata must be a mapping."
            )

        immutable_metadata = MappingProxyType(
            dict(self.metadata)
        )

        object.__setattr__(
            self,
            "metadata",
            immutable_metadata,
        )

    @property
    def length(self) -> int:
        """
        Return the number of characters covered by the candidate.
        """

        return self.end - self.start

    @property
    def is_positioned(self) -> bool:
        """
        Return True when the candidate has a valid positive span.
        """

        return (
            self.start >= 0
            and self.end > self.start
        )

    @property
    def is_accepted(self) -> bool:
        """
        Return True when MedNexus accepted the candidate.
        """

        return self.decision == CandidateDecision.ACCEPT

    @property
    def is_rejected(self) -> bool:
        """
        Return True when MedNexus rejected the candidate.
        """

        return self.decision == CandidateDecision.REJECT

    @property
    def requires_review(self) -> bool:
        """
        Return True when automatic resolution was not considered safe.
        """

        return (
            self.decision
            == CandidateDecision.REVIEW_REQUIRED
        )

    def matches_source_text(
        self,
        source_text: str,
    ) -> bool:
        """
        Verify that the candidate offsets point to its exact text.

        This protects MedNexus from invalid or stale offsets returned by
        an external engine.
        """

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        if self.end > len(source_text):
            return False

        return (
            source_text[self.start:self.end]
            == self.text
        )

    def with_decision(
        self,
        decision: CandidateDecision,
        *,
        reason: Optional[str] = None,
    ) -> "MedNexusCandidateEntity":
        """
        Return a new candidate containing an updated MedNexus decision.

        The original candidate remains unchanged.
        """

        if not isinstance(
            decision,
            CandidateDecision,
        ):
            raise TypeError(
                "decision must be a CandidateDecision."
            )

        return MedNexusCandidateEntity(
            text=self.text,
            start=self.start,
            end=self.end,
            source=self.source,
            raw_label=self.raw_label,
            canonical_type=self.canonical_type,
            confidence=self.confidence,
            decision=decision,
            normalized_label=self.normalized_label,
            surrogate=self.surrogate,
            reason=reason,
            metadata=self.metadata,
        )

    def with_canonical_type(
        self,
        canonical_type: CandidateEntityType,
        *,
        normalized_label: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> "MedNexusCandidateEntity":
        """
        Return a new candidate with a MedNexus canonical entity type.
        """

        if not isinstance(
            canonical_type,
            CandidateEntityType,
        ):
            raise TypeError(
                "canonical_type must be a CandidateEntityType."
            )

        return MedNexusCandidateEntity(
            text=self.text,
            start=self.start,
            end=self.end,
            source=self.source,
            raw_label=self.raw_label,
            canonical_type=canonical_type,
            confidence=self.confidence,
            decision=self.decision,
            normalized_label=normalized_label,
            surrogate=self.surrogate,
            reason=reason,
            metadata=self.metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Return a serialization-safe representation of the candidate.
        """

        return {
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "length": self.length,
            "source": self.source.value,
            "raw_label": self.raw_label,
            "canonical_type": self.canonical_type.value,
            "confidence": self.confidence,
            "decision": self.decision.value,
            "normalized_label": self.normalized_label,
            "surrogate": self.surrogate,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }