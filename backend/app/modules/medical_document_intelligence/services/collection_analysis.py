"""R4.0A report-level Radiology collection analysis over governed facts only.

The durable store contains bounded structured projections, never source text,
protected text, evidence quotes, engine candidates, or patient identifiers.
"""
from __future__ import annotations

import json
import hashlib
import os
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from itertools import combinations
from pathlib import Path
from statistics import mean, median
from threading import RLock
from uuid import uuid4


CONTRACT = "mrj-radiology-analysis-v0.4"
LEVEL = "REPORT_LEVEL"
COOCCURRENCE_MIN_SUPPORT = 2
COOCCURRENCE_TOP_N = 20
STAGES_OK = {"COMPLETE", "NEEDS_REVIEW"}
FILTERS = {"modality", "body_region", "laterality", "report_year", "sex", "age_band", "batch_id", "standardization_status"}
DIMENSIONS = ("modality", "body_region", "laterality", "report_year", "sex", "age_band", "facility", "region", "batch_id", "standardization_status")
_SAFE_TEXT = re.compile(r"^[\w .,:/()\-]{1,120}$", re.UNICODE)


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _state(value):
    return value.value if hasattr(value, "value") else value


def _known(field):
    return field.get("value") if isinstance(field, dict) and field.get("state") == "KNOWN" else None


def _age_band(patient):
    accepted = _known(patient.get("age_band"))
    if isinstance(accepted, str) and accepted:
        return accepted
    age = _known(patient.get("age"))
    if not isinstance(age, int) or isinstance(age, bool) or not 0 <= age <= 120:
        return None
    return "0-17" if age < 18 else "18-39" if age < 40 else "40-64" if age < 65 else "65+"


