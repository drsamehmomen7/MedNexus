from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple


class ClinicalCategory(str, Enum):
    """
    High-level categories for clinical vocabulary terms.

    These categories describe the clinical meaning of a term and are
    independent from privacy entity categories.
    """

    CLINICAL_SPECIALTY = "clinical_specialty"
    CLINICAL_OCCUPATION = "clinical_occupation"
    ANATOMY = "anatomy"
    DIAGNOSIS = "diagnosis"
    PROCEDURE = "procedure"
    MEDICATION = "medication"
    LABORATORY_TEST = "laboratory_test"
    IMAGING_TERM = "imaging_term"
    PATHOLOGY_TERM = "pathology_term"
    MICROBIOLOGY_TERM = "microbiology_term"
    CLINICAL_DESCRIPTOR = "clinical_descriptor"
    OTHER = "other"


class Specialty(str, Enum):
    """
    Medical specialties supported by the local vocabulary registry.

    The COMMON value is used for terms that apply across multiple
    specialties or document types.
    """

    COMMON = "common"
    LABORATORY_MEDICINE = "laboratory_medicine"
    PATHOLOGY = "pathology"
    RADIOLOGY = "radiology"
    CARDIOLOGY = "cardiology"
    NEUROLOGY = "neurology"
    ONCOLOGY = "oncology"
    SURGERY = "surgery"
    EMERGENCY_MEDICINE = "emergency_medicine"
    INTERNAL_MEDICINE = "internal_medicine"
    PEDIATRICS = "pediatrics"
    OBSTETRICS_GYNECOLOGY = "obstetrics_gynecology"
    PHARMACY = "pharmacy"
    MICROBIOLOGY = "microbiology"
    OTHER = "other"


class MatchMode(str, Enum):
    """
    Defines how a clinical term should be matched inside medical text.
    """

    EXACT = "exact"
    WORD = "word"
    PHRASE = "phrase"


@dataclass(frozen=True)
class ClinicalTerm:
    """
    Structured representation of a protected clinical term.

    ClinicalTerm is designed to support the current local curated
    vocabulary and future terminology integrations such as MedCAT,
    scispaCy, UMLS, and SNOMED CT.

    Example:

        ClinicalTerm(
            term="Pathologist",
            category=ClinicalCategory.CLINICAL_OCCUPATION,
            specialty=Specialty.PATHOLOGY,
            sections=("consultant",),
        )
    """

    term: str
    category: ClinicalCategory
    specialty: Specialty = Specialty.COMMON

    sections: Tuple[str, ...] = field(default_factory=tuple)
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    match_mode: MatchMode = MatchMode.WORD
    case_sensitive: bool = False
    enabled: bool = True

    document_types: Tuple[str, ...] = field(default_factory=tuple)

    snomed_code: Optional[str] = None
    umls_cui: Optional[str] = None

    source: str = "mednexus_local"
    description: Optional[str] = None

    def __post_init__(self):
        normalized_term = self.term.strip()

        if not normalized_term:
            raise ValueError("Clinical term must not be empty.")

        object.__setattr__(
            self,
            "term",
            normalized_term,
        )

        object.__setattr__(
            self,
            "sections",
            self._normalize_values(self.sections),
        )

        object.__setattr__(
            self,
            "aliases",
            self._normalize_values(self.aliases),
        )

        object.__setattr__(
            self,
            "document_types",
            self._normalize_values(self.document_types),
        )

        object.__setattr__(
            self,
            "source",
            self.source.strip() or "mednexus_local",
        )

        if self.snomed_code is not None:
            object.__setattr__(
                self,
                "snomed_code",
                self.snomed_code.strip() or None,
            )

        if self.umls_cui is not None:
            object.__setattr__(
                self,
                "umls_cui",
                self.umls_cui.strip() or None,
            )

    @staticmethod
    def _normalize_values(values: Tuple[str, ...]) -> Tuple[str, ...]:
        """
        Normalize tuple values and remove duplicates while preserving order.
        """

        normalized_values = []
        seen_values = set()

        for value in values:
            normalized_value = value.strip()

            if not normalized_value:
                continue

            duplicate_key = normalized_value.lower()

            if duplicate_key in seen_values:
                continue

            seen_values.add(duplicate_key)
            normalized_values.append(normalized_value)

        return tuple(normalized_values)

    def all_terms(self) -> Tuple[str, ...]:
        """
        Return the primary term together with all configured aliases.
        """

        return (self.term, *self.aliases)

    def applies_to_section(
        self,
        section: Optional[str],
    ) -> bool:
        """
        Determine whether the term applies to the supplied clinical section.

        A term with no configured sections is considered globally applicable.
        """

        if not self.sections:
            return True

        if section is None:
            return False

        normalized_section = section.strip().lower()

        return any(
            configured_section.lower() == normalized_section
            for configured_section in self.sections
        )

    def applies_to_document_type(
        self,
        document_type: Optional[str],
    ) -> bool:
        """
        Determine whether the term applies to the supplied document type.

        A term with no configured document types is considered globally
        applicable.
        """

        if not self.document_types:
            return True

        if document_type is None:
            return False

        normalized_document_type = document_type.strip().lower()

        return any(
            configured_type.lower() == normalized_document_type
            for configured_type in self.document_types
        )


@dataclass(frozen=True)
class VocabularyProfile:
    """
    Groups clinical terms under a named vocabulary profile.

    Profiles will later support document-type and specialty-specific
    vocabulary loading.
    """

    name: str
    specialty: Specialty
    terms: Tuple[ClinicalTerm, ...] = field(default_factory=tuple)

    description: Optional[str] = None
    version: str = "1.0"

    def __post_init__(self):
        normalized_name = self.name.strip()

        if not normalized_name:
            raise ValueError("Vocabulary profile name must not be empty.")

        object.__setattr__(
            self,
            "name",
            normalized_name,
        )

        object.__setattr__(
            self,
            "version",
            self.version.strip() or "1.0",
        )

    def enabled_terms(self) -> Tuple[ClinicalTerm, ...]:
        """
        Return only enabled clinical terms from the profile.
        """

        return tuple(
            term
            for term in self.terms
            if term.enabled
        )