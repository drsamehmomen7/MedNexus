from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .models import CanonicalConcept, DistributionPolicy, ReferenceSource, ResolvedConcept, ResolvedSpan, SourceTrustLevel
from .normalization import normalize_reference_term


_COMPOSITION_EQUIVALENT_MAPPING_TYPES = {"equivalent"}


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
        mapping_index = defaultdict(set)
        equivalent_mappings_by_concept = defaultdict(set)
        procedures_by_component = defaultdict(set)
        for concept in concepts:
            for mapping in concept.external_mappings:
                if mapping.mapping_type.casefold() in _COMPOSITION_EQUIVALENT_MAPPING_TYPES:
                    key = (mapping.source_id, mapping.external_id)
                    mapping_index[key].add(concept.mednexus_concept_id)
                    equivalent_mappings_by_concept[concept.mednexus_concept_id].add(key)
            if concept.concept_family.value == "IMAGING_PROCEDURE":
                for relationship in concept.relationships:
                    if relationship.relationship_type.value == "CAN_COMPOSE":
                        procedures_by_component[relationship.target_concept_id].add(
                            concept.mednexus_concept_id
                        )
        self._mapping_index = {
            key: frozenset(value) for key, value in mapping_index.items()
        }
        self._equivalent_mappings_by_concept = {
            key: frozenset(value)
            for key, value in equivalent_mappings_by_concept.items()
        }
        self._procedures_by_component = {
            key: frozenset(value) for key, value in procedures_by_component.items()
        }
        self._composition_token_index = self._build_composition_token_index(concepts)
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
                concepts = self._index.get(normalized, ())
                if width == 1:
                    concepts = tuple(dict.fromkeys(
                        (*concepts, *self._composition_token_index.get(normalized, ()))
                    ))
                if concepts:
                    found.append(ResolvedSpan(source, token.start(), end_token.end(), concepts, normalized))
        # Prefer longest spans at a coordinate while preserving genuine concept ambiguity.
        best = {}
        for item in found:
            key = (item.start, item.end)
            best[key] = item
        return tuple(sorted(best.values(), key=lambda item: (item.start, -(item.end-item.start))))

    @staticmethod
    def _build_composition_token_index(
        concepts: tuple[CanonicalConcept, ...],
    ) -> dict[str, tuple[CanonicalConcept, ...]]:
        """Derive stable modality composition from authoritative procedure prefixes.

        This does not create lexical aliases. A token contributes only components
        shared by every governed imaging procedure that uses that token as its
        leading term, and only modality type/subtype components are exposed.
        """

        by_id = {item.mednexus_concept_id: item for item in concepts}
        component_sets: dict[str, list[set[str]]] = defaultdict(list)
        for concept in concepts:
            if concept.concept_family.value != "IMAGING_PROCEDURE":
                continue
            components = {
                relationship.target_concept_id
                for relationship in concept.relationships
                if relationship.relationship_type.value == "CAN_COMPOSE"
                and relationship.target_concept_id in by_id
            }
            if not components:
                continue
            for term in concept.terms:
                normalized = normalize_reference_term(term)
                if normalized:
                    component_sets[normalized.split()[0]].append(components)

        result = {}
        for token, sets in component_sets.items():
            shared = set.intersection(*sets)
            governed = tuple(
                item for item in concepts
                if item.mednexus_concept_id in shared
                and dict(item.attributes).get("part_type") in {
                    "RAD_MODALITY_MODALITY_TYPE",
                    "RAD_MODALITY_MODALITY_SUBTYPE",
                }
            )
            if governed:
                result[token] = governed
        return result

    def concept(self, concept_id: str) -> CanonicalConcept:
        return self._concepts[concept_id]

    def source(self, source_id: str) -> ReferenceSource:
        return self._sources[source_id]

    def equivalent_concept_ids(
        self,
        concept_id: str,
        external_mappings: tuple[tuple[str, str], ...] = (),
    ) -> frozenset[str]:
        """Return only concepts joined by explicitly equivalent source mappings.

        ``external_mappings`` may contain only mappings already qualified as
        equivalent by the evidence adapter. The registry also restricts them to
        keys whose registered mapping semantics are explicitly equivalent.
        """

        identifiers = {concept_id}
        mappings = {
            *self._equivalent_mappings_by_concept.get(concept_id, ()),
            *(item for item in external_mappings if item in self._mapping_index),
        }
        for mapping in mappings:
            identifiers.update(self._mapping_index.get(mapping, ()))
        return frozenset(identifiers)

    def composing_procedures(self, component_ids) -> tuple[CanonicalConcept, ...]:
        procedure_ids = {
            procedure_id
            for component_id in component_ids
            for procedure_id in self._procedures_by_component.get(component_id, ())
        }
        return tuple(
            self._concepts[item]
            for item in sorted(procedure_ids)
            if item in self._concepts
        )

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
