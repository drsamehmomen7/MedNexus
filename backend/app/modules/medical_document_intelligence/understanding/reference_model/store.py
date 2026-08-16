from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import CanonicalConcept, ConceptFamily, ConceptRelationship, ExternalMapping, RelationshipType
from .normalization import normalize_reference_term


def reference_data_root() -> Path:
    configured = os.getenv("MEDNEXUS_REFERENCE_DATA_DIR")
    return Path(configured) if configured else Path(__file__).resolve().parents[7] / "Reference_Data"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_artifact(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    if not path.is_dir():
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(bytes.fromhex(sha256_file(item)))
    return digest.hexdigest()


def _concept_payload(concept: CanonicalConcept) -> dict:
    value = asdict(concept)
    value["concept_family"] = concept.concept_family.value
    for rel in value["relationships"]:
        rel["relationship_type"] = rel["relationship_type"].value if hasattr(rel["relationship_type"], "value") else rel["relationship_type"]
    return value


def _concept_from_payload(value: dict) -> CanonicalConcept:
    return CanonicalConcept(
        value["mednexus_concept_id"], value["canonical_name"], ConceptFamily(value["concept_family"]), value["domain"],
        tuple(value["preferred_terms"]), tuple(value.get("synonyms", ())), tuple(value.get("languages", ("en",))),
        tuple(ExternalMapping(**item) for item in value.get("external_mappings", ())),
        tuple(ConceptRelationship(RelationshipType(item["relationship_type"]), item["target_concept_id"], tuple(item["source_ids"]),
                                  item.get("source_relationship"), item.get("sequence_order"), item.get("target_external_id"))
              for item in value.get("relationships", ())),
        tuple(value.get("provenance", ())), value.get("status", "ACTIVE"),
        tuple(tuple(item) for item in value.get("attributes", ())),
    )


class ReferenceDataStore:
    def __init__(self, root: Path | None = None):
        self.root = root or reference_data_root()

    @property
    def normalized(self): return self.root / "normalized"

    @property
    def active_file(self): return self.root / "active.json"

    def save_import(self, source_id: str, version: str, artifact: Path, concepts: tuple[CanonicalConcept, ...]) -> dict:
        target = self.normalized / source_id / version
        target.mkdir(parents=True, exist_ok=True)
        checksum = sha256_artifact(artifact)
        mappings = sum(len(item.external_mappings) for item in concepts)
        receipt = {
            "source_id": source_id, "version": version, "artifact_name": artifact.name,
            "artifact_path": str(artifact.resolve()), "checksum_algorithm": "SHA256", "checksum": checksum,
            "imported_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "concept_count": len(concepts), "mapping_count": mappings,
        }
        (target / "concepts.json").write_text(json.dumps([_concept_payload(item) for item in concepts], ensure_ascii=False, indent=2), encoding="utf-8")
        (target / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return receipt

    def activate(self, source_id: str, version: str):
        if not (self.normalized / source_id / version / "receipt.json").is_file():
            raise FileNotFoundError(f"No verified import for {source_id} {version}.")
        active = self.active_configuration()
        active[source_id] = version
        self.root.mkdir(parents=True, exist_ok=True)
        self.active_file.write_text(json.dumps({"active": dict(sorted(active.items()))}, indent=2), encoding="utf-8")

    def active_configuration(self) -> dict[str, str]:
        if not self.active_file.is_file(): return {}
        return json.loads(self.active_file.read_text(encoding="utf-8")).get("active", {})

    def load(self, source_id: str, version: str) -> tuple[CanonicalConcept, ...]:
        payload = json.loads((self.normalized / source_id / version / "concepts.json").read_text(encoding="utf-8"))
        return tuple(_concept_from_payload(item) for item in payload)

    def verify(self, source_id: str, version: str) -> dict:
        receipt_path = self.normalized / source_id / version / "receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        artifact = Path(receipt["artifact_path"])
        present = artifact.is_file() or artifact.is_dir()
        current = sha256_artifact(artifact) if present else None
        return receipt | {"artifact_present": present, "checksum_valid": current == receipt["checksum"]}


def merge_concepts(concepts: tuple[CanonicalConcept, ...]) -> tuple[CanonicalConcept, ...]:
    """Conservatively merge exact normalized semantic duplicates while retaining every source mapping."""
    merged: dict[tuple[str, str, str], CanonicalConcept] = {}
    for concept in concepts:
        key = (concept.domain, concept.concept_family.value, normalize_reference_term(concept.canonical_name))
        existing = merged.get(key)
        if not existing:
            merged[key] = concept
            continue
        mappings = tuple({(m.source_id, m.external_id, m.display, m.mapping_type): m for m in (*existing.external_mappings, *concept.external_mappings)}.values())
        merged[key] = CanonicalConcept(
            existing.mednexus_concept_id, existing.canonical_name, existing.concept_family, existing.domain,
            tuple(dict.fromkeys((*existing.preferred_terms, *concept.preferred_terms))),
            tuple(dict.fromkeys((*existing.synonyms, *concept.synonyms))),
            tuple(dict.fromkeys((*existing.languages, *concept.languages))), mappings,
            tuple(dict.fromkeys((*existing.relationships, *concept.relationships))),
            tuple(dict.fromkeys((*existing.provenance, *concept.provenance))), existing.status,
            tuple(dict.fromkeys((*existing.attributes, *concept.attributes))),
        )
    return tuple(merged.values())
