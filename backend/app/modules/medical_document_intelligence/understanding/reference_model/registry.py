from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .models import CanonicalConcept, DistributionPolicy, ReferenceSource, ResolvedConcept, ResolvedSpan, SourceTrustLevel
from .normalization import normalize_reference_term


class ReferenceModelRegistry:
    def __init__(self, sources: tuple[ReferenceSource, ...], concepts: tuple[CanonicalConcept, ...],
                 active_configuration: dict[str, str] | None = None):
        self._sources = {item.source_id: item for item in sources}
        self._concepts = {item.mednexus_concept_id: item for item in concepts}
        if len(self._sources) != len(sources) or len(self._concepts) != len(concepts):
            raise ValueError("Reference source and MedNexus concept IDs must be unique.")
        index = defaultdict(list)
        for concept in concepts:
            for term in concept.terms:
                index[normalize_reference_term(term)].append(concept)
            for source_id in concept.provenance:
                if source_id not in self._sources:
                    raise ValueError(f"Unknown provenance source: {source_id}")
            for mapping in concept.external_mappings:
                if mapping.source_id not in self._sources:
                    raise ValueError(f"Unknown mapping source: {mapping.source_id}")
        self._index = {key: tuple(value) for key, value in index.items()}
        self._max_term_words = min(10, max((len(key.split()) for key in self._index), default=1))
        self._active_configuration = dict(active_configuration) if active_configuration is not None else {
            item.source_id: item.version for item in sources if item.enabled
        }

    def resolve(self, term: str) -> tuple[ResolvedConcept, ...]:
        normalized = normalize_reference_term(term)
        return tuple(ResolvedConcept(term, concept, normalized) for concept in self._index.get(normalized, ()))

    def resolve_text(self, text: str) -> tuple[ResolvedSpan, ...]:
        """Indexed deterministic lexical candidate generation; no raw source dataset scan."""
        import re
        tokens = list(re.finditer(r"[\w\u0600-\u06ff]+", text, re.UNICODE))
        found = []
        for start_index, token in enumerate(tokens):
            for width in range(1, min(self._max_term_words, len(tokens) - start_index) + 1):
                end_token = tokens[start_index + width - 1]
                source = text[token.start():end_token.end()]
                normalized = normalize_reference_term(source)
                concepts = self._index.get(normalized)
                if concepts:
                    found.append(ResolvedSpan(source, token.start(), end_token.end(), concepts, normalized))
        # Prefer longest spans at a coordinate while preserving genuine concept ambiguity.
        best = {}
        for item in found:
            key = (item.start, item.end)
            best[key] = item
        return tuple(sorted(best.values(), key=lambda item: (item.start, -(item.end-item.start))))

    def concept(self, concept_id: str) -> CanonicalConcept:
        return self._concepts[concept_id]

    def source(self, source_id: str) -> ReferenceSource:
        return self._sources[source_id]

    @property
    def sources(self):
        return tuple(self._sources.values())

    @property
    def concepts(self):
        return tuple(self._concepts.values())

    @property
    def active_configuration(self) -> dict[str, str]:
        return dict(self._active_configuration)


def load_reference_sources(path: Path | None = None) -> tuple[ReferenceSource, ...]:
    manifest = path or Path(__file__).with_name("manifest.json")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return tuple(ReferenceSource(
        **{**item, "distribution_policy": DistributionPolicy(item["distribution_policy"]),
           "trust_level": SourceTrustLevel(item.get("trust_level", "AUTHORITATIVE_STANDARD"))}
    ) for item in payload["sources"])


def build_default_reference_registry(concepts=()) -> ReferenceModelRegistry:
    return ReferenceModelRegistry(load_reference_sources(), tuple(concepts))
