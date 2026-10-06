"""Deterministic, presentation-only views of a completed Radiology AnalysisRun."""
from __future__ import annotations

import hashlib
import json

from backend.app.modules.medical_document_intelligence.services.collection_analysis import (
    CONTRACT as ANALYSIS_CONTRACT,
    collection_store,
)


CONTRACT = "mrj-radiology-visualization-v0.2"
DEFAULT_TOP_N = 10
METRIC_FIELDS = ("display_label", "concept_identity", "anatomy", "laterality", "assertion",
                 "concept_a", "concept_b", "dimension", "category", "field", "numerator",
                 "denominator", "value", "available", "missing", "measurement_type",
                 "normalized_unit", "sample_count", "minimum", "maximum", "mean", "median")


def _rows(analysis, key, *, require_denominator=True):
    if require_denominator and not analysis["collection_summary"]["included_reports"]:
        return []
    return [{field: row[field] for field in METRIC_FIELDS if field in row}
            for row in analysis[key] if not require_denominator or row["denominator"] > 0]


def _panel(analysis, panel_id, title, subtitle, kind, source, data, empty_state, accessibility,
           *, warning=None, source_ids=None, default_limit=None, denominator_context=None,
           denominator_unit="included_reports"):
    return {"panel_id": panel_id, "title": title, "subtitle": subtitle,
            "visualization_type": kind, "source_metric_type": source,
            "source_analysis_result_ids": source_ids if source_ids is not None else [
                f"{source}[{index}]" for index in range(len(data))],
            "data": data, "denominator_context": (analysis["collection_summary"]["included_reports"]
                                                    if denominator_context is None else denominator_context),
            "denominator_unit": denominator_unit,
            "filters_applied": analysis["eligibility_policy"]["filters"],
            "empty_state": empty_state if not data else None,
            "warnings": [warning] if warning else [],
            "accessibility_description": accessibility,
            "default_display_limit": default_limit}


