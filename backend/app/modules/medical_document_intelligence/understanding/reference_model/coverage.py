from __future__ import annotations

from collections import Counter

from .runtime import build_active_reference_registry


def reference_coverage(registry=None) -> dict:
    registry = registry or build_active_reference_registry()
    concepts = registry.concepts
    by_source = Counter(source for concept in concepts for source in concept.provenance)
    families = Counter(concept.concept_family.value for concept in concepts)
    record_types = Counter(dict(concept.attributes).get("record_type", "UNCLASSIFIED") for concept in concepts)
    mapping_sources = Counter(mapping.source_id for concept in concepts for mapping in concept.external_mappings)
    relationships = Counter(rel.relationship_type.value for concept in concepts for rel in concept.relationships)
    cids = {dict(concept.attributes).get("cid") for concept in concepts if dict(concept.attributes).get("cid")}
    legacy = {"REFERENCE_BACKED": 0, "MEDNEXUS_PROPRIETARY": 0, "COMPATIBILITY_ONLY": 0, "REDUNDANT": 0, "UNVERIFIED": 0}
    for concept in concepts:
        if "MNX_RAD_REF_V1" not in concept.provenance: continue
        external = {item.source_id for item in concept.external_mappings}
        if external: legacy["REFERENCE_BACKED"] += 1
        elif len(concept.provenance) > 1: legacy["REDUNDANT"] += 1
        else: legacy["COMPATIBILITY_ONLY"] += 1
    return {
        "canonical_concepts": len(concepts),
        "preferred_terms": sum(len(item.preferred_terms) for item in concepts),
        "synonyms": sum(len(item.synonyms) for item in concepts),
        "external_mappings": sum(len(item.external_mappings) for item in concepts),
        "relationships": sum(len(item.relationships) for item in concepts),
        "concepts_by_source": dict(sorted(by_source.items())),
        "concept_families": dict(sorted(families.items())),
        "record_types": dict(sorted(record_types.items())),
        "mapping_sources": dict(sorted(mapping_sources.items())),
        "relationship_types": dict(sorted(relationships.items())),
        "dcmr_context_groups": len(cids),
        "legacy_curated_audit": legacy,
    }
