from __future__ import annotations

import argparse
import json
from pathlib import Path

from .importers import importer_for
from .registry import load_reference_sources
from .store import ReferenceDataStore
from .coverage import reference_coverage


def _source(token: str):
    token = token.casefold()
    aliases = {"loinc": "LOINC_RSNA_2_82", "dicom": "DICOM_2026_CURRENT", "dicom-dcmr": "DICOM_DCMR_2026C", "radlex": "RADLEX_CURRENT", "snomed": "SNOMED_INT_20260701"}
    source_id = aliases.get(token, token.upper())
    return next((item for item in load_reference_sources() if item.source_id == source_id), None) or (_ for _ in ()).throw(ValueError(f"Unknown source: {token}"))


def status(store):
    active = store.active_configuration()
    rows = []
    for source in load_reference_sources():
        version = active.get(source.source_id)
        receipt = None
        if version:
            receipt = json.loads((store.normalized / source.source_id / version / "receipt.json").read_text(encoding="utf-8"))
        curated = source.source_id == "MNX_RAD_REF_V1"
        rows.append({"source": source.source_name, "source_id": source.source_id, "expected_version": source.version,
                     "status": "ACTIVE" if version or curated else ("LICENSED ARTIFACT REQUIRED" if source.distribution_policy.value == "LICENSE_RESTRICTED" else "MISSING ARTIFACT"),
                     "active_version": version or (source.version if curated else None), "concepts": receipt["concept_count"] if receipt else ("CURATED_FALLBACK" if curated else 0),
                     "mappings": receipt["mapping_count"] if receipt else 0})
    print(json.dumps({"reference_data_root": str(store.root), "sources": rows}, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mednexus-reference-model")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("coverage")
    imp = commands.add_parser("import"); imp.add_argument("source"); imp.add_argument("--path", required=True); imp.add_argument("--subset-file")
    verify = commands.add_parser("verify"); verify.add_argument("source", nargs="?")
    activate = commands.add_parser("activate"); activate.add_argument("source"); activate.add_argument("version", nargs="?")
    args = parser.parse_args(argv); store = ReferenceDataStore()
    if args.command == "status": status(store); return 0
    if args.command == "coverage": print(json.dumps(reference_coverage(), indent=2)); return 0
    if args.command == "import":
        source = _source(args.source); artifact = Path(args.path)
        subset = Path(args.subset_file).read_text(encoding="utf-8").splitlines() if args.subset_file else None
        concepts = importer_for(source).import_artifact(source, artifact, subset_ids=subset)
        print(json.dumps(store.save_import(source.source_id, source.version, artifact, concepts), indent=2)); return 0
    if args.command == "activate":
        source = _source(args.source); store.activate(source.source_id, args.version or source.version); status(store); return 0
    active = store.active_configuration()
    selected = [_source(args.source)] if args.source else [item for item in load_reference_sources() if item.source_id in active]
    print(json.dumps([store.verify(item.source_id, active.get(item.source_id, item.version)) for item in selected], indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
