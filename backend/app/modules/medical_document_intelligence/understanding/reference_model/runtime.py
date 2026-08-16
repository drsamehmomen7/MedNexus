from __future__ import annotations

from .radiology import RADIOLOGY_CANONICAL_CONCEPTS
from .registry import ReferenceModelRegistry, load_reference_sources
from .store import ReferenceDataStore, merge_concepts

_CACHE = {}


def build_active_reference_registry(store: ReferenceDataStore | None = None) -> ReferenceModelRegistry:
    store = store or ReferenceDataStore()
    stamp = store.active_file.stat().st_mtime_ns if store.active_file.is_file() else 0
    cache_key = (str(store.root.resolve()), stamp)
    if cache_key in _CACHE:
        return _CACHE[cache_key]
    sources = load_reference_sources()
    active = store.active_configuration()
    imported = []
    for source_id, version in sorted(active.items()):
        try:
            imported.extend(store.load(source_id, version))
        except (FileNotFoundError, ValueError):
            continue
    # Imported exact terms are indexed first; the curated set remains an offline compatibility fallback.
    concepts = merge_concepts(tuple(imported) + RADIOLOGY_CANONICAL_CONCEPTS)
    curated = {source.source_id: source.version for source in sources if source.enabled}
    registry = ReferenceModelRegistry(sources, concepts, curated | active)
    _CACHE.clear()
    _CACHE[cache_key] = registry
    return registry
