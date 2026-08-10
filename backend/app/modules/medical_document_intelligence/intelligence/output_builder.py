from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    MedNexusCandidateEntity,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)
from backend.app.modules.medical_document_intelligence.policies.policy_engine import (
    PolicyEngine,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)


@dataclass(frozen=True)
class MedNexusOutputResult:
    """
    Immutable result created by the MedNexus output-building layer.

    MedNexus, not the external engine, owns the final transformed text.
    """

    text: str
    replacements: Tuple[Mapping[str, object], ...]
    warnings: Tuple[str, ...]
    replaced_count: int
    kept_count: int
    rejected_count: int
    review_required_count: int
    pending_count: int

    @property
    def requires_review(self) -> bool:
        """
        Return True when unresolved candidates remain.
        """

        return (
            self.review_required_count > 0
            or self.pending_count > 0
        )

    def to_dict(self) -> dict:
        """
        Return a serialization-safe representation.
        """

        return {
            "text": self.text,
            "replacements": [
                dict(item)
                for item in self.replacements
            ],
            "warnings": list(self.warnings),
            "replaced_count": self.replaced_count,
            "kept_count": self.kept_count,
            "rejected_count": self.rejected_count,
            "review_required_count": (
                self.review_required_count
            ),
            "pending_count": self.pending_count,
            "requires_review": self.requires_review,
        }


class MedNexusOutputBuilder:
    """
    Build final de-identified text from MedNexus intelligence decisions.

    External-engine surrogate text is never used as the authoritative
    final output.

    Decision handling:

        ACCEPT:
            Replace the source span using a MedNexus-owned surrogate.

        KEEP:
            Preserve the exact source text.

        REJECT:
            Preserve the exact source text because the engine detection
            was considered a false positive.

        REVIEW_REQUIRED:
            Preserve the text and add a warning.

        PENDING:
            Preserve the text and add a warning.

    Replacements are applied from right to left to keep source offsets
    stable.
    """

    @classmethod
    def build(
        cls,
        *,
        source_text: str,
        candidates: Iterable[
            MedNexusCandidateEntity
        ],
        profile: PolicyProfile = PolicyProfile.MEDNEXUS_CLINICAL,
        hash_length: int = 10,
    ) -> MedNexusOutputResult:
        """
        Build MedNexus-controlled de-identified output.

        Args:
            source_text:
                Exact source text whose offsets were used during
                detection.

            candidates:
                Final merged and validated MedNexus candidates.

            hash_length:
                Length of deterministic identifier hashes.

        Returns:
            MedNexusOutputResult.
        """

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        if candidates is None:
            raise TypeError(
                "candidates must be an iterable."
            )

        if isinstance(hash_length, bool):
            raise TypeError(
                "hash_length must be an integer."
            )

        if not isinstance(hash_length, int):
            raise TypeError(
                "hash_length must be an integer."
            )

        if hash_length < 6:
            raise ValueError(
                "hash_length must be at least 6."
            )

        materialized = cls._materialize_candidates(
            candidates
        )

        accepted = [
            candidate
            for candidate in materialized
            if (
                candidate.decision
                == CandidateDecision.ACCEPT
            )
        ]

        cls._validate_accepted_spans(
            source_text=source_text,
            candidates=accepted,
        )

        output_text = source_text
        replacements = []
        policy_kept_count = 0

        for candidate in sorted(
            accepted,
            key=lambda item: (
                item.start,
                item.end,
            ),
            reverse=True,
        ):
            action = PolicyEngine.get_action(
                candidate.canonical_type,
                profile,
                require_mapping=True,
            )

            if action == PolicyAction.KEEP:
                policy_kept_count += 1
                continue

            surrogate = PolicyEngine.transform_value(
                value=candidate.text,
                entity=candidate.canonical_type,
                profile=profile,
                require_mapping=True,
                hash_length=hash_length,
            )

            original_value = output_text[
                candidate.start:candidate.end
            ]

            output_text = (
                output_text[:candidate.start]
                + surrogate
                + output_text[candidate.end:]
            )

            replacements.append(
                {
                    "start": candidate.start,
                    "end": candidate.end,
                    "original_text": original_value,
                    "surrogate": surrogate,
                    "entity_type": (
                        candidate.canonical_type.value
                    ),
                    "decision": (
                        candidate.decision.value
                    ),
                    "source": candidate.source.value,
                    "policy_action": action.value,
                }
            )

        replacements.reverse()

        kept_count = (
            cls._count_decision(
                materialized,
                CandidateDecision.KEEP,
            )
            + policy_kept_count
        )

        rejected_count = cls._count_decision(
            materialized,
            CandidateDecision.REJECT,
        )

        review_required = [
            candidate
            for candidate in materialized
            if (
                candidate.decision
                == CandidateDecision.REVIEW_REQUIRED
            )
        ]

        pending = [
            candidate
            for candidate in materialized
            if (
                candidate.decision
                == CandidateDecision.PENDING
            )
        ]

        warnings = cls._build_warnings(
            review_required=review_required,
            pending=pending,
        )

        return MedNexusOutputResult(
            text=output_text,
            replacements=tuple(replacements),
            warnings=tuple(warnings),
            replaced_count=len(replacements),
            kept_count=kept_count,
            rejected_count=rejected_count,
            review_required_count=len(
                review_required
            ),
            pending_count=len(pending),
        )

    @staticmethod
    def _materialize_candidates(
        candidates: Iterable[
            MedNexusCandidateEntity
        ],
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Validate and materialize candidate collections.
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
    def _validate_accepted_spans(
        *,
        source_text: str,
        candidates: Iterable[
            MedNexusCandidateEntity
        ],
    ) -> None:
        """
        Validate source offsets and accepted-candidate overlaps.
        """

        ordered = sorted(
            candidates,
            key=lambda candidate: (
                candidate.start,
                candidate.end,
            ),
        )

        previous_end: Optional[int] = None

        for candidate in ordered:
            if not candidate.matches_source_text(
                source_text
            ):
                raise ValueError(
                    "Accepted candidate offsets do not "
                    "match source_text."
                )

            if (
                previous_end is not None
                and candidate.start < previous_end
            ):
                raise ValueError(
                    "Accepted candidate spans must not overlap."
                )

            previous_end = candidate.end

    @staticmethod
    def _count_decision(
        candidates: Iterable[
            MedNexusCandidateEntity
        ],
        decision: CandidateDecision,
    ) -> int:
        """
        Count candidates having a specific decision.
        """

        return sum(
            1
            for candidate in candidates
            if candidate.decision == decision
        )

    @staticmethod
    def _build_warnings(
        *,
        review_required: Iterable[
            MedNexusCandidateEntity
        ],
        pending: Iterable[
            MedNexusCandidateEntity
        ],
    ) -> list[str]:
        """
        Build output warnings for unresolved candidates.
        """

        warnings = []

        for candidate in review_required:
            warnings.append(
                (
                    "Review required for candidate "
                    f"'{candidate.text}' "
                    f"({candidate.canonical_type.value}) "
                    f"at offsets "
                    f"{candidate.start}:{candidate.end}."
                )
            )

        for candidate in pending:
            warnings.append(
                (
                    "Pending candidate "
                    f"'{candidate.text}' "
                    f"({candidate.canonical_type.value}) "
                    f"at offsets "
                    f"{candidate.start}:{candidate.end}."
                )
            )

        return warnings
