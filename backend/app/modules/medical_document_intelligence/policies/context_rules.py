import re
from typing import List, Tuple

from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.schemas.detected_entity import (
    DetectedEntity,
)


class ContextRuleEngine:
    """
    Rule-based healthcare context detection.

    Supports:

    1. Field-aware detection:
       Patient Name:
       Ahmed Hassan

    2. Inline identifier detection:
       MRN-123456

    All results are returned using the unified MedNexus
    DetectedEntity contract.
    """

    FIELD_RULES: List[Tuple[re.Pattern, MedicalContextEntity]] = [
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>
                    patient
                    |
                    patient[ \t]+name
                )
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.PATIENT_NAME,
        ),
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>civil[ \t]+id)
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.CIVIL_ID,
        ),
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>
                    mrn
                    |
                    medical[ \t]+record[ \t]+number
                )
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.MRN,
        ),
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>visit[ \t]+number)
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.VISIT_NUMBER,
        ),
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>lab(?:oratory)?[ \t]+number)
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.LAB_NUMBER,
        ),
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>accession[ \t]+number)
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.ACCESSION_NUMBER,
        ),
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>specimen[ \t]+number)
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.SPECIMEN_NUMBER,
        ),
        (
            re.compile(
                r"""
                ^[ \t]*
                (?P<label>
                    consultant
                    |
                    physician
                    |
                    doctor
                    |
                    consultant[ \t]+pathologist
                    |
                    attending[ \t]+physician
                    |
                    requesting[ \t]+physician
                    |
                    authorized[ \t]+by
                    |
                    authorized[ \t]+physician
                    |
                    reported[ \t]+by
                )
                [ \t]*:[ \t]*
                (?:\r?\n[ \t]*)*
                (?P<value>Dr\.[ \t]+[^\r\n=]+?)
                [ \t]*$
                """,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            ),
            MedicalContextEntity.PHYSICIAN_NAME,
        ),
    ]

    INLINE_RULES: List[Tuple[re.Pattern, MedicalContextEntity]] = [
        (
            re.compile(
                r"\bMRN(?:[-:][ \t]*|[ \t]+)[A-Za-z0-9][A-Za-z0-9-]*\b",
                re.IGNORECASE,
            ),
            MedicalContextEntity.MRN,
        ),
        
            (
    	   re.compile(
       	       r"\bLAB[-:][ \t]*[A-Za-z0-9][A-Za-z0-9-]*\b",
               re.IGNORECASE,
         ),
           MedicalContextEntity.LAB_NUMBER,
   
        ),
        (
            re.compile(
                r"\bVIS(?:[-:][ \t]*|[ \t]+)[A-Za-z0-9][A-Za-z0-9-]*\b",
                re.IGNORECASE,
            ),
            MedicalContextEntity.VISIT_NUMBER,
        ),
        (
            re.compile(
                r"\bACC(?:[-:][ \t]*|[ \t]+)[A-Za-z0-9][A-Za-z0-9-]*\b",
                re.IGNORECASE,
            ),
            MedicalContextEntity.ACCESSION_NUMBER,
        ),
        (
            re.compile(
                r"\bSP(?:[-:][ \t]*|[ \t]+)[A-Za-z0-9][A-Za-z0-9-]*\b",
                re.IGNORECASE,
            ),
            MedicalContextEntity.SPECIMEN_NUMBER,
        ),
    ]

    RULES = INLINE_RULES

    @classmethod
    def detect(cls, text: str) -> List[DetectedEntity]:
        """
        Detect healthcare entities using field-aware and inline rules.

        Returns:
            A list of DetectedEntity objects.

        The field label is preserved as metadata, while only the
        field value is considered the detected sensitive span.
        """

        if not isinstance(text, str) or not text.strip():
            return []

        results: List[DetectedEntity] = []
        detected_spans = set()

        for pattern, entity in cls.FIELD_RULES:
            for match in pattern.finditer(text):
                raw_value = match.group("value")
                value = raw_value.strip()

                if not value:
                    continue

                raw_start, raw_end = match.span("value")

                leading_whitespace = len(raw_value) - len(raw_value.lstrip())
                trailing_whitespace = len(raw_value) - len(raw_value.rstrip())

                value_start = raw_start + leading_whitespace
                value_end = raw_end - trailing_whitespace

                detection_key = (
                    value_start,
                    value_end,
                    entity,
                )

                if detection_key in detected_spans:
                    continue

                label = match.group("label").strip()

                detected_spans.add(detection_key)

                results.append(
                    DetectedEntity(
                        entity=entity,
                        value=value,
                        start=value_start,
                        end=value_end,
                        source="context_rule_engine.field",
                        confidence=1.0,
                        label=label,
                        normalized_label=cls._normalize_label(label),
                    )
                )

        for pattern, entity in cls.INLINE_RULES:
            for match in pattern.finditer(text):
                matched_value = match.group().strip()
                value_start, value_end = match.span()

                detection_key = (
                    value_start,
                    value_end,
                    entity,
                )

                if detection_key in detected_spans:
                    continue

                detected_spans.add(detection_key)

                results.append(
                    DetectedEntity(
                        entity=entity,
                        value=matched_value,
                        start=value_start,
                        end=value_end,
                        source="context_rule_engine.inline",
                        confidence=1.0,
                    )
                )

        results.sort(
            key=lambda detected: (
                detected.start,
                detected.end,
                detected.entity.name,
            )
        )

        return results

    @staticmethod
    def _normalize_label(label: str) -> str:
        """
        Convert a source field label into a normalized metadata value.

        Example:
            "Patient Name" -> "patient_name"
        """

        normalized = re.sub(
            r"[^a-zA-Z0-9]+",
            "_",
            label.strip().lower(),
        )

        return normalized.strip("_")