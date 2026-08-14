from __future__ import annotations

import re
import unicodedata
from collections import defaultdict

from ..models import DocumentDomain
from .models import RecognitionConcept, RecognitionConceptCategory


class RecognitionKnowledgeRegistry:
    def __init__(self, concepts: tuple[RecognitionConcept, ...]):
        self._concepts = concepts
        self._by_id: dict[str, RecognitionConcept] = {}
        aliases: dict[str, list[RecognitionConcept]] = defaultdict(list)
        for concept in concepts:
            if concept.concept_id in self._by_id:
                raise ValueError(f"Duplicate recognition concept ID: {concept.concept_id}")
            self._by_id[concept.concept_id] = concept
            for alias in concept.aliases:
                aliases[self.normalize(alias)].append(concept)
        self._by_alias = {key: tuple(value) for key, value in aliases.items()}

    @staticmethod
    def normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).casefold()
        return re.sub(r"[^\w\u0600-\u06ff]+", " ", normalized).strip()

    def get(self, concept_id: str) -> RecognitionConcept:
        return self._by_id[concept_id]

    def resolve(
        self,
        alias: str,
        *,
        domain: DocumentDomain | None = None,
        category: RecognitionConceptCategory | None = None,
    ) -> tuple[RecognitionConcept, ...]:
        matches = self._by_alias.get(self.normalize(alias), ())
        return tuple(concept for concept in matches if (
            (domain is None or concept.domain is domain)
            and (category is None or concept.category is category)
        ))

    @property
    def concepts(self) -> tuple[RecognitionConcept, ...]:
        return self._concepts
