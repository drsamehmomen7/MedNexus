from __future__ import annotations

import re
from typing import Iterable, Tuple

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateDecision,
    CandidateEntityType,
    CandidateSource,
    MedNexusCandidateEntity,
)


class ContextValidator:
    """
    Validate MedNexus candidate entities against medical-document context.

    External engine detections are never considered authoritative.

    This validator decides whether a candidate should be:

        ACCEPT:
            Valid identity information that can proceed to policy handling.

        REJECT:
            A false-positive detection that must not alter the document.

        KEEP:
            A valid entity whose professional or clinical context requires
            preservation.

        REVIEW_REQUIRED:
            A potentially sensitive candidate that cannot be resolved safely.

    The validator does not modify document text and does not apply the final
    privacy transformation.
    """

    STRONG_IDENTIFIER_TYPES = {
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
        CandidateEntityType.PHONE_NUMBER,
        CandidateEntityType.EMAIL,
        CandidateEntityType.ADDRESS,
        CandidateEntityType.DATE_OF_BIRTH,
    }

    ROLE_SPECIFIC_NAME_TYPES = {
        CandidateEntityType.PATIENT_NAME,
        CandidateEntityType.PHYSICIAN_NAME,
        CandidateEntityType.NURSE_NAME,
        CandidateEntityType.GUARDIAN_NAME,
        CandidateEntityType.RELATIVE_NAME,
        CandidateEntityType.EMPLOYEE_NAME,
        CandidateEntityType.STUDENT_NAME,
    }

    SAFE_PROFESSIONAL_ROLE_TERMS = {
        "radiologist",
        "reporting radiologist",
        "physician",
        "reporting physician",
        "attending physician",
        "referring physician",
        "consultant",
        "consultant pathologist",
        "pathologist",
        "clinician",
        "doctor",
        "surgeon",
        "anesthetist",
        "anaesthetist",
        "nurse",
        "registered nurse",
        "school nurse",
        "vaccinator",
        "public health officer",
        "laboratory technician",
        "radiology technician",
        "medical officer",
        "occupational physician",
        "obstetrician",
        "intensivist",
        "طبيب",
        "الطبيب",
        "طبيب الأشعة",
        "طبيب اشعة",
        "استشاري",
        "الاستشاري",
        "استشاري الأشعة",
        "استشاري الباثولوجي",
        "أخصائي",
        "الأخصائي",
        "جراح",
        "طبيب التخدير",
        "ممرض",
        "الممرض",
        "ممرضة",
        "الممرضة",
        "مسؤول الصحة العامة",
    }

    SAFE_DOCUMENT_TERMS = {
        "document",
        "medical document",
        "medical record",
        "medical report",
        "clinical report",
        "laboratory report",
        "radiology report",
        "pathology report",
        "discharge summary",
        "operative note",
        "referral letter",
        "confidential",
        "confidential medical document",
        "hospital information system",
        "health information system",
        "electronic medical record",
        "electronic health record",
        "report",
        "record",
        "medical",
        "clinical",
        "مستند",
        "مستند طبي",
        "تقرير",
        "تقرير طبي",
        "سجل طبي",
        "نظام معلومات المستشفى",
        "نظام المعلومات الصحية",
        "سري",
    }

    PROFESSIONAL_CONTEXT_PATTERNS = (
        r"\breporting\s+radiologist\b",
        r"\breporting\s+physician\b",
        r"\badmitting\s+consultant\b",
        r"\bconsultant\s+pathologist\b",
        r"\battending\s+physician\b",
        r"\breferring\s+physician\b",
        r"\bauthorized\s+by\b",
        r"\bapproved\s+by\b",
        r"\bverified\s+by\b",
        r"\breported\s+by\b",
        r"\bsigned\s+by\b",
        r"طبيب\s+الأشعة",
        r"استشاري\s+الأشعة",
        r"استشاري\s+الباثولوجي",
        r"اعتمد\s+بواسطة",
        r"تم\s+الاعتماد\s+بواسطة",
    )

    PATIENT_FIELD_PATTERNS = (
        r"patient(?:\s+full)?\s+name",
        r"patient",
        r"name\s+of\s+patient",
        r"اسم\s+المريض",
        r"اسم\s+المريضة",
    )

    PHONE_PATTERN = re.compile(
        r"""
        (?:\+\s*)?
        [0-9٠-٩۰-۹]
        (?:[\s().\-/]*[0-9٠-٩۰-۹]){6,14}
        """,
        flags=re.VERBOSE,
    )

    EMAIL_PATTERN = re.compile(
        r"""
        [A-Z0-9._%+\-]+
        @
        [A-Z0-9.\-]+
        \.[A-Z]{2,}
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    CIVIL_ID_PATTERN = re.compile(
        r"(?<!\d)\d{12}(?!\d)"
    )

    MEDICAL_IDENTIFIER_PATTERN = re.compile(
        r"""
        (?:
            MRN
            |
            VIS
            |
            ACC
            |
            SP
            |
            LAB
            |
            DOC
            |
            EMP
            |
            STU
        )
        [\-_]?
        [A-Z0-9\-]{3,}
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    RAW_ENGINE_PLACEHOLDER_PATTERN = re.compile(
        r"""
        ^
        \[
        (?:
            first_name
            |
            last_name
            |
            middle_name
            |
            user_name
            |
            username
            |
            occupation
            |
            bic
            |
            organization
            |
            location
            |
            person
            |
            name
        )
        \]
        $
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    @classmethod
    def validate(
        cls,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ) -> MedNexusCandidateEntity:
        """
        Validate one candidate against the source document.

        Existing final decisions are preserved.
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

        if candidate.decision != CandidateDecision.PENDING:
            return candidate

        if not candidate.matches_source_text(source_text):
            return candidate.with_decision(
                CandidateDecision.REVIEW_REQUIRED,
                reason=(
                    "Candidate offsets do not match the source text."
                ),
            )

        decision, reason = cls._resolve_decision(
            candidate=candidate,
            source_text=source_text,
        )

        return candidate.with_decision(
            decision,
            reason=reason,
        )

    @classmethod
    def validate_many(
        cls,
        candidates: Iterable[MedNexusCandidateEntity],
        source_text: str,
    ) -> Tuple[MedNexusCandidateEntity, ...]:
        """
        Validate multiple candidates while preserving their order.
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
            cls.validate(
                candidate=candidate,
                source_text=source_text,
            )
            for candidate in candidates
        )

    @classmethod
    def _resolve_decision(
        cls,
        *,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ):
        """
        Resolve the appropriate MedNexus decision.
        """

        canonical_type = candidate.canonical_type
        normalized_text = cls._normalize_text(
            candidate.text
        )

        if cls._is_raw_engine_placeholder(
            candidate.text
        ):
            return (
                CandidateDecision.REJECT,
                "Raw external-engine placeholders are not valid source entities.",
            )

        if canonical_type in cls.STRONG_IDENTIFIER_TYPES:
            return cls._validate_strong_identifier(
                candidate=candidate,
            )

        if canonical_type == CandidateEntityType.PATIENT_NAME:
            return (
                CandidateDecision.ACCEPT,
                "Patient name confirmed by MedNexus role-aware context.",
            )

        if canonical_type in {
            CandidateEntityType.GUARDIAN_NAME,
            CandidateEntityType.RELATIVE_NAME,
            CandidateEntityType.EMPLOYEE_NAME,
            CandidateEntityType.STUDENT_NAME,
        }:
            return (
                CandidateDecision.ACCEPT,
                (
                    f"Role-specific identifying name confirmed as "
                    f"'{canonical_type.value}'."
                ),
            )

        if canonical_type in {
            CandidateEntityType.PHYSICIAN_NAME,
            CandidateEntityType.NURSE_NAME,
        }:
            return (
                CandidateDecision.ACCEPT,
                (
                    "Healthcare professional name is valid and accepted "
                    "for policy evaluation."
                ),
            )

        if canonical_type == CandidateEntityType.PROFESSIONAL_ROLE:
            if (
                normalized_text
                in cls.SAFE_PROFESSIONAL_ROLE_TERMS
                or cls._has_professional_context(
                    candidate=candidate,
                    source_text=source_text,
                )
            ):
                return (
                    CandidateDecision.REJECT,
                    (
                        "Professional role terminology is not patient-identifying "
                        "information."
                    ),
                )

            return (
                CandidateDecision.REVIEW_REQUIRED,
                "Professional-role candidate could not be resolved safely.",
            )

        if canonical_type == CandidateEntityType.UNKNOWN:
            if (
                normalized_text in cls.SAFE_DOCUMENT_TERMS
                or cls._is_document_context_false_positive(
                    candidate=candidate,
                    source_text=source_text,
                )
            ):
                return (
                    CandidateDecision.REJECT,
                    (
                        "Candidate is document or clinical terminology, not "
                        "identity information."
                    ),
                )

            return (
                CandidateDecision.REVIEW_REQUIRED,
                "Unknown candidate requires MedNexus review.",
            )

        if canonical_type == CandidateEntityType.PERSON_NAME:
            if cls._is_patient_context(
                candidate=candidate,
                source_text=source_text,
            ):
                return (
                    CandidateDecision.ACCEPT,
                    "Generic person name appears in a patient field.",
                )

            return (
                CandidateDecision.REVIEW_REQUIRED,
                (
                    "Generic person name could not be assigned a safe "
                    "clinical role."
                ),
            )

        if canonical_type in {
            CandidateEntityType.ORGANIZATION,
            CandidateEntityType.LOCATION,
        }:
            return (
                CandidateDecision.REVIEW_REQUIRED,
                (
                    f"'{canonical_type.value}' requires document-specific "
                    "policy evaluation."
                ),
            )

        if canonical_type in {
            CandidateEntityType.ADMISSION_DATE,
            CandidateEntityType.DISCHARGE_DATE,
            CandidateEntityType.COLLECTION_DATE,
            CandidateEntityType.EXAM_DATE,
            CandidateEntityType.GENERAL_DATE,
        }:
            return (
                CandidateDecision.ACCEPT,
                "Date candidate accepted for policy evaluation.",
            )

        return (
            CandidateDecision.REVIEW_REQUIRED,
            "Candidate type has no finalized MedNexus validation rule.",
        )

    @classmethod
    def _validate_strong_identifier(
        cls,
        *,
        candidate: MedNexusCandidateEntity,
    ):
        """
        Validate strongly identifying entity types.
        """

        entity_type = candidate.canonical_type
        value = candidate.text.strip()

        if entity_type == CandidateEntityType.PHONE_NUMBER:
            if cls.PHONE_PATTERN.fullmatch(value):
                return (
                    CandidateDecision.ACCEPT,
                    "Phone number matched a MedNexus contact-number pattern.",
                )

            return (
                CandidateDecision.REVIEW_REQUIRED,
                "Phone candidate did not match a valid contact-number pattern.",
            )

        if entity_type == CandidateEntityType.EMAIL:
            if cls.EMAIL_PATTERN.fullmatch(value):
                return (
                    CandidateDecision.ACCEPT,
                    "Email address matched the MedNexus email pattern.",
                )

            return (
                CandidateDecision.REVIEW_REQUIRED,
                "Email candidate did not match a valid email pattern.",
            )

        if entity_type == CandidateEntityType.CIVIL_ID:
            normalized_digits = cls._normalize_digits(value)

            if cls.CIVIL_ID_PATTERN.fullmatch(
                normalized_digits
            ):
                return (
                    CandidateDecision.ACCEPT,
                    "Civil ID matched the required 12-digit format.",
                )

            return (
                CandidateDecision.REVIEW_REQUIRED,
                "Civil ID candidate did not match the expected format.",
            )

        if entity_type in {
            CandidateEntityType.MRN,
            CandidateEntityType.VISIT_NUMBER,
            CandidateEntityType.ACCESSION_NUMBER,
            CandidateEntityType.SPECIMEN_NUMBER,
            CandidateEntityType.LAB_NUMBER,
            CandidateEntityType.DOCUMENT_ID,
            CandidateEntityType.EMPLOYEE_NUMBER,
            CandidateEntityType.STUDENT_NUMBER,
        }:
            if (
                len(value) >= 4
                and (
                    cls.MEDICAL_IDENTIFIER_PATTERN.search(value)
                    or any(character.isdigit() for character in value)
                )
            ):
                return (
                    CandidateDecision.ACCEPT,
                    (
                        f"Structured identifier confirmed as "
                        f"'{entity_type.value}'."
                    ),
                )

            return (
                CandidateDecision.REVIEW_REQUIRED,
                "Structured identifier candidate appears incomplete.",
            )

        return (
            CandidateDecision.ACCEPT,
            (
                f"Strong identifier accepted as "
                f"'{entity_type.value}'."
            ),
        )

    @classmethod
    def _is_document_context_false_positive(
        cls,
        *,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ) -> bool:
        """
        Detect false positives such as DOCUMENT classified as BIC.
        """

        raw_label = cls._normalize_text(
            candidate.raw_label or ""
        )

        canonical_label = cls._normalize_text(
            str(
                candidate.metadata.get(
                    "openmed_canonical_label",
                    "",
                )
            )
        )

        if raw_label not in {
            "bic",
            "swift",
            "iban",
            "occupation",
        } and canonical_label not in {
            "bic",
            "swift",
            "iban",
            "occupation",
        }:
            return False

        context = cls._context_window(
            candidate=candidate,
            source_text=source_text,
            radius=80,
        )

        normalized_context = cls._normalize_text(
            context
        )

        return any(
            term in normalized_context
            for term in cls.SAFE_DOCUMENT_TERMS
        )

    @classmethod
    def _has_professional_context(
        cls,
        *,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ) -> bool:
        """
        Check whether a role candidate is used as a medical role label.
        """

        context = cls._context_window(
            candidate=candidate,
            source_text=source_text,
            radius=60,
        )

        return any(
            re.search(
                pattern,
                context,
                flags=re.IGNORECASE,
            )
            for pattern in cls.PROFESSIONAL_CONTEXT_PATTERNS
        )

    @classmethod
    def _is_patient_context(
        cls,
        *,
        candidate: MedNexusCandidateEntity,
        source_text: str,
    ) -> bool:
        """
        Check whether a generic name appears in a patient field.
        """

        prefix_start = max(
            0,
            candidate.start - 100,
        )

        prefix = source_text[
            prefix_start:candidate.start
        ]

        normalized_prefix = cls._normalize_text(
            prefix
        )

        return any(
            re.search(
                pattern,
                normalized_prefix,
                flags=re.IGNORECASE,
            )
            for pattern in cls.PATIENT_FIELD_PATTERNS
        )

    @staticmethod
    def _context_window(
        *,
        candidate: MedNexusCandidateEntity,
        source_text: str,
        radius: int,
    ) -> str:
        """
        Return nearby source context around a candidate.
        """

        start = max(
            0,
            candidate.start - radius,
        )

        end = min(
            len(source_text),
            candidate.end + radius,
        )

        return source_text[start:end]

    @classmethod
    def _is_raw_engine_placeholder(
        cls,
        value: str,
    ) -> bool:
        """
        Return True for raw OpenMed-style placeholder values.
        """

        return bool(
            cls.RAW_ENGINE_PLACEHOLDER_PATTERN.fullmatch(
                value.strip()
            )
        )

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        """
        Normalize English or Arabic text for context comparison.
        """

        value = str(value).strip().lower()

        value = re.sub(
            r"[\[\]<>():{}]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @staticmethod
    def _normalize_digits(
        value: str,
    ) -> str:
        """
        Convert Arabic-Indic digits into Western digits.
        """

        translation_table = str.maketrans(
            {
                "٠": "0",
                "١": "1",
                "٢": "2",
                "٣": "3",
                "٤": "4",
                "٥": "5",
                "٦": "6",
                "٧": "7",
                "٨": "8",
                "٩": "9",
                "۰": "0",
                "۱": "1",
                "۲": "2",
                "۳": "3",
                "۴": "4",
                "۵": "5",
                "۶": "6",
                "۷": "7",
                "۸": "8",
                "۹": "9",
            }
        )

        return value.translate(
            translation_table
        )