def _report_year(patient):
    safe_time = _known(patient.get("safe_time_context"))
    year = safe_time.get("report_year") if isinstance(safe_time, dict) else None
    if year is None and isinstance(safe_time, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", safe_time):
        year = int(safe_time[:4])
    return year if isinstance(year, int) and not isinstance(year, bool) and 1900 <= year <= 2100 else None


def governed_report_snapshot(run, item):
    """Copy only allowed structured fields from one atomic Journey document."""
    from backend.app.modules.medical_document_intelligence.understanding.journey import JourneyStage

    status = {stage.value: _state(item.stage_status.get(stage, "NOT_STARTED"))
              for stage in (JourneyStage.PROTECT, JourneyStage.EXTRACT, JourneyStage.STANDARDIZE)}
    extract = item.stage_results.get(JourneyStage.EXTRACT) or {}
    standardized = item.stage_results.get(JourneyStage.STANDARDIZE) or {}
    synthesis = extract.get("clinical_synthesis") or {}
    source_facts = synthesis.get("canonical_facts") or []
    projections = {fact.get("source_fact_id"): fact for fact in standardized.get("standardized_facts", [])}
    clinical = item.context.clinical_context if item.context else None
    domain = clinical.domain_extension if clinical else None
    modality_context = domain.modality_context if domain else None
    study = standardized.get("standardized_study_context") or {}
    protected = item.stage_results.get(JourneyStage.PROTECT) or {}
    patient = (protected.get("patient_analytic_context") or {}).get("fields") or {}
    facts = []
    for fact in source_facts:
        projected = projections.get(fact.get("fact_id")) or {}
        concept = (projected.get("concept_mappings") or [{}])[0]
        mapping = {key: concept.get(key) for key in
                   ("terminology_system", "code", "mapping_status", "lookup_scope", "match_type")}
        measurements = [{key: measure.get(key) for key in
                         ("source_measurement_id", "original_text", "normalized_value", "normalized_unit",
                          "mapping_status", "measurement_type", "dimension")}
                        for measure in projected.get("standardized_measurements", [])]
        facts.append({"fact_id": fact.get("fact_id"), "canonical_concept": fact.get("canonical_concept"),
                      "display_label": fact.get("display_label"), "fact_type": fact.get("fact_type"),
                      "assertion_state": fact.get("assertion_state"),
                      "hypothesis_status": fact.get("hypothesis_status"),
                      "anatomy": list(fact.get("anatomy") or []),
                      "laterality": fact.get("laterality"),
                      "review_required": bool(fact.get("review_required")),
                      "mapping": mapping,
                      "component_mapping_count": len(projected.get("component_mappings") or []),
                      "measurements": measurements})
    source_digest = item.content_digest
    if not source_digest and item.source_artifact:
        source_digest = hashlib.sha256(item.source_artifact).hexdigest()
    if not source_digest and item.document is not None:
        source_digest = hashlib.sha256(item.document.text.encode("utf-8")).hexdigest()
    report_id = f"source:{source_digest}" if source_digest else f"journey:{run.run_id}:{item.document_id}"
    return {"report_id": report_id, "origin_run_id": run.run_id,
            "origin_document_id": item.document_id,
            "batch_id": run.run_id if _state(run.mode) == "BATCH" else None,
            "domain": item.context.identity.healthcare_domain if item.context else None,
            "stage_status": status, "review_status": item.review_status,
            "synthesis_coverage_failure": synthesis.get("technical_diagnostics", {}).get("code") == "SYNTHESIS_COVERAGE_FAILURE",
            "dimensions": {"modality": study.get("normalized_modality") or getattr(clinical, "modality", None),
                           "body_region": study.get("normalized_body_region") or getattr(clinical, "body_region", None),
                           "laterality": study.get("normalized_laterality") or _state(getattr(modality_context, "laterality", None)),
                           "report_year": _report_year(patient), "sex": _known(patient.get("sex")),
                           "age_band": _age_band(patient),
                           "facility": _known(patient.get("facility_context")),
                           "region": _known(patient.get("generalized_geography")),
                           "batch_id": run.run_id if _state(run.mode) == "BATCH" else None,
                           "standardization_status": status["STANDARDIZE"]},
            "facts": facts}


def eligibility(report):
    status = report["stage_status"]
    reasons = []
    if status.get("EXTRACT") not in STAGES_OK:
        reasons.append("EXTRACT_FAILED" if status.get("EXTRACT") == "FAILED" else "EXTRACT_BLOCKED")
    if report.get("synthesis_coverage_failure"):
        reasons.append("SYNTHESIS_COVERAGE_FAILURE")
    if not report.get("facts"):
        reasons.append("NO_CANONICAL_FACTS")
    if status.get("STANDARDIZE") not in STAGES_OK:
        reasons.append("STANDARDIZE_FAILED" if status.get("STANDARDIZE") == "FAILED" else "STANDARDIZE_BLOCKED")
    if report.get("domain") != "RADIOLOGY":
        reasons.append("INVALID_ANALYTIC_CONTEXT")
    if reasons:
        return {"status": "EXCLUDED", "reasons": sorted(set(reasons))}
    if (status.get("EXTRACT") == "NEEDS_REVIEW" or status.get("STANDARDIZE") == "NEEDS_REVIEW"
            or status.get("PROTECT") == "NEEDS_REVIEW" or report.get("review_status") in {"PENDING", "NEEDS_REVIEW"}
            or any(fact.get("review_required") for fact in report["facts"])):
        return {"status": "NEEDS_REVIEW", "reasons": ["REPORT_REVIEW_REQUIRED"]}
    return {"status": "ELIGIBLE", "reasons": []}


class ReportCollectionStore:
    """File-backed immutable collection versions and analysis run snapshots."""

    def __init__(self, root=None):
        default = "D:/MedNexus/Analysis_Workspace" if os.name == "nt" else "/tmp/mrj-analysis"
        self.root = Path(root or os.getenv("MRJ_ANALYSIS_STORE_DIR", default))
        self._lock = RLock()

    def _path(self, kind, identifier):
        if not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise LookupError("Unknown collection or analysis run.")
        return self.root / kind / f"{identifier}.json"

    def _read(self, kind, identifier):
        path = self._path(kind, identifier)
        if not path.is_file():
            raise LookupError("Unknown collection or analysis run.")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, kind, identifier, payload):
        path = self._path(kind, identifier)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".{identifier}.{uuid4().hex}.tmp")
        try:
            temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)

    def create(self, name, reports, description="", domain="RADIOLOGY", provenance=None):
        if not isinstance(name, str) or not _SAFE_TEXT.fullmatch(name.strip()):
            raise ValueError("Collection name must be a short safe label.")
        if not isinstance(description, str) or len(description) > 500:
            raise ValueError("Collection description is too long.")
        if domain != "RADIOLOGY":
            raise ValueError("R4.0A supports Radiology collections only.")
        reports = self._validate_members(reports)
        identifier = uuid4().hex
        now = _now()
        collection = {"collection_id": identifier, "name": name.strip(), "description": description,
                      "domain": domain, "created_at": now, "updated_at": now, "version": 1,
                      "inclusion_policy": "EXPLICIT_REPORT_MEMBERSHIP",
                      "provenance": provenance or {"source": "JOURNEY_STRUCTURED_RECORDS"},
                      "versions": [{"version": 1, "created_at": now, "reports": reports}]}
        with self._lock:
            self._write("collections", identifier, collection)
        return self.metadata(collection)

    @staticmethod
    def _validate_members(reports):
        if not isinstance(reports, list) or not reports:
            raise ValueError("At least one governed report is required.")
        ids = [report.get("report_id") for report in reports]
        if any(not isinstance(value, str) or not value for value in ids) or len(ids) != len(set(ids)):
            raise ValueError("Duplicate or missing report membership.")
        return sorted(deepcopy(reports), key=lambda item: item["report_id"])

    @staticmethod
    def metadata(collection):
        current = collection["versions"][-1]
        statuses = Counter(eligibility(item)["status"] for item in current["reports"])
        return {key: collection[key] for key in
                ("collection_id", "name", "description", "domain", "created_at", "updated_at", "version", "inclusion_policy", "provenance")} | {
                    "report_count": len(current["reports"]), "eligible": statuses["ELIGIBLE"],
                    "review_required": statuses["NEEDS_REVIEW"], "excluded": statuses["EXCLUDED"],
                    "report_ids": [item["report_id"] for item in current["reports"]]}

    def list(self):
        with self._lock:
            if not (self.root / "collections").exists():
                return []
            return sorted((self.metadata(json.loads(path.read_text(encoding="utf-8")))
                           for path in (self.root / "collections").glob("*.json")),
                          key=lambda item: (item["created_at"], item["collection_id"]), reverse=True)

    def get(self, identifier, version=None):
        with self._lock:
            collection = self._read("collections", identifier)
        selected = collection["version"] if version is None else version
        snapshot = next((item for item in collection["versions"] if item["version"] == selected), None)
        if snapshot is None:
            raise ValueError("INVALID_COLLECTION_VERSION")
        return deepcopy(collection), deepcopy(snapshot)

    def add_reports(self, identifier, reports):
        additions = self._validate_members(reports)
        with self._lock:
            collection = self._read("collections", identifier)
            current = collection["versions"][-1]["reports"]
            merged = self._validate_members([*current, *additions])
            collection["version"] += 1
            collection["updated_at"] = _now()
            collection["versions"].append({"version": collection["version"],
                                           "created_at": collection["updated_at"], "reports": merged})
            self._write("collections", identifier, collection)
        return self.metadata(collection)

    def analyze(self, identifier, *, version=None, include_review_required=False, filters=None):
        collection, snapshot = self.get(identifier, version)
        filters = _validate_filters(filters)
        key = json.dumps([CONTRACT, identifier, snapshot["version"], bool(include_review_required), filters], sort_keys=True)
        analysis_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        with self._lock:
            if self._path("analyses", analysis_id).is_file():
                return self._read("analyses", analysis_id)
            result = analyze_collection(collection, snapshot, include_review_required=include_review_required,
                                        filters=filters, analysis_id=analysis_id)
            self._write("analyses", result["analysis_run_id"], result)
        return result

    def get_analysis(self, identifier):
        with self._lock:
            return self._read("analyses", identifier)


