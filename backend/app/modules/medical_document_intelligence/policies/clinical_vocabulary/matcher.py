from typing import Dict, List, Optional, Sequence, Tuple

from .models import Specialty
from .registry import VocabularyRegistry
from .service import (
    ClinicalVocabularyMatch,
    ClinicalVocabularyService,
)
from .vocabularies.common import build_common_vocabulary
from .vocabularies.laboratory import build_laboratory_vocabulary
from .vocabularies.pathology import build_pathology_vocabulary


class ClinicalVocabularyMatcher:
    """
    Provides a simple matching interface for the clinical context protector.

    The matcher owns the default MedNexus local vocabulary registry and hides
    registry and service implementation details from the de-identification
    pipeline.

    Future vocabulary profiles can be added to build_default_registry()
    without changing ClinicalContextProtector.
    """

    def __init__(
        self,
        vocabulary_registry: Optional[VocabularyRegistry] = None,
    ):
        self.registry = (
            vocabulary_registry
            if vocabulary_registry is not None
            else self.build_default_registry()
        )

        self.service = ClinicalVocabularyService(
            vocabulary_registry=self.registry,
        )

    @staticmethod
    def build_default_registry() -> VocabularyRegistry:
        """
        Build the default MedNexus local clinical vocabulary registry.
        """

        vocabulary_registry = VocabularyRegistry()

        vocabulary_registry.register(
            build_common_vocabulary()
        )

        vocabulary_registry.register(
            build_laboratory_vocabulary()
        )

        vocabulary_registry.register(
            build_pathology_vocabulary()
        )

        return vocabulary_registry

    def find_matches(
        self,
        text: str,
        *,
        section: Optional[str] = None,
        document_type: Optional[str] = None,
        specialties: Optional[Sequence[Specialty]] = None,
    ) -> List[ClinicalVocabularyMatch]:
        """
        Find clinical vocabulary matches in the supplied text.
        """

        return self.service.find_matches(
            text,
            section=section,
            document_type=document_type,
            specialties=specialties,
        )

    def contains_match(
        self,
        text: str,
        *,
        section: Optional[str] = None,
        document_type: Optional[str] = None,
        specialties: Optional[Sequence[Specialty]] = None,
    ) -> bool:
        """
        Return True when the supplied text contains a clinical vocabulary term.
        """

        return self.service.contains_clinical_term(
            text,
            section=section,
            document_type=document_type,
            specialties=specialties,
        )

    def protect_matches(
        self,
        text: str,
        *,
        section: Optional[str] = None,
        document_type: Optional[str] = None,
        specialties: Optional[Sequence[Specialty]] = None,
        token_prefix: str = "__CVE_",
        starting_number: int = 1,
    ) -> Tuple[str, Dict[str, str], int]:
        """
        Replace matched clinical terms with temporary protection tokens.

        Tokens are numbered according to their original left-to-right
        appearance in the text.

        Returns:
            protected_text:
                Text after replacing clinical terms with tokens.

            mapping:
                Mapping between protection tokens and original matched text.

            next_token_number:
                Next available token number after all replacements.
        """

        if not isinstance(text, str):
            raise TypeError("Text must be a string.")

        if not isinstance(starting_number, int):
            raise TypeError("Starting number must be an integer.")

        if starting_number < 1:
            raise ValueError("Starting number must be greater than zero.")

        if not isinstance(token_prefix, str) or not token_prefix:
            raise ValueError("Token prefix must not be empty.")

        matches = self.find_matches(
            text,
            section=section,
            document_type=document_type,
            specialties=specialties,
        )

        if not matches:
            return text, {}, starting_number

        mapping: Dict[str, str] = {}
        replacements = []
        token_number = starting_number

        # Assign token numbers in normal left-to-right text order.
        for match in matches:
            token = f"{token_prefix}{token_number:04d}__"

            mapping[token] = match.text

            replacements.append(
                (
                    match.start,
                    match.end,
                    token,
                )
            )

            token_number += 1

        protected_text = text

        # Apply replacements from right to left so character positions
        # from the original text remain valid.
        for start, end, token in reversed(replacements):
            protected_text = (
                protected_text[:start]
                + token
                + protected_text[end:]
            )

        return protected_text, mapping, token_number