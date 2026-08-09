from typing import Dict, Iterable, List, Optional

from .models import (
    ClinicalTerm,
    Specialty,
    VocabularyProfile,
)


class VocabularyRegistry:
    """
    Central registry for all clinical vocabulary profiles.

    The registry is intentionally lightweight and independent from
    any terminology provider. Future integrations (MedCAT,
    scispaCy, SNOMED CT, UMLS) will register their vocabularies
    through the same interface.
    """

    def __init__(self):
        self._profiles: Dict[Specialty, VocabularyProfile] = {}

    def register(
        self,
        profile: VocabularyProfile,
    ) -> None:
        """
        Register or replace a vocabulary profile.
        """
        self._profiles[profile.specialty] = profile

    def unregister(
        self,
        specialty: Specialty,
    ) -> None:
        """
        Remove a registered profile.
        """
        self._profiles.pop(specialty, None)

    def clear(self) -> None:
        """
        Remove all registered profiles.
        """
        self._profiles.clear()

    def has_profile(
        self,
        specialty: Specialty,
    ) -> bool:
        return specialty in self._profiles

    def get_profile(
        self,
        specialty: Specialty,
    ) -> Optional[VocabularyProfile]:
        return self._profiles.get(specialty)

    def list_profiles(self) -> List[VocabularyProfile]:
        return list(self._profiles.values())

    def list_specialties(self) -> List[Specialty]:
        return list(self._profiles.keys())

    def get_terms(
        self,
        specialty: Specialty,
    ) -> List[ClinicalTerm]:
        profile = self.get_profile(specialty)

        if profile is None:
            return []

        return list(profile.enabled_terms())

    def all_terms(self) -> List[ClinicalTerm]:
        """
        Return all enabled terms from every registered profile.
        """
        terms: List[ClinicalTerm] = []

        for profile in self._profiles.values():
            terms.extend(profile.enabled_terms())

        return terms

    def __len__(self):
        return len(self._profiles)

    def __contains__(
        self,
        specialty: Specialty,
    ):
        return specialty in self._profiles


registry = VocabularyRegistry()