def _identity(fact, report_id):
    mapping = fact.get("mapping") or {}
    if (mapping.get("mapping_status") == "MATCHED" and mapping.get("code")
            and mapping.get("lookup_scope") in {"WHOLE_LABEL", "CANONICAL_CONCEPT"}):
        base = f"{mapping.get('terminology_system')}:{mapping['code']}"
    else:
        base = f"MRJ:{fact['canonical_concept']}" if fact.get("canonical_concept") else f"REPORT_FACT:{report_id}:{fact['fact_id']}"
    anatomy = tuple(sorted(str(value).casefold() for value in fact.get("anatomy") or []))
    laterality = str(fact.get("laterality") or "MISSING").upper()
    return (base, anatomy, laterality)


def _metric(kind, numerator, denominator, report_ids, context, **extra):
    return {"metric_type": kind, "analysis_level": LEVEL, "numerator": numerator,
            "denominator": denominator, "value": round(numerator / denominator, 6) if denominator else None,
            "eligibility_rule": context["eligibility_rule"], "exclusions": context["excluded_report_ids"],
            "collection_id": context["collection_id"], "collection_version": context["collection_version"],
            "analysis_run_id": context["analysis_run_id"], "report_ids": sorted(report_ids), **extra}


def _validate_filters(filters):
    if filters is None:
        return {}
    if not isinstance(filters, dict) or set(filters) - FILTERS:
        raise ValueError("Unsupported structured analysis filter.")
    if any(not isinstance(value, (str, int)) or len(str(value)) > 80 for value in filters.values()):
        raise ValueError("Invalid analysis filter value.")
    return dict(sorted(filters.items()))


