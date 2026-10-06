"""R5.0A presentation-only visualization contracts; all inputs are synthetic."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend.app.modules.medical_document_intelligence.services import collection_visualization as visualize
from backend.app.modules.medical_document_intelligence.services.collection_analysis import ReportCollectionStore
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyDocument, JourneyStage, JourneyStore, StageStatus,
)
from backend.tests.test_collection_analysis import analyze, fact, report


def panel(result, name):
    return next(item for item in result["panels"] if item["panel_id"] == name)


def test_visualization_copies_analysis_values_and_has_deterministic_provenance():
    analysis = analyze([report("a", [fact("edema", components=2), fact("mass"),
                                     fact("no_aspiration", assertion="ABSENT_NEGATED"),
                                     fact("tumor", assertion="UNCERTAIN", hypothesis="FAVORED",
                                          kind="DIAGNOSTIC_HYPOTHESIS")]),
                        report("b", [fact("edema"), fact("mass")])])
    original = deepcopy(analysis)
    result = visualize.build_visualization(analysis)
    assert result == visualize.build_visualization(analysis)
    assert analysis == original
    assert result["analysis_run_id"] == analysis["analysis_run_id"]
    assert result["collection_id"] == analysis["collection_id"]
    assert result["collection_version"] == analysis["collection_version"]
    assert result["generated_at"] == analysis["generated_at"]
    assert result["provenance"]["analysis_contract"] == analysis["contract"]
    finding = panel(result, "top_findings")["data"][0]
    source = analysis["finding_frequencies"][0]
    assert (finding["numerator"], finding["denominator"], finding["value"]) == (
        source["numerator"], source["denominator"], source["value"])
    assert finding["concept_identity"] == source["concept_identity"]
    assert finding["concept_identity"].startswith("MRJ:")
    assert result["collection_summary"]["included_reports"] == 2
    assert panel(result, "top_findings")["denominator_context"] == 2
    assert panel(result, "top_findings")["denominator_unit"] == "included_reports"
    assert panel(result, "top_findings")["default_display_limit"] == 10
    assert panel(result, "diagnostic_considerations")["data"][0]["assertion"] == "FAVORED"
    assert panel(result, "pertinent_negatives")["data"][0]["display_label"] == "no_aspiration"
    assert panel(result, "cooccurrence")["data"][0]["numerator"] == 2
    assert panel(result, "cooccurrence")["data"] == [
        {key: row[key] for key in visualize.METRIC_FIELDS if key in row}
        for row in analysis["cooccurrence_presentation"]["repeated_patterns"]]
    assert panel(result, "standardization")["data"][0]["component_mappings_available"] == 2
    assert panel(result, "standardization")["data"][0]["whole_fact_matched"] == 0
    assert panel(result, "standardization")["denominator_context"] == analysis["standardization_coverage"]["denominator_facts"]
    assert panel(result, "standardization")["denominator_unit"] == "canonical_facts"
    assert all("source_measurement_id" not in str(item["data"]) for item in result["panels"])
    assert all(word not in str(result).lower() for word in
               ("population prevalence", "incidence", "association", "correlation", "causation"))
    altered = deepcopy(analysis)
    altered["finding_frequencies"][0]["value"] = 0.371234
    assert panel(visualize.build_visualization(altered), "top_findings")["data"][0]["value"] == 0.371234


def test_zero_denominator_and_one_off_pairs_have_safe_empty_states():
    analysis = analyze([report("review", [fact("edema"), fact("mass")], standardize="NEEDS_REVIEW")])
    conservative = visualize.build_visualization(analysis)
    for name in ("top_findings", "diagnostic_considerations", "pertinent_negatives", "measurements",
                 "stratification", "temporal", "cooccurrence", "coverage"):
        assert panel(conservative, name)["data"] == []
        assert panel(conservative, name)["empty_state"]
    assert panel(conservative, "top_findings")["empty_state"].startswith("NO_FINDING_FREQUENCIES")
    assert panel(conservative, "temporal")["empty_state"].startswith("MISSING_TEMPORAL_DATA")
    assert panel(conservative, "measurements")["empty_state"].startswith("INSUFFICIENT_COMPARABLE_MEASUREMENTS")
    included = analyze([report("review", [fact("edema"), fact("mass")], standardize="NEEDS_REVIEW")], include=True)
    one_off = visualize.build_visualization(included)
    assert included["cooccurrences"] and panel(one_off, "cooccurrence")["data"] == []
    assert "No repeated co-occurrence patterns" in panel(one_off, "cooccurrence")["empty_state"]
    assert one_off["analysis_policy"]["include_review_required_for_validation"] is True
    assert one_off["analysis_policy"]["human_review_asserted"] is False
    assert one_off["collection_summary"]["included_review_required_reports"] == 1


def test_measurement_distribution_and_missing_coverage_are_copied_without_recalculation():
    measure = {"source_measurement_id": "m1", "original_text": "1.4 cm", "normalized_value": "14",
               "normalized_unit": "mm", "mapping_status": "MATCHED", "measurement_type": "diameter",
               "dimension": "length"}
    analysis = analyze([report("a", [fact("lesion", measures=[measure])]),
                        report("b", [fact("lesion", measures=[{**measure, "source_measurement_id": "m2"}])])])
    result = visualize.build_visualization(analysis)
    measured = panel(result, "measurements")
    assert measured["visualization_type"] == "TABLE"
    assert measured["data"][0]["normalized_unit"] == "mm"
    assert measured["data"][0]["sample_count"] == 2
    assert measured["data"][0]["mean"] == analysis["measurement_distributions"][0]["mean"]
    assert "original_text" not in str(measured) and "source_measurement_id" not in str(measured)
    coverage = panel(result, "coverage")
    year = next(row for row in coverage["data"] if row["field"] == "report_service_date")
    source = next(row for row in analysis["coverage_metrics"] if row["field"] == "report_service_date")
    assert (year["available"], year["missing"], year["denominator"], year["value"]) == (
        source["available"], source["missing"], source["denominator"], source["value"])
    assert year["missing"] == 2


def test_temporal_view_requires_two_governed_year_buckets_and_preserves_order():
    first = report("a")
    second = report("b")
    first["dimensions"]["report_year"] = 2025
    second["dimensions"]["report_year"] = 2023
    analysis = analyze([first, second])
    year_sources = [(index, row["category"]) for index, row in enumerate(analysis["stratifications"])
                    if row["dimension"] == "report_year" and str(row["category"]).isdigit()]
    analysis["stratifications"].reverse()
    result = visualize.build_visualization(analysis)
    temporal = panel(result, "temporal")
    assert temporal["visualization_type"] == "LINE"
    assert [row["category"] for row in temporal["data"]] == ["2023", "2025"]
    assert all(row["denominator"] == 2 for row in temporal["data"])
    assert temporal["source_analysis_result_ids"] == [
        f"stratifications[{len(analysis['stratifications']) - 1 - index}]"
        for index, _ in sorted(year_sources, key=lambda item: int(item[1]))]


def test_visualization_store_http_roundtrip_and_exact_journey_attachment(tmp_path, monkeypatch):
    from backend.app.main import app
    from backend.app.modules.medical_document_intelligence.api import understanding as api

    store = ReportCollectionStore(tmp_path)
    collection = store.create("Synthetic visualization", [report("a", [fact("edema")])])
    analysis = store.analyze(collection["collection_id"])
    monkeypatch.setattr(visualize, "collection_store", store)
    monkeypatch.setattr(api, "visualization_store", visualize.VisualizationStore())
    journey = JourneyStore()
    run = journey.create_run("SINGLE")
    item = JourneyDocument("document", "synthetic.txt", 0, "txt")
    item.stage_status[JourneyStage.ANALYZE] = StageStatus.COMPLETE
    item.stage_results[JourneyStage.ANALYZE] = {"analysis_run_id": analysis["analysis_run_id"]}
    run.documents.append(item)
    monkeypatch.setattr(api, "journey_store", journey)
    client = TestClient(app)
    response = client.post(f"/api/v1/understanding/analysis-runs/{analysis['analysis_run_id']}/visualize",
                           json={"journey_run_id": run.run_id})
    assert response.status_code == 200
    result = response.json()
    assert client.get(f"/api/v1/understanding/visualization-runs/{result['visualization_run_id']}").json() == result
    assert client.post(f"/api/v1/understanding/analysis-runs/{analysis['analysis_run_id']}/visualize",
                       json={}).json() == result
    assert item.stage_results[JourneyStage.VISUALIZE]["analysis_run_id"] == analysis["analysis_run_id"]
    assert item.stage_status[JourneyStage.VISUALIZE] is StageStatus.COMPLETE
    assert run.current_stage is JourneyStage.VISUALIZE
    unrelated = journey.create_run("SINGLE")
    other_item = JourneyDocument("other", "other.txt", 0, "txt")
    other_item.stage_status[JourneyStage.ANALYZE] = StageStatus.COMPLETE
    other_item.stage_results[JourneyStage.ANALYZE] = {"analysis_run_id": "different-analysis"}
    unrelated.documents.append(other_item)
    journey.attach_collection_visualization(unrelated.run_id, result)
    assert other_item.stage_status[JourneyStage.VISUALIZE] is StageStatus.NOT_STARTED
    assert client.post("/api/v1/understanding/analysis-runs/" + "f" * 32 + "/visualize", json={}).status_code == 404


def test_incompatible_analysis_contract_is_rejected():
    old = analyze([report("a")])
    old["contract"] = "mrj-radiology-analysis-v0.3"
    with pytest.raises(ValueError, match="INCOMPATIBLE_ANALYSIS_RUN"):
        visualize.build_visualization(old)
