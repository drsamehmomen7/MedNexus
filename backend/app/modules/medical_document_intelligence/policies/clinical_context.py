import re
from typing import Dict, List, Optional, Tuple

from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.matcher import (
    ClinicalVocabularyMatcher,
)
from backend.app.modules.medical_document_intelligence.policies.clinical_vocabulary.models import (
    ClinicalCategory,
)
from backend.app.modules.medical_document_intelligence.policies.protected_terms import (
    PROTECTED_TERMS,
)


CLINICAL_SECTIONS = {
    "patient_information": [
        "Patient",
        "Patient Name",
        "Civil ID",
        "MRN",
        "Date of Birth",
    ],
    "specimen": [
        "Specimen",
        "Specimen Number",
        "Accession Number",
    ],
    "gross_description": [
        "Gross Description",
        "Macroscopic Description",
        "Macroscopic Examination",
    ],
    "microscopic_description": [
        "Microscopic Description",
        "Microscopic Examination",
        "Histological Examination",
        "Histologic Examination",
    ],
    "diagnosis": [
        "Diagnosis",
        "Final Diagnosis",
        "Impression",
        "Interpretation",
        "Comment",
    ],
    "consultant": [
        "Consultant",
        "Consultant Pathologist",
        "Reporting Physician",
        "Authorized By",
        "Approved By",
        "Validated By",
        "Verified By",
        "Reported By",
        "Signed By",
    ],
}


def normalize_heading(value: str) -> str:
    """
    Normalize a possible section heading for reliable comparison.
    """

    value = value.strip()
    value = value.rstrip(":")
    value = re.sub(r"\s+", " ", value)

    return value.lower()


SECTION_TITLE_MAP = {
    normalize_heading(title): section_name
    for section_name, titles in CLINICAL_SECTIONS.items()
    for title in titles
}


class ClinicalContextDetector:
    """
    Detect the clinical sections present in a medical document.
    """

    @staticmethod
    def detect(text: str) -> List[str]:
        detected_sections = []

        for line in text.splitlines():
            normalized_line = normalize_heading(line)

            section_name = SECTION_TITLE_MAP.get(normalized_line)

            if (
                section_name is not None
                and section_name not in detected_sections
            ):
                detected_sections.append(section_name)

        return detected_sections