def build_visualization(analysis):
    """Copy governed values without deriving new clinical metrics or changing scope."""
    if analysis.get("contract") != ANALYSIS_CONTRACT:
        raise ValueError("INCOMPATIBLE_ANALYSIS_RUN")
    identifier = hashlib.sha256(json.dumps([CONTRACT, analysis["analysis_run_id"], DEFAULT_TOP_N],
                                         separators=(",", ":")).encode("utf-8")).hexdigest()[:32]
    summary = analysis["collection_summary"]
    included = summary["included_reports"]
    policy = analysis["eligibility_policy"]
    findings = _rows(analysis, "finding_frequencies")
    hypotheses = _rows(analysis, "diagnostic_hypothesis_frequencies")
    negatives = _rows(analysis, "pertinent_negative_frequencies")
    measurements = _rows(analysis, "measurement_distributions")
    strata = _rows(analysis, "stratifications")
    temporal_sources = sorted(
        ((index, row) for index, row in enumerate(analysis["stratifications"])
         if included and row["denominator"] > 0 and row["dimension"] == "report_year"
         and str(row["category"]).isdigit()),
        key=lambda item: int(item[1]["category"]),
    )
    temporal = [{field: row[field] for field in METRIC_FIELDS if field in row}
                for _, row in temporal_sources] if len(temporal_sources) >= 2 else []
    repeated = [{field: row[field] for field in METRIC_FIELDS if field in row}
                for row in analysis["cooccurrence_presentation"]["repeated_patterns"]
                if included and row["denominator"] > 0]
    coverage = _rows(analysis, "coverage_metrics")
    standard = {field: analysis["standardization_coverage"][field] for field in
                ("whole_fact_matched", "needs_review", "unmapped",
                 "component_mappings_available", "denominator_facts")}
    snapshot = {field: summary[field] for field in
                ("total_reports", "included_reports", "excluded_reports", "review_required_reports",
                 "included_review_required_reports", "facts_total")}
    panels = [
        _panel(analysis, "collection_snapshot", "Collection Snapshot", "Counts supplied by ANALYZE.",
               "SUMMARY_METRIC", "collection_summary", [snapshot], None,
               "Collection membership, included reports, exclusions, and canonical fact count.",
               source_ids=["collection_summary"]),
        _panel(analysis, "top_findings", "Top Findings", "PRESENT finding report frequency; included-report denominator shown on every row.",
               "HORIZONTAL_BAR", "finding_frequencies", findings,
               "NO_FINDING_FREQUENCIES: No PRESENT finding frequencies for this analysis policy.",
               "Ranked present finding frequencies. Bars begin at zero; full counts and labels accompany each bar.",
               default_limit=DEFAULT_TOP_N),
        _panel(analysis, "diagnostic_considerations", "Diagnostic Considerations",
               "Hypotheses retain their status; these are not confirmed findings.",
               "HORIZONTAL_BAR", "diagnostic_hypothesis_frequencies", hypotheses,
               "NO_DIAGNOSTIC_CONSIDERATIONS: No diagnostic considerations in this analysis.",
               "Diagnostic hypotheses are separate from present findings and include their assertion status.",
               default_limit=DEFAULT_TOP_N),
        _panel(analysis, "pertinent_negatives", "Pertinent Negatives", "Documented absence; not disease occurrence.",
               "HORIZONTAL_BAR", "pertinent_negative_frequencies", negatives,
               "NO_PERTINENT_NEGATIVES: No documented negatives in this analysis.",
               "Documented negative findings are separate from positive finding frequencies.",
               default_limit=DEFAULT_TOP_N),
        _panel(analysis, "measurements", "Measurements", "Only ANALYZE-approved comparable measurement distributions.",
               "TABLE", "measurement_distributions", measurements,
               "INSUFFICIENT_COMPARABLE_MEASUREMENTS: No safely comparable measurement distributions.",
               "Measurement summaries retain ANALYZE units, type, sample count, minimum, maximum, mean, and median."),
        _panel(analysis, "stratification", "Stratification", "Report-level categories, including MISSING.",
               "HORIZONTAL_BAR", "stratifications", strata,
               "NO_ELIGIBLE_REPORTS: No included reports to stratify.",
               "Structured report categories include missingness and use the included-report denominator."),
        _panel(analysis, "temporal", "Report Year", "Time view only when at least two governed year buckets exist.",
               "LINE" if temporal else "TABLE", "stratifications", temporal,
               "MISSING_TEMPORAL_DATA: No comparable report-year series is available.",
               "Report-year values are copied from ANALYZE; the line uses a zero baseline.",
               source_ids=[f"stratifications[{index}]" for index, _ in temporal_sources] if temporal else []),
        _panel(analysis, "cooccurrence", "Co-occurrence", "Repeated within-report PRESENT pairs only; minimum support 2 reports, top 20.",
               "HORIZONTAL_BAR", "cooccurrence_presentation.repeated_patterns", repeated,
               "No repeated co-occurrence patterns were observed in this collection.",
               "Repeated co-occurrence pairs are descriptive and retain their included-report denominator."),
        _panel(analysis, "coverage", "Data Coverage", "Available and missing structured-data counts.",
               "COVERAGE_BAR", "coverage_metrics", coverage,
               "NO_ELIGIBLE_REPORTS: No included-report coverage to display.",
               "Each field shows available and missing report counts against the included-report denominator."),
        _panel(analysis, "standardization", "Standardization Coverage",
               "Terminology coverage, not clinical validity; component mappings are separate.",
               "TABLE", "standardization_coverage", [standard], None,
               "Whole-fact matched, needs-review, and unmapped counts retain the canonical-fact denominator.",
               source_ids=["standardization_coverage"], denominator_context=standard["denominator_facts"],
               denominator_unit="canonical_facts"),
    ]
    return {"contract": CONTRACT, "visualization_run_id": identifier,
            "analysis_run_id": analysis["analysis_run_id"], "collection_id": analysis["collection_id"],
            "collection_version": analysis["collection_version"], "collection_name": analysis["collection_name"],
            "generated_at": analysis["generated_at"], "generated_at_basis": "ANALYSIS_RUN_GENERATED_AT",
            "configuration": {"default_top_n": DEFAULT_TOP_N}, "analysis_policy": policy,
            "collection_summary": snapshot, "panels": panels,
            "provenance": {"analysis_run_id": analysis["analysis_run_id"],
                           "analysis_contract": analysis["contract"],
                           "collection_id": analysis["collection_id"],
                           "collection_version": analysis["collection_version"],
                           "analysis_generated_at": analysis["generated_at"],
                           "analysis_policy": policy,
                           "source_analysis_provenance": analysis["analysis_provenance"]}}


class VisualizationStore:
    """Persist the immutable presentation of an already persisted AnalysisRun."""

    def create(self, analysis_run_id):
        analysis = collection_store.get_analysis(analysis_run_id)
        result = build_visualization(analysis)
        with collection_store._lock:
            path = collection_store._path("visualizations", result["visualization_run_id"])
            if path.is_file():
                return collection_store._read("visualizations", result["visualization_run_id"])
            collection_store._write("visualizations", result["visualization_run_id"], result)
        return result

    def get(self, visualization_run_id):
        with collection_store._lock:
            return collection_store._read("visualizations", visualization_run_id)


visualization_store = VisualizationStore()