def analyze_collection(collection, snapshot, *, include_review_required=False, filters=None, analysis_id=None):
    filters = _validate_filters(filters)
    reports = snapshot["reports"]
    eligibility_rows = [{"report_id": report["report_id"], **eligibility(report)} for report in reports]
    by_id = {report["report_id"]: report for report in reports}
    filtered_out = {report["report_id"] for report in reports if any(
        str(report.get("dimensions", {}).get(key) or "MISSING") != str(value) for key, value in filters.items())}
    included = [row["report_id"] for row in eligibility_rows if row["report_id"] not in filtered_out and
                (row["status"] == "ELIGIBLE" or include_review_required and row["status"] == "NEEDS_REVIEW")]
    excluded = [row["report_id"] for row in eligibility_rows if row["status"] == "EXCLUDED"]
    review = [row["report_id"] for row in eligibility_rows if row["status"] == "NEEDS_REVIEW"]
    analysis_id = analysis_id or uuid4().hex
    context = {"collection_id": collection["collection_id"], "collection_version": snapshot["version"],
               "analysis_run_id": analysis_id, "eligibility_rule": "ELIGIBLE_PLUS_EXPLICIT_VALIDATION_REVIEW" if include_review_required else "ELIGIBLE_ONLY",
               "excluded_report_ids": sorted(set(excluded) | filtered_out)}
    denominator = len(included)
    grouped = defaultdict(set)
    labels = {}
    present_by_report = {}
    measurements = defaultdict(list)
    unclassified_measurements = 0
    all_facts = []
    for report_id in included:
        report = by_id[report_id]
        present = set()
        for fact in report["facts"]:
            all_facts.append(fact)
            identity = _identity(fact, report_id)
            labels.setdefault(identity, fact.get("display_label") or fact.get("canonical_concept") or "Unspecified canonical fact")
            assertion = fact.get("assertion_state")
            hypothesis = fact.get("hypothesis_status")
            if fact.get("fact_type") == "DIAGNOSTIC_HYPOTHESIS" or hypothesis:
                bucket = ("diagnostic_consideration", identity, hypothesis or "UNSPECIFIED")
            elif assertion == "PRESENT":
                bucket = ("finding_report_frequency", identity, "PRESENT")
                present.add(identity)
            elif assertion == "ABSENT_NEGATED":
                bucket = ("documented_absence_frequency", identity, "ABSENT")
            else:
                bucket = ("uncertain_fact_frequency", identity, "UNCERTAIN")
            grouped[bucket].add(report_id)
            for measure in fact.get("measurements") or []:
                if assertion != "PRESENT" or fact.get("fact_type") == "DIAGNOSTIC_HYPOTHESIS" or hypothesis:
                    unclassified_measurements += 1
                    continue
                if measure.get("mapping_status") != "MATCHED" or measure.get("normalized_value") is None:
                    unclassified_measurements += 1
                    continue
                kind = measure.get("measurement_type")
                dimension = measure.get("dimension")
                if not kind or not dimension or not measure.get("normalized_unit"):
                    unclassified_measurements += 1
                    continue
                try:
                    numeric = Decimal(str(measure["normalized_value"]))
                except (ValueError, ArithmeticError):
                    unclassified_measurements += 1
                    continue
                if not numeric.is_finite():
                    unclassified_measurements += 1
                    continue
                measurements[(identity, fact.get("fact_type") or "FINDING", kind, dimension, measure["normalized_unit"])].append(
                    (numeric, report_id, measure.get("source_measurement_id"), measure.get("original_text")))
        present_by_report[report_id] = present

    def frequency_rows(kind):
        rows = []
        for (bucket, identity, assertion), ids in grouped.items():
            if bucket != kind:
                continue
            rows.append(_metric(bucket, len(ids), denominator, ids, context,
                                concept_identity=identity[0], display_label=labels[identity],
                                anatomy=list(identity[1]), laterality=identity[2],
                                assertion=assertion))
        return sorted(rows, key=lambda row: (-row["numerator"], row["concept_identity"], row["assertion"]))

    pairs = defaultdict(set)
    for report_id, identities in present_by_report.items():
        for pair in combinations(sorted(identities), 2):
            pairs[pair].add(report_id)
    cooccurrences = sorted((_metric("report_level_cooccurrence", len(ids), denominator, ids, context,
                                     concept_a=pair[0][0], concept_b=pair[1][0])
                            for pair, ids in pairs.items()),
                           key=lambda row: (-row["numerator"], row["concept_a"], row["concept_b"]))
    repeated_pairs = sorted((row for row in cooccurrences if row["numerator"] >= COOCCURRENCE_MIN_SUPPORT),
                            key=lambda row: (-row["numerator"], -row["value"],
                                             row["concept_a"], row["concept_b"]))
    cooccurrence_presentation = {"minimum_support": COOCCURRENCE_MIN_SUPPORT, "top_n": COOCCURRENCE_TOP_N,
                                 "repeated_patterns": repeated_pairs[:COOCCURRENCE_TOP_N],
                                 "total_valid_pairs": len(cooccurrences),
                                 "one_off_pairs": sum(row["numerator"] == 1 for row in cooccurrences)}

    distributions = []
    for (identity, fact_type, kind, dimension, unit), samples in sorted(measurements.items()):
        values = [value for value, *_ in samples]
        ids = {report_id for _, report_id, *_ in samples}
        distributions.append(_metric("measurement_distribution", len(ids), denominator, ids, context,
                                     concept_identity=identity[0], fact_type=fact_type,
                                     measurement_type=kind, dimension=dimension,
                                     normalized_unit=unit, sample_count=len(samples),
                                     minimum=str(min(values)), maximum=str(max(values)),
                                     mean=str(Decimal(str(mean(values)))), median=str(Decimal(str(median(values)))),
                                     source_measurement_ids=sorted(source for _, _, source, _ in samples if source),
                                     original_measurements=[{"report_id": report_id, "source_measurement_id": source,
                                                             "original_text": original}
                                                            for _, report_id, source, original in samples]))

    strata = []
    coverage = []
    for dimension in DIMENSIONS:
        buckets = defaultdict(set)
        for report_id in included:
            raw = by_id[report_id].get("dimensions", {}).get(dimension)
            buckets[str(raw) if raw not in (None, "") else "MISSING"].add(report_id)
        for value, ids in sorted(buckets.items()):
            strata.append(_metric("report_stratification", len(ids), denominator, ids, context,
                                  dimension=dimension, category=value))
        available = set(included) - buckets.get("MISSING", set())
        coverage.append(_metric("field_coverage", len(available), denominator, available, context,
                                field=dimension, available=len(available), missing=denominator - len(available)))
    assertion_buckets = defaultdict(set)
    for report_id in included:
        states = {fact.get("assertion_state") for fact in by_id[report_id]["facts"]
                  if fact.get("fact_type") != "DIAGNOSTIC_HYPOTHESIS" and not fact.get("hypothesis_status")}
        for state in states or {"MISSING"}:
            assertion_buckets["ABSENT" if state == "ABSENT_NEGATED" else state or "MISSING"].add(report_id)
    for value, ids in sorted(assertion_buckets.items()):
        strata.append(_metric("report_stratification", len(ids), denominator, ids, context,
                              dimension="assertion", category=value))
    year_coverage = next(row for row in coverage if row["field"] == "report_year")
    coverage.append({**year_coverage, "field": "report_service_date"})
    for field, predicate in (
        ("clinical_facts", lambda report: bool(report["facts"])),
        ("measurements", lambda report: any(fact.get("measurements") for fact in report["facts"])),
        ("standardized_concept_mapping", lambda report: any(
            fact.get("mapping", {}).get("mapping_status") == "MATCHED" for fact in report["facts"])),
    ):
        ids = {report_id for report_id in included if predicate(by_id[report_id])}
        coverage.append(_metric("field_coverage", len(ids), denominator, ids, context,
                                field=field, available=len(ids), missing=denominator - len(ids)))
    mapping_counts = Counter((fact.get("mapping") or {}).get("mapping_status") or "UNMAPPED" for fact in all_facts)
    diagnostics = []
    if not included:
        diagnostics.append("ALL_REPORTS_REQUIRE_REVIEW" if review and not include_review_required and not excluded else "NO_ELIGIBLE_REPORTS")
    if not distributions:
        diagnostics.append("INSUFFICIENT_COMPARABLE_MEASUREMENTS")
    if any(row["missing"] for row in coverage):
        diagnostics.append("MISSING_ANALYTIC_DIMENSION")
    summary = {"total_reports": len(reports), "eligible_reports": sum(row["status"] == "ELIGIBLE" for row in eligibility_rows),
               "review_required_reports": len(review), "excluded_reports": len(excluded),
               "included_reports": denominator, "included_review_required_reports": len(set(included) & set(review)),
               "facts_total": len(all_facts),
               "present_facts": sum(fact.get("assertion_state") == "PRESENT" and fact.get("fact_type") != "DIAGNOSTIC_HYPOTHESIS" and not fact.get("hypothesis_status") for fact in all_facts),
               "negative_facts": sum(fact.get("assertion_state") == "ABSENT_NEGATED" and fact.get("fact_type") != "DIAGNOSTIC_HYPOTHESIS" and not fact.get("hypothesis_status") for fact in all_facts),
               "uncertain_facts": sum(fact.get("assertion_state") == "UNCERTAIN" and fact.get("fact_type") != "DIAGNOSTIC_HYPOTHESIS" and not fact.get("hypothesis_status") for fact in all_facts),
               "standardized_matched": mapping_counts["MATCHED"], "standardized_review": mapping_counts["NEEDS_REVIEW"],
               "standardized_unmapped": mapping_counts["UNMAPPED"]}
    return {"contract": CONTRACT, "analysis_run_id": analysis_id, "collection_id": collection["collection_id"],
            "collection_version": snapshot["version"], "collection_name": collection["name"],
            "generated_at": _now(), "domain": collection["domain"], "analysis_level": LEVEL,
            "patient_level_analysis": "NOT_AVAILABLE",
            "eligibility_policy": {"include_review_required_for_validation": bool(include_review_required),
                                   "human_review_asserted": False, "filters": filters},
            "eligibility_summary": {"reports": eligibility_rows, "included_report_ids": sorted(included),
                                    "excluded_report_ids": sorted(excluded), "review_required_report_ids": sorted(review),
                                    "filtered_out_report_ids": sorted(filtered_out)},
            "collection_summary": summary, "finding_frequencies": frequency_rows("finding_report_frequency"),
            "diagnostic_hypothesis_frequencies": frequency_rows("diagnostic_consideration"),
            "pertinent_negative_frequencies": frequency_rows("documented_absence_frequency"),
            "uncertain_fact_frequencies": frequency_rows("uncertain_fact_frequency"),
            "measurement_distributions": distributions, "measurement_coverage": {"unclassified_measurements": unclassified_measurements},
            "stratifications": strata, "cooccurrences": cooccurrences,
            "cooccurrence_presentation": cooccurrence_presentation, "coverage_metrics": coverage,
            "standardization_coverage": {"whole_fact_matched": mapping_counts["MATCHED"],
                                         "needs_review": mapping_counts["NEEDS_REVIEW"],
                                         "unmapped": mapping_counts["UNMAPPED"],
                                         "component_mappings_available": sum(fact.get("component_mapping_count", 0) for fact in all_facts),
                                         "denominator_facts": len(all_facts)},
            "diagnostics": diagnostics,
            "analysis_provenance": {**context, "contract": CONTRACT, "collection_snapshot_created_at": snapshot["created_at"],
                                    "inclusion_policy": collection["inclusion_policy"], "filters": filters,
                                    "included_report_ids": sorted(included), "review_required_report_ids": sorted(review)}}


collection_store = ReportCollectionStore()
