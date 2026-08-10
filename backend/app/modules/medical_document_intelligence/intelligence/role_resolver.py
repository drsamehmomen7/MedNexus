from __future__ import annotations

import re
from typing import Iterable, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
    MedNexusCandidateEntity,
)


class RoleResolver:
    """
    Resolve generic person-name candidates into clinically meaningful roles.

    The resolver uses nearby field labels and document context.

    It does not:
        - accept or reject a candidate
        - apply a privacy policy
        - modify document text
        - transform placeholders

    It only refines generic PERSON_NAME candidates into MedNexus roles.
    """

    FIELD_ROLE_PATTERNS = {
        CandidateEntityType.PATIENT_NAME: (
            r"patient(?:\s+full)?\s+name",
            r"patient",
            r"name\s+of\s+patient",
            r"اسم\s+المريض",
            r"اسم\s+المريضة",
            r"المريض",
            r"المريضة",
        ),
        CandidateEntityType.PHYSICIAN_NAME: (
            r"physician",
            r"reporting\s+physician",
            r"doctor",
            r"consultant",
            r"consultant\s+pathologist",
            r"reporting\s+radiologist",
            r"radiologist",
            r"referring\s+physician",
            r"attending\s+physician",
            r"authorized\s+by",
            r"approved\s+by",
            r"reported\s+by",
            r"verified\s+by",
            r"signed\s+by",
            r"clinician",
            r"طبيب",
            r"الطبيب",
            r"طبيب\s+الأشعة",
            r"استشاري",
            r"الاستشاري",
            r"اعتمد\s+بواسطة",
            r"معتمد\s+بواسطة",
            r"أخصائي",
            r"الأخصائي",
        ),
        CandidateEntityType.NURSE_NAME: (
            r"nurse",
            r"assigned\s+nurse",
            r"triage\s+nurse",
            r"school\s+nurse",
            r"vaccinator",
            r"registered\s+nurse",
            r"rn",
            r"ممرضة",
            r"الممرضة",
            r"ممرض",
            r"الممرض",
            r"ممرضة\s+المدرسة",
            r"ممرض\s+المدرسة",
        ),
        CandidateEntityType.GUARDIAN_NAME: (
            r"guardian",
            r"guardian\s+name",
            r"parent",
            r"parent\s+name",
            r"ولي\s+الأمر",
            r"اسم\s+ولي\s+الأمر",
            r"الوصي",
            r"اسم\s+الوصي",
        ),
        CandidateEntityType.RELATIVE_NAME: (
            r"next\s+of\s+kin",
            r"relative",
            r"spouse",
            r"family\s+contact",
            r"emergency\s+contact",
            r"قريب",
            r"اسم\s+القريب",
            r"ذوي\s+المريض",
            r"أقرب\s+الأقارب",
            r"جهة\s+الاتصال",
            r"الزوج",
            r"الزوجة",
        ),
        CandidateEntityType.EMPLOYEE_NAME: (
            r"employee",
            r"employee\s+name",
            r"staff\s+name",
            r"اسم\s+الموظف",
            r"الموظف",
            r"اسم\s+العامل",
        ),
        CandidateEntityType.STUDENT_NAME: (
            r"student",
            r"student\s+name",
            r"pupil",
            r"child\s+name",
            r"اسم\s+الطالب",
            r"اسم\s+الطالبة",
            r"الطالب",
            r"الطالبة",
            r"اسم\s+الطفل",
            r"اسم\s+الطفلة",
        ),
    }

    _FIELD_PATTERN = re.compile(
        r"""
        (?P<label>
            [^\r\n:]{1,80}
        )
        \s*:\s*
        (?P<value>[^\r\n]+)
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    @classmethod
    def resolve(
        cls,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ) -> MedNexusCandidateEntity:
        """
        Resolve one person candidate using document context.

        Existing role-specific classifications are preserved.

        Only generic PERSON_NAME and UNKNOWN candidates are considered.
        """

        if not isinstance(
            candidate,
            MedNexusCandidateEntity,
        ):
            raise TypeError(
                "candidate must be a MedNexusCandidateEntity."
            )

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        if candidate.canonical_type in {
            CandidateEntityType.PATIENT_NAME,
            CandidateEntityType.PHYSICIAN_NAME,
            CandidateEntityType.NURSE_NAME,
            CandidateEntityType.GUARDIAN_NAME,
            CandidateEntityType.RELATIVE_NAME,
            CandidateEntityType.EMPLOYEE_NAME,
            CandidateEntityType.STUDENT_NAME,
        }:
            return candidate

        if candidate.canonical_type not in {
            CandidateEntityType.PERSON_NAME,
            CandidateEntityType.UNKNOWN,
        }:
            return candidate

        resolved_type = cls._resolve_from_field(
            candidate=candidate,
            source_text=source_text,
        )

        if resolved_type is None:
            resolved_type = cls._resolve_from_nearby_context(
                candidate=candidate,
                source_text=source_text,
            )

        if resolved_type is None:
            return candidate

        return candidate.with_canonical_type(
            resolved_type,
            normalized_label=resolved_type.value,
            reason=(
                f"Resolved person role from document context "
                f"as '{resolved_type.value}'."
            ),
        )

    @classmethod
    def resolve_many(
        cls,
        candidates: Iterable[MedNexusCandidateEntity],
        source_text: str,
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Resolve multiple candidates while preserving their order.
        """

        if candidates is None:
            raise TypeError(
                "candidates must be an iterable."
            )

        if not isinstance(source_text, str):
            raise TypeError(
                "source_text must be a string."
            )

        return tuple(
            cls.resolve(
                candidate=candidate,
                source_text=source_text,
            )
            for candidate in candidates
        )

    @classmethod
    def _resolve_from_field(
        cls,
        *,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ):
        """
        Resolve a candidate when it appears inside a labelled field.
        """

        for match in cls._FIELD_PATTERN.finditer(
            source_text
        ):
            value_start = match.start("value")
            value_end = match.end("value")

            if not cls._spans_overlap(
                candidate.start,
                candidate.end,
                value_start,
                value_end,
            ):
                continue

            label = cls._normalize_context(
                match.group("label")
            )

            return cls._resolve_label_role(
                label
            )

        return None

    @classmethod
    def _resolve_from_nearby_context(
        cls,
        *,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ):
        """
        Resolve names located on the line following a field label.

        Example:

            Patient Name:
            Ahmed Hassan
        """

        context_start = max(
            0,
            candidate.start - 120,
        )

        prefix = source_text[
            context_start:candidate.start
        ]

        prefix_lines = [
            line.strip()
            for line in prefix.splitlines()
            if line.strip()
        ]

        if not prefix_lines:
            return None

        for line in reversed(prefix_lines[-3:]):
            normalized = cls._normalize_context(
                line.rstrip(":")
            )

            resolved = cls._resolve_label_role(
                normalized
            )

            if resolved is not None:
                return resolved

        return None

    @classmethod
    def _resolve_label_role(
        cls,
        normalized_label: str,
    ):
        """
        Map a normalized field label to a MedNexus role.
        """

        for entity_type, patterns in (
            cls.FIELD_ROLE_PATTERNS.items()
        ):
            for pattern in patterns:
                if re.fullmatch(
                    pattern,
                    normalized_label,
                    flags=re.IGNORECASE,
                ):
                    return entity_type

        return None

    @staticmethod
    def _normalize_context(
        value: str,
    ) -> str:
        """
        Normalize an English or Arabic field label.
        """

        value = value.strip()
        value = value.rstrip(":")
        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.lower()

    @staticmethod
    def _spans_overlap(
        first_start: int,
        first_end: int,
        second_start: int,
        second_end: int,
    ) -> bool:
        """
        Return True when two character spans overlap.
        """

        return (
            first_start < second_end
            and first_end > second_start
        )
