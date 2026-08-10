from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.intelligence.context_validator import (
    ContextValidator,
)
from backend.app.modules.medical_document_intelligence.intelligence.detection_merger import (
    DetectionMerger,
)
from backend.app.modules.medical_document_intelligence.intelligence.entity_canonicalizer import (
    EntityCanonicalizer,
)
from backend.app.modules.medical_document_intelligence.intelligence.openmed_candidate_adapter import (
    OpenMedCandidateAdapter,
)
from backend.app.modules.medical_document_intelligence.intelligence.role_resolver import (
    RoleResolver,
)


@dataclass(frozen=True)
class MedNexusIntelligenceResult:
    """
    Immutable result produced by MedNexus Intelligence Core.

    The result separates candidates by their final MedNexus decision so
    later pipeline stages can apply policies and rebuild document output
    safely.

    Categories:

        accepted:
            Valid identity candidates that may proceed to privacy-policy
            transformation.

        kept:
            Valid entities that must remain unchanged according to the
            current professional or clinical context.

        rejected:
            False-positive detections that must not alter the document.

        review_required:
            Candidates that could not be resolved safely.

        pending:
            Candidates that have not received a final intelligence
            decision.

        all_candidates:
            Full merged candidate sequence ordered by source offsets.
    """

    all_candidates: Tuple[MedNexusCandidateEntity, ...]
    accepted: Tuple[MedNexusCandidateEntity, ...]
    kept: Tuple[MedNexusCandidateEntity, ...]
    rejected: Tuple[MedNexusCandidateEntity, ...]
    review_required: Tuple[MedNexusCandidateEntity, ...]
    pending: Tuple[MedNexusCandidateEntity, ...]

    @property
    def total_count(self) -> int:
        """
        Return the total number of merged MedNexus candidates.
        """

        return len(self.all_candidates)

    @property
    def accepted_count(self) -> int:
        """
        Return the number of accepted identity candidates.
        """

        return len(self.accepted)

    @property
    def kept_count(self) -> int:
        """
        Return the number of candidates preserved by MedNexus.
        """

        return len(self.kept)

    @property
    def rejected_count(self) -> int:
        """
        Return the number of false-positive detections rejected.
        """

        return len(self.rejected)

    @property
    def review_required_count(self) -> int:
        """
        Return the number of candidates requiring manual review.
        """

        return len(self.review_required)

    @property
    def pending_count(self) -> int:
        """
        Return the number of unresolved pending candidates.
        """

        return len(self.pending)

    @property
    def is_safe_for_automatic_output(self) -> bool:
        """
        Return True when no candidate requires review or remains pending.

        This property does not replace the future OutputSafetyValidator.
        It is an intelligence-stage readiness indicator only.
        """

        return (
            self.review_required_count == 0
            and self.pending_count == 0
        )

    def to_dict(self) -> dict:
        """
        Return a serialization-safe representation.
        """

        return {
            "total_count": self.total_count,
            "accepted_count": self.accepted_count,
            "kept_count": self.kept_count,
            "rejected_count": self.rejected_count,
            "review_required_count": self.review_required_count,
            "pending_count": self.pending_count,
            "is_safe_for_automatic_output": (
                self.is_safe_for_automatic_output
            ),
            "all_candidates": [
                candidate.to_dict()
                for candidate in self.all_candidates
            ],
            "accepted": [
                candidate.to_dict()
                for candidate in self.accepted
            ],
            "kept": [
                candidate.to_dict()
                for candidate in self.kept
            ],
            "rejected": [
                candidate.to_dict()
                for candidate in self.rejected
            ],
            "review_required": [
                candidate.to_dict()
                for candidate in self.review_required
            ],
            "pending": [
                candidate.to_dict()
                for candidate in self.pending
            ],
        }


