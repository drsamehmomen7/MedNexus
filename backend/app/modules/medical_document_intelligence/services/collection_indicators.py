"""Governed indicators sourced only from a persisted AnalysisRun."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy

from backend.app.modules.medical_document_intelligence.services.collection_analysis import (
    CONTRACT as ANALYSIS_CONTRACT,
    collection_store,
)


CONTRACT = "mrj-indicator-run-v0.1"
DEFINITION_CONTRACT = "mrj-indicator-definition-v0.1"
RESULT_CONTRACT = "mrj-indicator-result-v0.1"
DEFINITION_VERSION = 2
TOP_FINDINGS = 5
TOP_HYPOTHESES = 3
TOP_NEGATIVES = 3
COVERAGE_FIELDS = ("modality", "body_region", "report_service_date")
STANDARDIZATION_FIELDS = (
    ("whole_fact_matched", "Whole-fact MATCHED"),
    ("needs_review", "Whole-fact NEEDS_REVIEW"),
    ("unmapped", "Whole-fact UNMAPPED"),
)
READINESS_STATES = ("READY", "VALIDATION_ONLY", "NEEDS_REVIEW", "NOT_READY", "INVALID")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()[:32]


def _definition(kind, metric, *, name, numerator_definition, denominator_definition,
                interpretation_scope, domain, unit="REPORT_FRACTION", status="ACTIVE"):
    identity = {key: metric.get(key) for key in ("concept_identity", "anatomy", "laterality",
                                                 "assertion", "field", "measurement_type",
                                                 "dimension", "normalized_unit") if key in metric}
    definition = {
        "contract": DEFINITION_CONTRACT, "indicator_id": _digest([kind, identity]),
        "version": DEFINITION_VERSION, "name": name, "description": interpretation_scope,
        "domain": domain, "indicator_type": kind,
        "analysis_level": "FACT_LEVEL" if kind == "STANDARDIZATION_COVERAGE" else "REPORT_LEVEL",
        "source_metric_type": metric.get("metric_type", kind),
        "target_concept_identity": metric.get("concept_identity"),
        "target_anatomy": metric.get("anatomy", []),
        "target_laterality": metric.get("laterality"),
        "target_assertion": metric.get("assertion"),
        "target_hypothesis_status": metric.get("assertion") if kind == "DIAGNOSTIC_CONSIDERATION_FREQUENCY" else None,
        "target_field": metric.get("field"),
        "numerator_definition": numerator_definition,
        "denominator_definition": denominator_definition,
        "eligibility_rule": "INHERIT_ANALYSIS_RUN_POLICY",
        "exclusions": "INHERIT_ANALYSIS_RUN_EXCLUSIONS",
        "time_window_definition": "ANALYSIS_COLLECTION_SNAPSHOT",
        "stratification_definition": "INHERIT_ANALYSIS_RUN_FILTERS",
        "unit": unit, "interpretation_scope": interpretation_scope, "status": status,
    }
    definition["revision"] = _digest({key: value for key, value in definition.items()
                                       if key not in {"indicator_id", "version", "revision"}})
    return definition


def validate_definition_update(prior, updated):
    """A changed governed meaning cannot silently reuse an existing version."""
    if prior["indicator_id"] != updated["indicator_id"]:
        raise ValueError("INDICATOR_IDENTITY_CHANGED")
    if prior["revision"] != updated["revision"] and updated["version"] <= prior["version"]:
        raise ValueError("INDICATOR_DEFINITION_VERSION_CONFLICT")


def _source_candidates(analysis):
    rows = []
    def make_definition(kind, metric, **kwargs):
        return _definition(kind, metric, domain=analysis["domain"], **kwargs)

    for source, kind, limit, label, numerator, scope in (
        ("finding_frequencies", "REPORT_FINDING_FREQUENCY", TOP_FINDINGS,
         "Report-level frequency of {}", "Included reports containing a PRESENT {} fact",
         "Measures the share of included radiology reports containing a PRESENT {} fact. This is report-level frequency, not population prevalence."),
        ("diagnostic_hypothesis_frequencies", "DIAGNOSTIC_CONSIDERATION_FREQUENCY", TOP_HYPOTHESES,
         "Report-level diagnostic consideration: {} ({})",
         "Included reports with a {} diagnostic consideration for {}",
         "Measures documented diagnostic considerations in included reports; it does not establish a diagnosis."),
        ("pertinent_negative_frequencies", "DOCUMENTED_NEGATIVE_FREQUENCY", TOP_NEGATIVES,
         "Documented absence: {}", "Included reports documenting absence of {}",
         "Measures documented absence in included reports, not a disease-free population rate."),
    ):
        for index, metric in enumerate(analysis[source][:limit]):
            display = metric["display_label"]
            if kind == "DIAGNOSTIC_CONSIDERATION_FREQUENCY":
                name = label.format(display, metric["assertion"])
                numerator_text = numerator.format(metric["assertion"], display)
            else:
                scope_label = display[3:] if kind == "DOCUMENTED_NEGATIVE_FREQUENCY" and display.casefold().startswith("no ") else display
                name = label.format(scope_label)
                numerator_text = numerator.format(scope_label)
            definition = make_definition(kind, metric, name=name, numerator_definition=numerator_text,
                                     denominator_definition="All reports included by the source AnalysisRun policy",
                                     interpretation_scope=scope.format(display) if "{}" in scope else scope)
            rows.append((definition, metric, f"{source}[{index}]"))
    by_field = {row["field"]: (index, row) for index, row in enumerate(analysis["coverage_metrics"])}
    for field in COVERAGE_FIELDS:
        if field not in by_field:
            continue
        index, metric = by_field[field]
        definition = make_definition("DATA_COVERAGE", metric, name=f"{field.replace('_', ' ').title()} data coverage",
                                 numerator_definition=f"Included reports with structured {field} available",
                                 denominator_definition="All reports included by the source AnalysisRun policy",
                                 interpretation_scope="Measures structured-data availability, not a clinical outcome.")
        rows.append((definition, metric, f"coverage_metrics[{index}]"))
    coverage = analysis["standardization_coverage"]
    for key, label in STANDARDIZATION_FIELDS:
        metric = {"metric_type": "standardization_coverage", "field": key,
                  "numerator": coverage[key], "denominator": coverage["denominator_facts"],
                  "value": None}
        definition = make_definition("STANDARDIZATION_COVERAGE", metric, name=label + " terminology coverage",
                                 numerator_definition=f"Analyzed canonical facts with {label} whole-fact status",
                                 denominator_definition="Analyzed canonical facts in the source AnalysisRun",
                                 interpretation_scope="Measures terminology coverage, not clinical validity. Component mappings are separate.",
                                 unit="CANONICAL_FACT_RATIO")
        rows.append((definition, metric, f"standardization_coverage.{key}"))
    if analysis["measurement_distributions"]:
        for index, metric in enumerate(analysis["measurement_distributions"][:3]):
            definition = make_definition("MEASUREMENT_SUMMARY", metric,
                                     name=f"Comparable {metric['measurement_type']} summary: {metric['concept_identity']}",
                                     numerator_definition="Included reports with a governed comparable measurement in this distribution",
                                     denominator_definition="All reports included by the source AnalysisRun policy",
                                     interpretation_scope="Describes an ANALYZE-approved comparable measurement distribution; no unit conversion occurs here.")
            rows.append((definition, metric, f"measurement_distributions[{index}]"))
    else:
        metric = {"metric_type": "measurement_distribution", "field": "comparable_measurement",
                  "numerator": None, "denominator": analysis["collection_summary"]["included_reports"],
                  "value": None}
        definition = make_definition("MEASUREMENT_SUMMARY", metric, name="Comparable measurement summary",
                                 numerator_definition="Included reports with a governed comparable measurement distribution",
                                 denominator_definition="All reports included by the source AnalysisRun policy",
                                 interpretation_scope="No measurement summary is issued without an ANALYZE-approved comparable distribution.")
        rows.append((definition, metric, None))
    return rows


def evaluate_indicator(definition, metric, analysis, source_path):
    """Wrap the source metric; never recount reports or divide source counts."""
    summary = analysis["collection_summary"]
    policy = analysis["eligibility_policy"]
    numerator = metric.get("numerator")
    denominator = metric.get("denominator")
    value = metric.get("value")
    warnings = []
    if (definition.get("contract") != DEFINITION_CONTRACT or definition.get("version", 0) < 1
            or not definition.get("numerator_definition") or not definition.get("denominator_definition")
            or definition.get("analysis_level") != (
                "FACT_LEVEL" if definition.get("indicator_type") == "STANDARDIZATION_COVERAGE"
                else "REPORT_LEVEL")
            or definition.get("source_metric_type") != metric.get("metric_type")
            or definition.get("target_assertion") != metric.get("assertion")
            or definition.get("target_concept_identity") != metric.get("concept_identity")
            or definition.get("revision") != _digest({key: item for key, item in definition.items()
                                                      if key not in {"indicator_id", "version", "revision"}})):
        state, reason = "INVALID", "INVALID_INDICATOR_DEFINITION"
    elif definition["status"] != "ACTIVE":
        state, reason = "NEEDS_REVIEW", "DEFINITION_REQUIRES_REVIEW"
    elif definition["time_window_definition"] != "ANALYSIS_COLLECTION_SNAPSHOT":
        state, reason = "NOT_READY", "MISSING_REQUIRED_DIMENSION"
    elif not isinstance(denominator, int) or denominator <= 0:
        state, reason = "NOT_READY", "NO_ELIGIBLE_DENOMINATOR"
    elif source_path is None:
        state, reason = "NOT_READY", "INSUFFICIENT_DATA"
    elif (not isinstance(numerator, int) or numerator < 0 or numerator > denominator
          or metric.get("analysis_run_id", analysis["analysis_run_id"]) != analysis["analysis_run_id"]
          or metric.get("collection_id", analysis["collection_id"]) != analysis["collection_id"]
          or metric.get("collection_version", analysis["collection_version"]) != analysis["collection_version"]):
        state, reason = "INVALID", "INVALID_SOURCE_METRIC"
    elif summary["included_review_required_reports"]:
        state, reason = "VALIDATION_ONLY", "VALIDATION_ONLY_INPUT"
    else:
        state, reason = "READY", None
    if definition["indicator_type"] == "STANDARDIZATION_COVERAGE" and state in {"READY", "VALIDATION_ONLY"}:
        warnings.append("RATIO_NOT_PUBLISHED_BY_ANALYZE")
    if reason:
        warnings.append(reason)
    if state in {"NOT_READY", "INVALID"}:
        value = None
    coverage_field = ("measurements" if definition["indicator_type"] == "MEASUREMENT_SUMMARY"
                      else "standardized_concept_mapping" if definition["indicator_type"] == "STANDARDIZATION_COVERAGE"
                      else metric.get("field") if definition["indicator_type"] == "DATA_COVERAGE"
                      else "clinical_facts")
    coverage_row = next((row for row in analysis["coverage_metrics"] if row["field"] == coverage_field), None)
    coverage = ({key: coverage_row[key] for key in ("field", "available", "missing", "denominator", "value")}
                if coverage_row else {})
    if definition["indicator_type"] == "MEASUREMENT_SUMMARY" and source_path:
        coverage.update({key: metric[key] for key in ("sample_count", "minimum", "maximum", "mean", "median",
                                                     "normalized_unit", "measurement_type", "dimension") if key in metric})
    result = {"contract": RESULT_CONTRACT,
              "indicator_result_id": _digest([RESULT_CONTRACT, analysis["analysis_run_id"],
                                               definition["indicator_id"], definition["version"]]),
              "indicator_id": definition["indicator_id"], "indicator_version": definition["version"],
              "definition_revision": definition["revision"],
              "analysis_run_id": analysis["analysis_run_id"], "collection_id": analysis["collection_id"],
              "collection_version": analysis["collection_version"], "generated_at": analysis["generated_at"],
              "source_metric_path": source_path, "source_metric_type": definition["source_metric_type"],
              "time_window_definition": definition["time_window_definition"],
              "numerator": numerator, "denominator": denominator, "value": value,
              "unit": definition["unit"], "included_reports": summary["included_reports"],
              "excluded_reports": summary["excluded_reports"],
              "review_required_reports": summary["review_required_reports"],
              "included_review_required_reports": summary["included_review_required_reports"],
              "coverage": coverage, "readiness_state": state, "warnings": warnings,
              "provenance": {"indicator_id": definition["indicator_id"],
                             "indicator_version": definition["version"],
                             "definition_revision": definition["revision"],
                             "analysis_run_id": analysis["analysis_run_id"],
                             "analysis_contract": analysis["contract"],
                             "collection_id": analysis["collection_id"],
                             "collection_version": analysis["collection_version"],
                             "analysis_policy": deepcopy(policy),
                             "eligibility_rule": metric.get("eligibility_rule", analysis["analysis_provenance"]["eligibility_rule"]),
                             "excluded_report_ids": deepcopy(analysis["eligibility_summary"]["excluded_report_ids"]),
                             "filtered_out_report_ids": deepcopy(analysis["eligibility_summary"]["filtered_out_report_ids"]),
                             "included_report_ids": deepcopy(analysis["eligibility_summary"]["included_report_ids"]),
                             "contributing_report_ids": deepcopy(metric.get("report_ids", [])),
                             "source_metric_path": source_path,
                             "target_concept_identity": definition["target_concept_identity"],
                             "time_window_definition": definition["time_window_definition"]}}
    return result


def build_indicator_run(analysis):
    """Build a small, stable candidate catalog from authoritative analytical rows."""
    if analysis.get("contract") != ANALYSIS_CONTRACT:
        raise ValueError("INCOMPATIBLE_ANALYSIS_RUN")
    if analysis.get("analysis_level") != "REPORT_LEVEL":
        raise ValueError("UNSUPPORTED_ANALYSIS_LEVEL")
    candidates = _source_candidates(analysis)
    definitions = []
    results = []
    for definition, metric, source_path in candidates:
        definitions.append(definition)
        results.append(evaluate_indicator(definition, metric, analysis, source_path))
    counts = Counter(result["readiness_state"] for result in results)
    summary = {state: counts[state] for state in READINESS_STATES}
    diagnostics = []
    if not analysis["finding_frequencies"] and not analysis["diagnostic_hypothesis_frequencies"] and not analysis["pertinent_negative_frequencies"]:
        diagnostics.append("NO_INDICATOR_CANDIDATES")
    if not analysis["collection_summary"]["included_reports"]:
        diagnostics.append("NO_VALID_DENOMINATOR")
    if analysis["collection_summary"]["included_review_required_reports"]:
        diagnostics.append("VALIDATION_ONLY_INPUT")
    if not analysis["measurement_distributions"]:
        diagnostics.append("INSUFFICIENT_DATA")
    if next((row for row in analysis["coverage_metrics"] if row["field"] == "report_service_date"), {}).get("available") == 0:
        diagnostics.append("MISSING_REQUIRED_DIMENSION")
    return {"contract": CONTRACT, "indicator_run_id": _digest([CONTRACT, analysis["analysis_run_id"],
                                                                  DEFINITION_VERSION, TOP_FINDINGS,
                                                                  TOP_HYPOTHESES, TOP_NEGATIVES, COVERAGE_FIELDS]),
            "analysis_run_id": analysis["analysis_run_id"], "collection_id": analysis["collection_id"],
            "collection_version": analysis["collection_version"], "collection_name": analysis["collection_name"],
            "generated_at": analysis["generated_at"], "generated_at_basis": "ANALYSIS_RUN_GENERATED_AT",
            "analysis_policy": deepcopy(analysis["eligibility_policy"]),
            "eligibility_summary": deepcopy(analysis["eligibility_summary"]),
            "collection_summary": deepcopy(analysis["collection_summary"]),
            "definitions": definitions, "results": results, "readiness_summary": summary,
            "diagnostics": diagnostics,
            "provenance": {"analysis_run_id": analysis["analysis_run_id"],
                           "analysis_contract": analysis["contract"],
                           "collection_id": analysis["collection_id"],
                           "collection_version": analysis["collection_version"],
                           "analysis_policy": deepcopy(analysis["eligibility_policy"]),
                           "source_analysis_provenance": deepcopy(analysis["analysis_provenance"])}}


class IndicatorStore:
    """Persist source-linked results and immutable versioned definitions outside Git."""

    def create(self, analysis_run_id):
        analysis = collection_store.get_analysis(analysis_run_id)
        run = build_indicator_run(analysis)
        with collection_store._lock:
            path = collection_store._path("indicator_runs", run["indicator_run_id"])
            if path.is_file():
                return collection_store._read("indicator_runs", run["indicator_run_id"])
            for definition in run["definitions"]:
                key = _digest(["definition", definition["indicator_id"], definition["version"]])
                prior_path = collection_store._path("indicator_definitions", key)
                if prior_path.is_file():
                    prior = collection_store._read("indicator_definitions", key)
                    validate_definition_update(prior, definition)
                else:
                    collection_store._write("indicator_definitions", key, definition)
            collection_store._write("indicator_runs", run["indicator_run_id"], run)
        return run

    def get(self, indicator_run_id):
        with collection_store._lock:
            return collection_store._read("indicator_runs", indicator_run_id)


indicator_store = IndicatorStore()
