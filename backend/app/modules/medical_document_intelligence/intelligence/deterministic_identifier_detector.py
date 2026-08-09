from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)


@dataclass(frozen=True)
class _FieldRule:
    """
    Internal immutable rule definition used by the deterministic detector.

    Each rule requires a trusted field label before a candidate value is
    created. This keeps MedNexus conservative and avoids treating arbitrary
    clinical numbers as identity information.
    """

    name: str
    entity_type: CandidateEntityType
    pattern: re.Pattern[str]
    confidence: float = 1.0


class DeterministicIdentifierDetector:
    """
    MedNexus-owned deterministic detector for structured identifiers.

    The detector is intentionally independent from OpenMed. It produces
    MedNexusCandidateEntity objects that enter the existing Intelligence Core
    together with external-engine candidates.

    Design principles:

        - prefer explicit field labels for ambiguous numeric identifiers
        - allow only high-confidence inline patterns
        - preserve exact source offsets
        - never modify document text
        - never make the final privacy decision here
        - never create OpenMed-specific objects

    ContextValidator remains responsible for ACCEPT / KEEP / REJECT /
    REVIEW_REQUIRED decisions, and DetectionMerger remains responsible for
    resolving overlaps between MedNexus and external-engine detections.
    """

    _VALUE_SEPARATOR = r"\s*(?:[:#=]|[-–—])?\s*"

    _PHONE_VALUE = (
        r"(?P<value>"
        r"(?:\+\s*)?"
        r"[0-9٠-٩۰-۹]"
        r"(?:[\s().\-/]*[0-9٠-٩۰-۹]){6,14}"
        r")"
    )

    _EMAIL_VALUE = (
        r"(?P<value>"
        r"[A-Z0-9._%+\-]+"
        r"@"
        r"[A-Z0-9.\-]+"
        r"\."
        r"[A-Z]{2,}"
        r")"
    )

    _IDENTIFIER_VALUE = (
        r"(?P<value>"
        r"[A-Z0-9]"
        r"[A-Z0-9._/\-]{2,}"
        r")"
    )

    _CIVIL_ID_VALUE = (
        r"(?P<value>"
        r"[0-9٠-٩۰-۹]{12}"
        r")"
    )

    _PATIENT_NAME_VALUE = (
        r"(?P<value>"
        r"[^\r\n:]{2,120}?"
        r")"
        r"(?=\s*(?:\r?\n|$))"
    )

    FIELD_RULES: Tuple[_FieldRule, ...] = (
        _FieldRule(
            name="patient_name_field",
            entity_type=CandidateEntityType.PATIENT_NAME,
            pattern=re.compile(
                r"(?P<label>"
                r"patient\s+name"
                r"|اسم\s+المريض"
                r")"
                + _VALUE_SEPARATOR
                + _PATIENT_NAME_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="phone_field",
            entity_type=CandidateEntityType.PHONE_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"(?:phone|telephone|mobile|cell|tel)"
                r"(?:\s*(?:number|no\.?))?"
                r"|contact\s*(?:number|no\.?)"
                r"|(?:رقم\s*)?(?:الهاتف|هاتف|الجوال|جوال|الموبايل|موبايل|التليفون|تليفون|التلفون|تلفون)"
                r")"
                + _VALUE_SEPARATOR
                + _PHONE_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="email_field",
            entity_type=CandidateEntityType.EMAIL,
            pattern=re.compile(
                r"(?P<label>"
                r"e[\s\-]?mail(?:\s*address)?"
                r"|email"
                r"|البريد\s+الإلكتروني"
                r"|البريد\s+الالكتروني"
                r")"
                + _VALUE_SEPARATOR
                + _EMAIL_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="civil_id_field",
            entity_type=CandidateEntityType.CIVIL_ID,
            pattern=re.compile(
                r"(?P<label>"
                r"civil\s*(?:id|i\.d\.)"
                r"|civil\s+number"
                r"|cid"
                r"|الرقم\s+المدني"
                r"|رقم\s+مدني"
                r")"
                + _VALUE_SEPARATOR
                + _CIVIL_ID_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="mrn_field",
            entity_type=CandidateEntityType.MRN,
            pattern=re.compile(
                r"(?P<label>"
                r"mrn"
                r"|medical\s+record\s+(?:number|no\.?)"
                r"|patient\s+record\s+(?:number|no\.?)"
                r"|رقم\s+الملف\s+الطبي"
                r"|رقم\s+الملف"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="visit_number_field",
            entity_type=CandidateEntityType.VISIT_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"visit\s*(?:number|no\.?)"
                r"|visit\s*id"
                r"|encounter\s*(?:number|no\.?|id)"
                r"|رقم\s+الزيارة"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="accession_number_field",
            entity_type=CandidateEntityType.ACCESSION_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"accession\s*(?:number|no\.?|id)?"
                r"|رقم\s+الأكسشن"
                r"|رقم\s+الاكسشن"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="specimen_number_field",
            entity_type=CandidateEntityType.SPECIMEN_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"specimen\s*(?:number|no\.?|id)"
                r"|sample\s*(?:number|no\.?|id)"
                r"|رقم\s+العينة"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="lab_number_field",
            entity_type=CandidateEntityType.LAB_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"lab(?:oratory)?\s*(?:number|no\.?|id)"
                r"|رقم\s+المختبر"
                r"|رقم\s+المعمل"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="document_id_field",
            entity_type=CandidateEntityType.DOCUMENT_ID,
            pattern=re.compile(
                r"(?P<label>"
                r"document\s*(?:number|no\.?|id)"
                r"|report\s*(?:number|no\.?|id)"
                r"|form\s*(?:number|no\.?|id)"
                r"|electronic\s+signature\s*(?:id|number|no\.?)"
                r"|signature\s*(?:id|number|no\.?)"
                r"|رقم\s+التوقيع\s+الإلكتروني"
                r"|معرف\s+التوقيع\s+الإلكتروني"
                r"|رقم\s+المستند"
                r"|رقم\s+التقرير"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="record_checksum_field",
            entity_type=CandidateEntityType.DOCUMENT_ID,
            pattern=re.compile(
                r"(?P<label>"
                r"record\s+checksum"
                r"|record\s+hash"
                r"|document\s+checksum"
                r"|report\s+checksum"
                r"|بصمة\s+(?:السجل|المستند|التقرير)"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="insurance_number_field",
            entity_type=CandidateEntityType.INSURANCE_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"insurance\s*(?:number|no\.?|id)"
                r"|policy\s*(?:number|no\.?)"
                r"|رقم\s+التأمين"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="employee_number_field",
            entity_type=CandidateEntityType.EMPLOYEE_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"employee\s*(?:number|no\.?|id)"
                r"|staff\s*(?:number|no\.?|id)"
                r"|رقم\s+الموظف"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
        _FieldRule(
            name="student_number_field",
            entity_type=CandidateEntityType.STUDENT_NUMBER,
            pattern=re.compile(
                r"(?P<label>"
                r"student\s*(?:number|no\.?|id)"
                r"|school\s*(?:number|no\.?|id)"
                r"|رقم\s+الطالب"
                r")"
                + _VALUE_SEPARATOR
                + _IDENTIFIER_VALUE,
                flags=re.IGNORECASE,
            ),
        ),
    )

    INLINE_EMAIL_PATTERN = re.compile(
        r"(?<![A-Z0-9._%+\-])"
        r"[A-Z0-9._%+\-]+"
        r"@"
        r"[A-Z0-9.\-]+"
        r"\."
        r"[A-Z]{2,}"
        r"(?![A-Z0-9._%+\-])",
        flags=re.IGNORECASE,
    )

    INLINE_KUWAIT_PHONE_PATTERN = re.compile(
        r"(?<![0-9٠-٩۰-۹])"
        r"\+\s*965"
        r"(?:[\s().\-]*[0-9٠-٩۰-۹]){8}"
        r"(?![0-9٠-٩۰-۹])"
    )

    @classmethod
    def detect(
        cls,
        text: str,
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Detect high-confidence structured identifiers in source text.

        The returned candidates are sorted by source offset and remain in the
        PENDING state so the existing ContextValidator owns the final decision.
        """

        if not isinstance(text, str):
            raise TypeError(
                "text must be a string."
            )

        if not text:
            return ()

        candidates = []

        candidates.extend(
            cls._detect_field_candidates(text)
        )

        candidates.extend(
            cls._detect_inline_emails(text)
        )

        candidates.extend(
            cls._detect_inline_kuwait_phones(text)
        )

        return cls._deduplicate_and_sort(
            candidates
        )

    @classmethod
    def _detect_field_candidates(
        cls,
        text: str,
    ) -> list[MedNexusCandidateEntity]:
        """
        Detect identifiers that are anchored to trusted field labels.
        """

        candidates = []

        for rule in cls.FIELD_RULES:
            for match in rule.pattern.finditer(text):
                value = match.group("value")
                start, end = match.span("value")

                candidate = cls._build_candidate(
                    text=value,
                    start=start,
                    end=end,
                    source=CandidateSource.MEDNEXUS_FIELD_RULE,
                    entity_type=rule.entity_type,
                    confidence=rule.confidence,
                    raw_label=match.group("label"),
                    rule_name=rule.name,
                    metadata={
                        "detector": "deterministic_identifier_detector",
                        "detection_mode": "field",
                        "field_label": match.group("label"),
                    },
                )

                candidates.append(candidate)

        return candidates

    @classmethod
    def _detect_inline_emails(
        cls,
        text: str,
    ) -> list[MedNexusCandidateEntity]:
        """
        Detect unambiguous email addresses anywhere in the document.
        """

        return [
            cls._build_candidate(
                text=match.group(0),
                start=match.start(),
                end=match.end(),
                source=CandidateSource.MEDNEXUS_INLINE_RULE,
                entity_type=CandidateEntityType.EMAIL,
                confidence=1.0,
                raw_label="inline_email",
                rule_name="inline_email",
                metadata={
                    "detector": "deterministic_identifier_detector",
                    "detection_mode": "inline",
                },
            )
            for match in cls.INLINE_EMAIL_PATTERN.finditer(text)
        ]

    @classmethod
    def _detect_inline_kuwait_phones(
        cls,
        text: str,
    ) -> list[MedNexusCandidateEntity]:
        """
        Detect explicit Kuwait international phone numbers.

        Inline phone detection deliberately requires the +965 country code.
        Local 8-digit values without a field label remain untouched because
        they can otherwise collide with dates, accession fragments, clinical
        measurements, and other medical numeric data.
        """

        return [
            cls._build_candidate(
                text=match.group(0),
                start=match.start(),
                end=match.end(),
                source=CandidateSource.MEDNEXUS_INLINE_RULE,
                entity_type=CandidateEntityType.PHONE_NUMBER,
                confidence=1.0,
                raw_label="kuwait_phone",
                rule_name="inline_kuwait_phone",
                metadata={
                    "detector": "deterministic_identifier_detector",
                    "detection_mode": "inline",
                    "country_code": "965",
                },
            )
            for match in cls.INLINE_KUWAIT_PHONE_PATTERN.finditer(text)
        ]

    @staticmethod
    def _build_candidate(
        *,
        text: str,
        start: int,
        end: int,
        source: CandidateSource,
        entity_type: CandidateEntityType,
        confidence: float,
        raw_label: str,
        rule_name: str,
        metadata: dict,
    ) -> MedNexusCandidateEntity:
        """
        Build one immutable MedNexus deterministic candidate.
        """

        candidate_metadata = dict(metadata)
        candidate_metadata["rule_name"] = rule_name

        return MedNexusCandidateEntity(
            text=text,
            start=start,
            end=end,
            source=source,
            raw_label=raw_label,
            canonical_type=entity_type,
            confidence=confidence,
            decision=CandidateDecision.PENDING,
            normalized_label=entity_type.value,
            metadata=candidate_metadata,
        )

    @classmethod
    def _deduplicate_and_sort(
        cls,
        candidates: Iterable[MedNexusCandidateEntity],
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Remove exact duplicate spans produced by multiple deterministic rules.

        Field-aware detections are preferred over inline detections for the
        same span because the field label provides stronger document context.
        """

        source_priority = {
            CandidateSource.MEDNEXUS_FIELD_RULE: 3,
            CandidateSource.MEDNEXUS_ARABIC_RULE: 2,
            CandidateSource.MEDNEXUS_INLINE_RULE: 1,
        }

        deduplicated: dict[
            tuple[int, int, CandidateEntityType],
            MedNexusCandidateEntity,
        ] = {}

        for candidate in candidates:
            key = (
                candidate.start,
                candidate.end,
                candidate.canonical_type,
            )

            existing = deduplicated.get(key)

            if existing is None:
                deduplicated[key] = candidate
                continue

            if (
                source_priority.get(candidate.source, 0)
                > source_priority.get(existing.source, 0)
            ):
                deduplicated[key] = candidate

        return tuple(
            sorted(
                deduplicated.values(),
                key=lambda candidate: (
                    candidate.start,
                    candidate.end,
                    candidate.canonical_type.value,
                ),
            )
        )