class MedNexusIntelligenceOrchestrator:
    """
    Execute the MedNexus Intelligence Core pipeline.

    OpenMed remains a candidate-detection engine only.

    MedNexus is responsible for:

        - adapting external engine entities
        - converting them into MedNexus contracts
        - resolving medical and administrative roles
        - validating detections against clinical context
        - merging internal and external detections
        - classifying final decisions

    The orchestrator does not modify document text and does not apply
    privacy transformations. Those responsibilities belong to the next
    pipeline stage.
    """

    @classmethod
    def process_openmed_result(
        cls,
        *,
        engine_result: Any,
        source_text: str,
        context_candidates: Iterable[
            MedNexusCandidateEntity
        ] = (),
        mednexus_candidates: Iterable[
            MedNexusCandidateEntity
        ] = (),
    ) -> MedNexusIntelligenceResult:
        """
        Process OpenMed results and optional MedNexus rule detections.

        Args:
            engine_result:
                Raw OpenMed result object.

            source_text:
                Exact text that was sent to OpenMed.

            mednexus_candidates:
                Candidate entities produced by MedNexus deterministic,
                field-aware, Arabic, or inline rules.

        Returns:
            MedNexusIntelligenceResult.
        """

        if engine_result is None:
            raise TypeError(
                "engine_result cannot be None."
            )

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        if mednexus_candidates is None:
            raise TypeError(
                "mednexus_candidates must be an iterable."
            )

        if context_candidates is None:
            raise TypeError(
                "context_candidates must be an iterable."
            )

        context_candidates = cls._validate_internal_candidates(
            context_candidates
        )

        internal_candidates = cls._validate_internal_candidates(
            mednexus_candidates
        )

        openmed_candidates = (
            OpenMedCandidateAdapter.adapt_result(
                engine_result=engine_result,
                source_text=source_text,
            )
        )

        return cls._process_candidate_groups(
            source_text=source_text,
            candidate_groups=(
                context_candidates,
                internal_candidates,
                openmed_candidates,
            ),
        )

    @classmethod
    def process_candidates(
        cls,
        *,
        source_text: str,
        candidates: Iterable[
            MedNexusCandidateEntity
        ],
    ) -> MedNexusIntelligenceResult:
        """
        Process candidate collections without requiring an OpenMed result.

        This method supports deterministic-only execution and future
        engines.
        """

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        if candidates is None:
            raise TypeError(
                "candidates must be an iterable."
            )

        validated_candidates = (
            cls._validate_internal_candidates(
                candidates
            )
        )

        return cls._process_candidate_groups(
            source_text=source_text,
            candidate_groups=(validated_candidates,),
        )

    @classmethod
    def _process_candidate_groups(
        cls,
        *,
        source_text: str,
        candidate_groups: Iterable[
            Iterable[MedNexusCandidateEntity]
        ],
    ) -> MedNexusIntelligenceResult:
        """Run every candidate source through one intelligence path."""

        combined = tuple(
            candidate
            for group in candidate_groups
            for candidate in group
        )
        canonicalized = EntityCanonicalizer.canonicalize_many(
            combined
        )
        role_resolved = RoleResolver.resolve_many(
            candidates=canonicalized,
            source_text=source_text,
        )
        validated = ContextValidator.validate_many(
            candidates=role_resolved,
            source_text=source_text,
        )
        merged = DetectionMerger.merge(validated)

        return cls._build_result(merged)

    @staticmethod
    def _validate_internal_candidates(
        candidates: Iterable[
            MedNexusCandidateEntity
        ],
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Validate and materialize MedNexus candidate collections.
        """

        materialized = []

        for candidate in candidates:
            if not isinstance(
                candidate,
                MedNexusCandidateEntity,
            ):
                raise TypeError(
                    "All candidates must be "
                    "MedNexusCandidateEntity objects."
                )

            materialized.append(candidate)

        return tuple(materialized)

    @staticmethod
    def _build_result(
        candidates: Iterable[
            MedNexusCandidateEntity
        ],
    ) -> MedNexusIntelligenceResult:
        """
        Group merged candidates by MedNexus decision.
        """

        all_candidates = tuple(candidates)

        accepted = tuple(
            candidate
            for candidate in all_candidates
            if (
                candidate.decision
                == CandidateDecision.ACCEPT
            )
        )

        kept = tuple(
            candidate
            for candidate in all_candidates
            if (
                candidate.decision
                == CandidateDecision.KEEP
            )
        )

        rejected = tuple(
            candidate
            for candidate in all_candidates
            if (
                candidate.decision
                == CandidateDecision.REJECT
            )
        )

        review_required = tuple(
            candidate
            for candidate in all_candidates
            if (
                candidate.decision
                == CandidateDecision.REVIEW_REQUIRED
            )
        )

        pending = tuple(
            candidate
            for candidate in all_candidates
            if (
                candidate.decision
                == CandidateDecision.PENDING
            )
        )

        return MedNexusIntelligenceResult(
            all_candidates=all_candidates,
            accepted=accepted,
            kept=kept,
            rejected=rejected,
            review_required=review_required,
            pending=pending,
        )
