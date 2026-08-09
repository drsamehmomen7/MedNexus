import re
from dataclasses import dataclass
from typing import List, Optional, Pattern, Sequence

from .models import ClinicalTerm, MatchMode, Specialty
from .registry import VocabularyRegistry, registry


@dataclass(frozen=True)
class ClinicalVocabularyMatch:
    """
    Represents one clinical vocabulary match found inside medical text.
    """

    text: str
    start: int
    end: int
    term: ClinicalTerm
    matched_value: str


class ClinicalVocabularyService:
    """
    Searches medical text using registered clinical vocabulary profiles.

    The service supports:

    - Primary terms and aliases
    - Case-sensitive and case-insensitive matching
    - Exact, word, and phrase matching
    - Clinical section filtering
    - Document-type filtering
    - Specialty filtering
    - Overlap prevention

    It is intentionally independent from OpenMed and the de-identification
    pipeline so it can later support MedCAT, scispaCy, UMLS, and SNOMED CT.
    """

    def __init__(
        self,
        vocabulary_registry: Optional[VocabularyRegistry] = None,
    ):
        self.registry = vocabulary_registry or registry

    def find_matches(
        self,
        text: str,
        *,
        section: Optional[str] = None,
        document_type: Optional[str] = None,
        specialties: Optional[Sequence[Specialty]] = None,
    ) -> List[ClinicalVocabularyMatch]:
        """
        Find clinical vocabulary matches inside the supplied text.

        Args:
            text:
                Medical text to search.

            section:
                Optional current clinical section.

            document_type:
                Optional document type.

            specialties:
                Optional list of specialties to include.
                Common vocabulary is always included when specialty
                filtering is active.

        Returns:
            Ordered list of non-overlapping clinical vocabulary matches.
        """

        if not isinstance(text, str):
            raise TypeError("Text must be a string.")

        if not text:
            return []

        candidate_terms = self._get_candidate_terms(
            section=section,
            document_type=document_type,
            specialties=specialties,
        )

        matches: List[ClinicalVocabularyMatch] = []

        for term in candidate_terms:
            for matched_value in term.all_terms():
                pattern = self._compile_pattern(
                    value=matched_value,
                    match_mode=term.match_mode,
                    case_sensitive=term.case_sensitive,
                )

                for match in pattern.finditer(text):
                    matches.append(
                        ClinicalVocabularyMatch(
                            text=match.group(0),
                            start=match.start(),
                            end=match.end(),
                            term=term,
                            matched_value=matched_value,
                        )
                    )

        matches.sort(
            key=lambda item: (
                item.start,
                -(item.end - item.start),
                item.term.term.lower(),
            )
        )

        return self._remove_overlapping_matches(matches)

    def contains_clinical_term(
        self,
        text: str,
        *,
        section: Optional[str] = None,
        document_type: Optional[str] = None,
        specialties: Optional[Sequence[Specialty]] = None,
    ) -> bool:
        """
        Return True when at least one clinical vocabulary match is found.
        """

        return bool(
            self.find_matches(
                text,
                section=section,
                document_type=document_type,
                specialties=specialties,
            )
        )

    def get_matched_terms(
        self,
        text: str,
        *,
        section: Optional[str] = None,
        document_type: Optional[str] = None,
        specialties: Optional[Sequence[Specialty]] = None,
    ) -> List[ClinicalTerm]:
        """
        Return unique ClinicalTerm objects matched inside the text.

        Order follows the first appearance of each term.
        """

        matches = self.find_matches(
            text,
            section=section,
            document_type=document_type,
            specialties=specialties,
        )

        unique_terms: List[ClinicalTerm] = []
        seen_terms = set()

        for match in matches:
            identity = (
                match.term.term.lower(),
                match.term.specialty,
                match.term.category,
            )

            if identity in seen_terms:
                continue

            seen_terms.add(identity)
            unique_terms.append(match.term)

        return unique_terms

    def _get_candidate_terms(
        self,
        *,
        section: Optional[str],
        document_type: Optional[str],
        specialties: Optional[Sequence[Specialty]],
    ) -> List[ClinicalTerm]:
        terms = self.registry.all_terms()

        allowed_specialties = self._normalize_specialties(specialties)

        candidate_terms: List[ClinicalTerm] = []

        for term in terms:
            if allowed_specialties is not None:
                if (
                    term.specialty != Specialty.COMMON
                    and term.specialty not in allowed_specialties
                ):
                    continue

            if not term.applies_to_section(section):
                continue

            if not term.applies_to_document_type(document_type):
                continue

            candidate_terms.append(term)

        return candidate_terms

    @staticmethod
    def _normalize_specialties(
        specialties: Optional[Sequence[Specialty]],
    ) -> Optional[set]:
        if specialties is None:
            return None

        normalized_specialties = set()

        for specialty in specialties:
            if not isinstance(specialty, Specialty):
                raise TypeError(
                    "Specialties must contain Specialty enum values."
                )

            normalized_specialties.add(specialty)

        return normalized_specialties

    @staticmethod
    def _compile_pattern(
        *,
        value: str,
        match_mode: MatchMode,
        case_sensitive: bool,
    ) -> Pattern[str]:
        escaped_value = re.escape(value)

        if match_mode == MatchMode.EXACT:
            expression = rf"\A{escaped_value}\Z"

        elif match_mode == MatchMode.WORD:
            expression = rf"(?<!\w){escaped_value}(?!\w)"

        elif match_mode == MatchMode.PHRASE:
            expression = rf"(?<!\w){escaped_value}(?!\w)"

        else:
            raise ValueError(
                f"Unsupported clinical vocabulary match mode: {match_mode}"
            )

        flags = 0 if case_sensitive else re.IGNORECASE

        return re.compile(expression, flags)

    @staticmethod
    def _remove_overlapping_matches(
        matches: List[ClinicalVocabularyMatch],
    ) -> List[ClinicalVocabularyMatch]:
        """
        Keep the longest match when multiple matches overlap.

        Example:

            Doctor
            Clinical Doctor

        If both begin at the same position, the longer match is retained.
        """

        accepted_matches: List[ClinicalVocabularyMatch] = []

        for candidate in matches:
            overlaps_existing = any(
                candidate.start < accepted.end
                and candidate.end > accepted.start
                for accepted in accepted_matches
            )

            if overlaps_existing:
                continue

            accepted_matches.append(candidate)

        return accepted_matches