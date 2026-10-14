"""Project only pinned, durable reviewed records into MRJ's existing AnalysisRun authority."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from backend.app.modules.medical_document_intelligence.services.collection_analysis import (
    CONTRACT, _identity, analyze_collection,
)
from backend.app.modules.medical_document_intelligence.services.reviewed_collection_repository import (
    SqliteReviewedCollectionRepository,
)
from backend.app.modules.medical_document_intelligence.understanding.journey import journey_store


def reviewed_projection(record) -> dict[str, Any]:
    value = record.to_dict()
    version = value["record_version"]
    profile = value.get("profile_provenance") or {}
    context = value["exam_context"]
    standardized = {item.get("source_fact_id"): item for item in value["standardized_facts"]}
    facts = []
    for fact in value["canonical_facts"]:
        if (fact.get("temporal_status") == "SUPERSEDED"
                or fact.get("fact_type") in {"REPORT_ASSESSMENT", "RECOMMENDATION"}
                or fact.get("group") in {"ASSESSMENT", "RECOMMENDATION"}
                or not fact.get("evidence_anchors")):
            continue
        enrichment = standardized.get(fact["fact_id"]) or {}
        mapping = (enrichment.get("concept_mappings") or [{}])[0]
        measurements = [{"source_measurement_id": item.get("source_measurement_id") or
                         f"{fact['fact_id']}:measure:{index}",
                         "original_text": item.get("original_text"),
                         "normalized_value": item.get("normalized_value"),
                         "normalized_unit": item.get("normalized_unit"),
                         "mapping_status": item.get("mapping_status"),
                         "measurement_type": item.get("measurement_type"),
                         "dimension": item.get("dimension")}
                        for index, item in enumerate(enrichment.get("standardized_measurements", []))]
        facts.append({"fact_id": fact["fact_id"], "canonical_concept": fact.get("canonical_concept"),
                      "display_label": fact.get("display_label"), "fact_type": fact.get("fact_type"),
                      "assertion_state": fact.get("assertion_state"),
                      "hypothesis_status": fact.get("hypothesis_status"),
                      "anatomy": fact.get("anatomy") or [], "laterality": fact.get("laterality"),
                      "review_required": False, "profile_context": profile.get("profile_id"),
                      "mapping": {"terminology_system": mapping.get("system"), "code": mapping.get("code"),
                                  "mapping_status": mapping.get("mapping_status"),
                                  "lookup_scope": mapping.get("lookup_scope")},
                      "component_mapping_count": len(enrichment.get("component_mappings") or []),
                      "measurements": measurements})
    return {"report_id": f"reviewed:{value['reviewed_record_id']}:v{version}",
            "reviewed_record_id": value["reviewed_record_id"], "reviewed_record_version": version,
            "durably_reviewed": True, "domain": context.get("domain"),
            "stage_status": {}, "review_status": "REVIEWED", "synthesis_coverage_failure": False,
            "dimensions": {"modality": context.get("normalized_modality"),
                           "body_region": context.get("normalized_body_region"),
                           "laterality": context.get("normalized_laterality"),
                           "report_year": None, "standardization_status": "REVIEWED"},
            "facts": facts}


def _quality(records: list) -> dict[str, Any]:
    buckets = defaultdict(lambda: {"denominator": 0, "documented": 0,
                                   "not_documented": 0, "limited": 0, "not_applicable": 0})
    unavailable = 0
    for record in records:
        value = record.to_dict()
        profile = value.get("profile_provenance") or {}
        coverage = value.get("profile_coverage")
        if not profile or coverage is None:
            unavailable += 1
            continue
        for section in coverage:
            for element in [section, *section["elements"]]:
                element_id = element.get("element_id") or section["section_id"]
                key = (profile["profile_id"], profile["profile_version"], element_id)
                row = buckets[key]
                status = element["coverage"]
                if status == "NOT_APPLICABLE":
                    row["not_applicable"] += 1
                else:
                    row["denominator"] += 1
                    row[{"DOCUMENTED": "documented", "NOT_DOCUMENTED": "not_documented",
                         "LIMITED_OR_NOT_VISUALIZED": "limited"}[status]] += 1
    return {"profile_coverage": [dict(profile_id=key[0], profile_version=key[1], element_id=key[2], **row)
                                 for key, row in sorted(buckets.items())],
            "records_without_coverage_snapshot": unavailable,
            "review_alert_reports": sum(bool(record.to_dict().get("review_issues")) for record in records),
            "major_review_acknowledged_reports": sum(record.to_dict()["major_review_required"] for record in records)}


class ReviewedCollectionIntelligence:
    def __init__(self, repository: SqliteReviewedCollectionRepository | None = None) -> None:
        self.repository = repository or SqliteReviewedCollectionRepository(journey_store.reviewed_records)

    def analyze(self, collection_id: str, version: int | None = None) -> dict[str, Any]:
        head = self.repository.get_collection(collection_id)
        snapshot = self.repository.get_version(collection_id, version)
        if not snapshot["members"]:
            raise ValueError("Collection version has no reviewed records to analyze.")
        records = self.repository.get_members(collection_id, snapshot["collection_version"])
        reports = [reviewed_projection(record) for record in records]
        key = json.dumps([CONTRACT, collection_id, snapshot["collection_version"],
                          [(item["reviewed_record_id"], item["reviewed_record_version"])
                           for item in snapshot["members"]]], sort_keys=True)
        analysis_id = hashlib.sha256(key.encode()).hexdigest()[:32]
        try:
            return self.repository.get_analysis(analysis_id)
        except LookupError:
            pass
        legacy_collection = {"collection_id": collection_id, "name": head["name"],
                             "domain": "RADIOLOGY", "inclusion_policy": "DURABLE_REVIEWED_ONLY"}
        legacy_snapshot = {"version": snapshot["collection_version"], "created_at": snapshot["created_at"],
                           "reports": reports}
        result = analyze_collection(legacy_collection, legacy_snapshot, analysis_id=analysis_id)
        result.pop("cooccurrences", None)
        result.pop("cooccurrence_presentation", None)
        result["eligibility_policy"]["human_review_asserted"] = True
        result["analysis_provenance"]["exact_membership"] = [
            {"reviewed_record_id": item["reviewed_record_id"],
             "reviewed_record_version": item["reviewed_record_version"]}
            for item in snapshot["members"]]
        result["data_quality"] = _quality(records)
        self.repository.save_analysis(result)
        return result

    def contributors(self, analysis_id: str, kind: str, index: int) -> dict[str, Any]:
        analysis = self.repository.get_analysis(analysis_id)
        key = {"findings": "finding_frequencies", "measurements": "measurement_distributions"}.get(kind)
        if key is None or not 0 <= index < len(analysis[key]):
            raise LookupError("Metric was not found.")
        metric = analysis[key][index]
        records = self.repository.get_members(analysis["collection_id"], analysis["collection_version"])
        by_report = {f"reviewed:{item.to_dict()['reviewed_record_id']}:v{item.to_dict()['record_version']}": item
                     for item in records}
        rows = []
        for report_id in metric["report_ids"]:
            record = by_report[report_id]
            value = record.to_dict()
            projection = reviewed_projection(record)
            source_facts = {fact["fact_id"]: fact for fact in value["canonical_facts"]}
            for fact in projection["facts"]:
                if kind == "findings":
                    if (fact.get("assertion_state") != "PRESENT"
                            or _identity(fact, report_id)[0] != metric["concept_identity"]
                            or list(_identity(fact, report_id)[1]) != metric["anatomy"]
                            or _identity(fact, report_id)[2] != metric["laterality"]):
                        continue
                    measurements = []
                else:
                    measurements = [item for item in fact["measurements"]
                                    if item["source_measurement_id"] in metric["source_measurement_ids"]
                                    and item["measurement_type"] == metric["measurement_type"]
                                    and item["normalized_unit"] == metric["normalized_unit"]]
                    identity = _identity(fact, report_id)
                    if (not measurements or identity[0] != metric["concept_identity"]
                            or list(identity[1]) != metric.get("anatomy", [])
                            or identity[2] != metric.get("laterality")
                            or fact.get("profile_context") != metric.get("profile_context")):
                        continue
                source = source_facts[fact["fact_id"]]
                anchor = source["evidence_anchors"][0]
                evidence = record.evidence_context(fact["fact_id"], anchor.get("evidence_id"))
                if not evidence or not evidence["exact_highlight"]:
                    raise ValueError("Reviewed fact evidence is unavailable.")
                rows.append({"reviewed_record_id": value["reviewed_record_id"],
                             "reviewed_record_version": value["record_version"],
                             "exam_context": value["exam_context"], "fact_id": fact["fact_id"],
                             "fact_label": fact.get("display_label") or fact.get("canonical_concept"),
                             "assertion_state": fact.get("assertion_state"), "measurements": measurements,
                             "evidence": {"quote": anchor["quote"], "start_offset": anchor["start_offset"],
                                          "end_offset": anchor["end_offset"],
                                          "protected_artifact_sha256": evidence["artifact_sha256"]}})
        return {"metric": metric, "contributors": rows, "collection_id": analysis["collection_id"],
                "collection_version": analysis["collection_version"], "analysis_run_id": analysis_id}


reviewed_collection_intelligence = ReviewedCollectionIntelligence()