class ClinicalContextProtector:
    """
    Protect clinical vocabulary inside relevant document sections.

    Protection sources:

    1. Clinical Vocabulary Engine v1
       - Structured clinical terms
       - Aliases
       - Section-aware rules
       - Document-type-aware rules

    2. Legacy protected terms
       - Preserved for backward compatibility

    Protected values are replaced temporarily before AI processing and
    restored afterwards.
    """

    _vocabulary_matcher = ClinicalVocabularyMatcher()

    @classmethod
    def protect(
        cls,
        text: str,
        document_type: Optional[str] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """
        Protect clinical vocabulary before external AI processing.

        Args:
            text:
                Original medical document text.

            document_type:
                Optional explicit document type.

                Examples:
                    laboratory_report
                    pathology_report

                When document type is not supplied, a conservative
                section-based fallback is used until automatic document
                type detection is implemented in Stage 2.

        Returns:
            protected_text:
                Text containing temporary clinical context tokens.

            mapping:
                Mapping between every token and its original value.
        """

        if not isinstance(text, str):
            raise TypeError("Text must be a string.")

        mapping: Dict[str, str] = {}

        protected_lines: List[str] = []
        current_section: Optional[str] = None
        token_number = 1

        for line in text.splitlines(keepends=True):
            line_without_break = line.rstrip("\r\n")
            line_break = line[len(line_without_break):]

            normalized_line = normalize_heading(line_without_break)

            detected_section = SECTION_TITLE_MAP.get(normalized_line)

            if detected_section is not None:
                current_section = detected_section
                protected_lines.append(line)
                continue

            protected_line = line_without_break

            (
                protected_line,
                vocabulary_mapping,
                token_number,
            ) = cls._protect_vocabulary_terms(
                text=protected_line,
                section=current_section,
                document_type=document_type,
                starting_number=token_number,
            )

            mapping.update(vocabulary_mapping)

            (
                protected_line,
                legacy_mapping,
                token_number,
            ) = cls._protect_legacy_terms(
                text=protected_line,
                section=current_section,
                starting_number=token_number,
            )

            mapping.update(legacy_mapping)

            protected_lines.append(
                protected_line + line_break
            )

        protected_text = "".join(protected_lines)

        return protected_text, mapping

    @classmethod
    def _protect_vocabulary_terms(
        cls,
        *,
        text: str,
        section: Optional[str],
        document_type: Optional[str],
        starting_number: int,
    ) -> Tuple[str, Dict[str, str], int]:
        """
        Protect terms supplied by Clinical Vocabulary Engine v1.
        """

        protected_text = text
        mapping: Dict[str, str] = {}
        token_number = starting_number

        candidate_document_types = cls._resolve_candidate_document_types(
            section=section,
            document_type=document_type,
        )

        for candidate_document_type in candidate_document_types:
            (
                protected_text,
                candidate_mapping,
                token_number,
            ) = cls._vocabulary_matcher.protect_matches(
                protected_text,
                section=section,
                document_type=candidate_document_type,
                excluded_categories=(
                    ClinicalCategory.CLINICAL_OCCUPATION,
                    ClinicalCategory.CLINICAL_SPECIALTY,
                ),
                token_prefix="__CTX_",
                starting_number=token_number,
            )

            mapping.update(candidate_mapping)

        # Common vocabulary terms have no document-type restriction.
        (
            protected_text,
            common_mapping,
            token_number,
        ) = cls._vocabulary_matcher.protect_matches(
            protected_text,
            section=section,
            document_type=None,
            excluded_categories=(
                ClinicalCategory.CLINICAL_OCCUPATION,
                ClinicalCategory.CLINICAL_SPECIALTY,
            ),
            token_prefix="__CTX_",
            starting_number=token_number,
        )

        mapping.update(common_mapping)

        return protected_text, mapping, token_number

    @staticmethod
    def _resolve_candidate_document_types(
        *,
        section: Optional[str],
        document_type: Optional[str],
    ) -> Tuple[str, ...]:
        """
        Resolve document types used for vocabulary matching.

        Explicit document type always takes priority.

        Until Stage 2 introduces automatic document type detection,
        section-based fallback rules allow safe protection of the current
        laboratory and pathology vocabulary.
        """

        if document_type:
            return (document_type,)

        if section in {
            "gross_description",
            "microscopic_description",
            "diagnosis",
        }:
            return ("pathology_report",)

        if section == "consultant":
            return (
                "laboratory_report",
                "pathology_report",
            )

        return ()

    @staticmethod
    def _protect_legacy_terms(
        *,
        text: str,
        section: Optional[str],
        starting_number: int,
    ) -> Tuple[str, Dict[str, str], int]:
        """
        Protect terms from the original PROTECTED_TERMS dictionary.
        """

        mapping: Dict[str, str] = {}
        token_number = starting_number
        protected_text = text

        section_terms = PROTECTED_TERMS.get(
            section,
            set(),
        )

        sorted_terms = sorted(
            section_terms,
            key=len,
            reverse=True,
        )

        for term in sorted_terms:
            pattern = re.compile(
                rf"\b{re.escape(term)}\b",
                flags=re.IGNORECASE,
            )

            def replace_match(match: re.Match) -> str:
                nonlocal token_number

                token = f"__CTX_{token_number:04d}__"

                mapping[token] = match.group(0)
                token_number += 1

                return token

            protected_text = pattern.sub(
                replace_match,
                protected_text,
            )

        return protected_text, mapping, token_number

    @staticmethod
    def restore(
        text: str,
        mapping: Dict[str, str],
    ) -> str:
        """
        Restore original clinical vocabulary after AI processing.
        """

        restored_text = text

        for token, original_value in mapping.items():
            restored_text = restored_text.replace(
                token,
                original_value,
            )

        return restored_text
