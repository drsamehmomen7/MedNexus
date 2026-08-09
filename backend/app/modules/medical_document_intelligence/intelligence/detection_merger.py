from __future__ import annotations

from typing import Iterable, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)


class DetectionMerger:
    """
    Merge MedNexus and external-engine candidate detections.

    MedNexus detections always take priority over external-engine detections.

    Priority order:

        1. MedNexus field rules
        2. MedNexus Arabic rules
        3. MedNexus inline rules
        4. Accepted OpenMed candidates
        5. Review-required candidates
        6. Rejected candidates

    The merger removes duplicates and resolves overlapping spans
    deterministically.

    It does not modify document text.
    """

    SOURCE_PRIORITY = {
        CandidateSource.MEDNEXUS_FIELD_RULE: 100,
        CandidateSource.MEDNEXUS_ARABIC_RULE: 95,
        CandidateSource.MEDNEXUS_INLINE_RULE: 90,
        CandidateSource.OPENMED: 60,
        CandidateSource.EXTERNAL_ENGINE: 50,
        CandidateSource.UNKNOWN: 10,
    }

    DECISION_PRIORITY = {
        CandidateDecision.ACCEPT: 100,
        CandidateDecision.KEEP: 90,
        CandidateDecision.REVIEW_REQUIRED: 70,
        CandidateDecision.PENDING: 50,
        CandidateDecision.REJECT: 10,
    }

    TYPE_PRIORITY = {
        CandidateEntityType.PATIENT_NAME: 100,
        CandidateEntityType.PHYSICIAN_NAME: 95,
        CandidateEntityType.NURSE_NAME: 95,
        CandidateEntityType.GUARDIAN_NAME: 95,
        CandidateEntityType.RELATIVE_NAME: 95,
        CandidateEntityType.EMPLOYEE_NAME: 95,
        CandidateEntityType.STUDENT_NAME: 95,

        CandidateEntityType.CIVIL_ID: 100,
        CandidateEntityType.MRN: 100,
        CandidateEntityType.VISIT_NUMBER: 100,
        CandidateEntityType.ACCESSION_NUMBER: 100,
        CandidateEntityType.SPECIMEN_NUMBER: 100,
        CandidateEntityType.LAB_NUMBER: 100,
        CandidateEntityType.DOCUMENT_ID: 100,
        CandidateEntityType.INSURANCE_NUMBER: 100,
        CandidateEntityType.EMPLOYEE_NUMBER: 100,
        CandidateEntityType.STUDENT_NUMBER: 100,

        CandidateEntityType.PHONE_NUMBER: 100,
        CandidateEntityType.EMAIL: 100,
        CandidateEntityType.ADDRESS: 95,
        CandidateEntityType.DATE_OF_BIRTH: 95,

        CandidateEntityType.PERSON_NAME: 70,
        CandidateEntityType.PROFESSIONAL_ROLE: 40,
        CandidateEntityType.ORGANIZATION: 40,
        CandidateEntityType.LOCATION: 40,
        CandidateEntityType.GENERAL_DATE: 40,
        CandidateEntityType.UNKNOWN: 10,
    }

    @classmethod
    def merge(
        cls,
        *candidate_groups: Iterable[MedNexusCandidateEntity],
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Merge multiple candidate collections.

        Returns a deterministic tuple sorted by source position.
        """

        flattened = cls._flatten_groups(
            candidate_groups
        )

        if not flattened:
            return ()

        deduplicated = cls._remove_exact_duplicates(
            flattened
        )

        resolved = cls._resolve_overlaps(
            deduplicated
        )

        return tuple(
            sorted(
                resolved,
                key=lambda candidate: (
                    candidate.start,
                    candidate.end,
                ),
            )
        )

    @classmethod
    def merge_two(
        cls,
        first: Iterable[MedNexusCandidateEntity],
        second: Iterable[MedNexusCandidateEntity],
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Convenience method for merging two collections.
        """

        return cls.merge(
            first,
            second,
        )

    @classmethod
    def _flatten_groups(
        cls,
        candidate_groups,
    ):
        """
        Flatten and validate all candidate collections.
        """

        flattened = []

        for group in candidate_groups:
            if group is None:
                continue

            for candidate in group:
                if not isinstance(
                    candidate,
                    MedNexusCandidateEntity,
                ):
                    raise TypeError(
                        "All detections must be "
                        "MedNexusCandidateEntity objects."
                    )

                flattened.append(candidate)

        return flattened

    @classmethod
    def _remove_exact_duplicates(
        cls,
        candidates,
    ):
        """
        Remove exact duplicates while preserving the strongest candidate.
        """

        grouped = {}

        for candidate in candidates:
            key = (
                candidate.start,
                candidate.end,
                candidate.text,
            )

            existing = grouped.get(key)

            if existing is None:
                grouped[key] = candidate
                continue

            grouped[key] = cls._choose_stronger(
                existing,
                candidate,
            )

        return list(grouped.values())

    @classmethod
    def _resolve_overlaps(
        cls,
        candidates,
    ):
        """
        Resolve overlapping candidate spans.

        The strongest candidate wins.

        A rejected candidate never removes an accepted MedNexus detection.
        """

        ordered = sorted(
            candidates,
            key=lambda candidate: (
                -cls._candidate_score(candidate),
                -(candidate.end - candidate.start),
                candidate.start,
            ),
        )

        accepted = []

        for candidate in ordered:
            overlapping_indexes = [
                index
                for index, existing in enumerate(accepted)
                if cls._spans_overlap(
                    candidate,
                    existing,
                )
            ]

            if not overlapping_indexes:
                accepted.append(candidate)
                continue

            overlapping_candidates = [
                accepted[index]
                for index in overlapping_indexes
            ]

            strongest_existing = max(
                overlapping_candidates,
                key=cls._candidate_score,
            )

            winner = cls._choose_stronger(
                strongest_existing,
                candidate,
            )

            if winner is strongest_existing:
                continue

            accepted = [
                existing
                for existing in accepted
                if not cls._spans_overlap(
                    candidate,
                    existing,
                )
            ]

            accepted.append(candidate)

        return accepted

    @classmethod
    def _choose_stronger(
        cls,
        first: MedNexusCandidateEntity,
        second: MedNexusCandidateEntity,
    ) -> MedNexusCandidateEntity:
        """
        Choose the strongest of two competing candidates.
        """

        first_score = cls._candidate_score(
            first
        )

        second_score = cls._candidate_score(
            second
        )

        if second_score > first_score:
            return second

        if first_score > second_score:
            return first

        first_length = first.end - first.start
        second_length = second.end - second.start

        if second_length > first_length:
            return second

        if first_length > second_length:
            return first

        if second.confidence is not None:
            if first.confidence is None:
                return second

            if second.confidence > first.confidence:
                return second

        return first

    @classmethod
    def _candidate_score(
        cls,
        candidate: MedNexusCandidateEntity,
    ) -> int:
        """
        Calculate deterministic candidate strength.
        """

        source_score = cls.SOURCE_PRIORITY.get(
            candidate.source,
            0,
        )

        decision_score = cls.DECISION_PRIORITY.get(
            candidate.decision,
            0,
        )

        type_score = cls.TYPE_PRIORITY.get(
            candidate.canonical_type,
            0,
        )

        confidence_score = 0

        if candidate.confidence is not None:
            confidence_score = int(
                candidate.confidence * 10
            )

        return (
            source_score
            + decision_score
            + type_score
            + confidence_score
        )

    @staticmethod
    def _spans_overlap(
        first: MedNexusCandidateEntity,
        second: MedNexusCandidateEntity,
    ) -> bool:
        """
        Return True when two candidate spans overlap.
        """

        return (
            first.start < second.end
            and first.end > second.start
        )