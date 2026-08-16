from __future__ import annotations

from dataclasses import asdict

from .registry import ReferenceModelRegistry


def configuration_snapshot(registry: ReferenceModelRegistry) -> dict:
    return {
        "active": registry.active_configuration,
        "sources": [asdict(item) | {"distribution_policy": item.distribution_policy.value}
                    for item in registry.sources],
    }


def compare_source_versions(before: ReferenceModelRegistry, after: ReferenceModelRegistry) -> dict[str, tuple[str | None, str | None]]:
    old = {item.source_id: item.version for item in before.sources}
    new = {item.source_id: item.version for item in after.sources}
    return {key: (old.get(key), new.get(key)) for key in old.keys() | new.keys() if old.get(key) != new.get(key)}
