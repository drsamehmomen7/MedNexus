"""R6.0A indicator authority and governance tests; all inputs are synthetic."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend.app.modules.medical_document_intelligence.services import collection_indicators as indicators
from backend.app.modules.medical_document_intelligence.services.collection_analysis import ReportCollectionStore
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyDocument, JourneyStage, JourneyStore, StageStatus,
)
from backend.tests.test_collection_analysis import analyze, fact, report


def pair(run, kind, *, field=None, assertion=None):
    for definition, result in zip(run["definitions"], run["results"]):
        if (definition["indicator_type"] == kind and (field is None or definition["target_field"] == field)
                and (assertion is None or definition["target_assertion"] == assertion)):
            return definition, result
    raise AssertionError(f"Missing indicator: {kind}/{field}/{assertion}")


def test_analysis_is_only_numerical_authority_and_output_is_deterministic():
    rows = [report("a", [fact("edema", mapping="UNMAPPED"), fact("tumor", assertion="UNCERTAIN",
                              hypothesis="FAVORED", kind="DIAGNOSTIC_HYPOTHESIS"),
                         fact("aspiration", assertion="ABSENT_NEGATED")]),
            report("b", [fact("edema", mapping="UNMAPPED")])]
    analysis = analyze(rows)
    original = deepcopy(analysis)
    run = indicators.build_indicator_run(analysis)
    assert run == indicators.build_indicator_run(analysis)
    assert analysis == original
    assert run["analysis_run_id"] == analysis["analysis_run_id"]
    assert (run["collection_id"], run["collection_version"]) == (
        analysis["collection_id"], analysis["collection_version"])
    definition, result = pair(run, "REPORT_FINDING_FREQUENCY")
    metric = analysis["finding_frequencies"][0]
    assert (result["numerator"], result["denominator"], result["value"]) == (
        metric["numerator"], metric["denominator"], metric["value"])
    assert result["readiness_state"] == "READY"
    assert result["provenance"]["contributing_report_ids"] == metric["report_ids"]
    assert result["provenance"]["analysis_policy"] == analysis["eligibility_policy"]
    assert result["provenance"]["excluded_report_ids"] == analysis["eligibility_summary"]["excluded_report_ids"]
    assert definition["analysis_level"] == "REPORT_LEVEL"
    assert definition["time_window_definition"] == "ANALYSIS_COLLECTION_SNAPSHOT"
    assert "not population prevalence" in definition["interpretation_scope"]
    altered = deepcopy(analysis)
    altered["finding_frequencies"][0]["value"] = 0.371234
    assert pair(indicators.build_indicator_run(altered), "REPORT_FINDING_FREQUENCY")[1]["value"] == 0.371234
    assert "raw_engine_candidate_count" not in str(run)
    assert "original_text" not in str(run)


def test_hypotheses_negatives_unmapped_and_component_identity_stay_separate():
    rows = [report("a", [fact("edema", mapping="UNMAPPED", components=2),
                         fact("tumor", assertion="UNCERTAIN", hypothesis="FAVORED", kind="DIAGNOSTIC_HYPOTHESIS"),
                         fact("aspiration", assertion="ABSENT_NEGATED")]),
            report("b", [fact("edema", mapping="UNMAPPED")])]
    run = indicators.build_indicator_run(analyze(rows))
    finding, found = pair(run, "REPORT_FINDING_FREQUENCY")
    hypothesis, considered = pair(run, "DIAGNOSTIC_CONSIDERATION_FREQUENCY", assertion="FAVORED")
    negative, absent = pair(run, "DOCUMENTED_NEGATIVE_FREQUENCY", assertion="ABSENT")
    assert finding["target_concept_identity"] == "MRJ:edema" and found["numerator"] == 2
    assert hypothesis["target_hypothesis_status"] == "FAVORED" and considered["numerator"] == 1
    assert "diagnostic consideration" in hypothesis["name"].lower()
    assert negative["target_assertion"] == "ABSENT" and absent["numerator"] == 1
    assert "Documented absence" in negative["name"]
    assert "Documented absence: No " not in negative["name"]
    assert pair(run, "STANDARDIZATION_COVERAGE", field="whole_fact_matched")[1]["numerator"] == 0
    assert pair(run, "STANDARDIZATION_COVERAGE", field="unmapped")[1]["numerator"] == 4
    assert all("association" not in definition["interpretation_scope"].lower()
               and "causation" not in definition["interpretation_scope"].lower()
               for definition in run["definitions"])
    assert not any("target" in result for result in run["results"])


def test_validation_only_zero_denominator_and_coverage_zero_are_distinct():
    reviewed = analyze([report("review", [fact("edema")], standardize="NEEDS_REVIEW")], include=True)
    run = indicators.build_indicator_run(reviewed)
    assert pair(run, "REPORT_FINDING_FREQUENCY")[1]["readiness_state"] == "VALIDATION_ONLY"
    assert run["readiness_summary"]["VALIDATION_ONLY"] > 0
    assert run["analysis_policy"]["human_review_asserted"] is False
    date = pair(run, "DATA_COVERAGE", field="report_service_date")[1]
    assert (date["numerator"], date["denominator"], date["value"]) == (0, 1, 0.0)
    assert date["readiness_state"] == "VALIDATION_ONLY"
    conservative = indicators.build_indicator_run(analyze([report("review", standardize="NEEDS_REVIEW")]))
    modality = pair(conservative, "DATA_COVERAGE", field="modality")[1]
    assert modality["denominator"] == 0 and modality["value"] is None
    assert modality["readiness_state"] == "NOT_READY"
    assert "NO_ELIGIBLE_DENOMINATOR" in modality["warnings"]
    assert conservative["readiness_summary"]["READY"] == 0


def test_coverage_standardization_and_measurement_policy_copy_source_rows():
    measurement = {"source_measurement_id": "m1", "original_text": "1.4 cm", "normalized_value": "14",
                   "normalized_unit": "mm", "mapping_status": "MATCHED", "measurement_type": "diameter",
                   "dimension": "length"}
    analysis = analyze([report("a", [fact("lesion", measures=[measurement])], modality="CT"),
                        report("b", [fact("lesion", measures=[{**measurement, "source_measurement_id": "m2"}])],
                               modality=None)])
    run = indicators.build_indicator_run(analysis)
    modality = pair(run, "DATA_COVERAGE", field="modality")[1]
    source = next(row for row in analysis["coverage_metrics"] if row["field"] == "modality")
    assert (modality["numerator"], modality["denominator"], modality["value"]) == (
        source["numerator"], source["denominator"], source["value"])
    assert modality["coverage"]["missing"] == 1
    matched = pair(run, "STANDARDIZATION_COVERAGE", field="whole_fact_matched")[1]
    assert (matched["numerator"], matched["denominator"]) == (
        analysis["standardization_coverage"]["whole_fact_matched"],
        analysis["standardization_coverage"]["denominator_facts"])
    assert matched["value"] is None and "RATIO_NOT_PUBLISHED_BY_ANALYZE" in matched["warnings"]
    assert pair(run, "STANDARDIZATION_COVERAGE", field="whole_fact_matched")[0]["analysis_level"] == "FACT_LEVEL"
    measured = pair(run, "MEASUREMENT_SUMMARY")[1]
    source_measure = analysis["measurement_distributions"][0]
    assert (measured["numerator"], measured["denominator"], measured["value"]) == (
        source_measure["numerator"], source_measure["denominator"], source_measure["value"])
    assert measured["coverage"]["mean"] == source_measure["mean"]
    assert "source_measurement_id" not in str(run) and "original_text" not in str(run)
    empty_measure = pair(indicators.build_indicator_run(analyze([report("x")])), "MEASUREMENT_SUMMARY")[1]
    assert empty_measure["readiness_state"] == "NOT_READY" and empty_measure["value"] is None
    assert "INSUFFICIENT_DATA" in empty_measure["warnings"]


def test_definition_version_and_readiness_validation_are_governed():
    analysis = analyze([report("a")])
    definition, result = pair(indicators.build_indicator_run(analysis), "REPORT_FINDING_FREQUENCY")
    changed = deepcopy(definition)
    changed["denominator_definition"] = "A different denominator"
    changed["revision"] = indicators._digest({key: value for key, value in changed.items()
                                               if key not in {"indicator_id", "version", "revision"}})
    with pytest.raises(ValueError, match="INDICATOR_DEFINITION_VERSION_CONFLICT"):
        indicators.validate_definition_update(definition, changed)
    changed["version"] = definition["version"] + 1
    indicators.validate_definition_update(definition, changed)
    assert result["indicator_version"] == definition["version"] and result["definition_revision"] == definition["revision"]
    reviewed = deepcopy(definition)
    reviewed["status"] = "NEEDS_REVIEW"
    reviewed["revision"] = indicators._digest({key: value for key, value in reviewed.items()
                                                if key not in {"indicator_id", "version", "revision"}})
    assert indicators.evaluate_indicator(reviewed, analysis["finding_frequencies"][0], analysis,
                                         "finding_frequencies[0]")["readiness_state"] == "NEEDS_REVIEW"
    invalid = deepcopy(definition)
    invalid["denominator_definition"] = ""
    assert indicators.evaluate_indicator(invalid, analysis["finding_frequencies"][0], analysis,
                                         "finding_frequencies[0]")["readiness_state"] == "INVALID"
    timed = deepcopy(definition)
    timed["time_window_definition"] = "REPORT_SERVICE_DATE"
    timed["revision"] = indicators._digest({key: value for key, value in timed.items()
                                            if key not in {"indicator_id", "version", "revision"}})
    timed_result = indicators.evaluate_indicator(timed, analysis["finding_frequencies"][0], analysis,
                                                 "finding_frequencies[0]")
    assert timed_result["readiness_state"] == "NOT_READY"
    assert "MISSING_REQUIRED_DIMENSION" in timed_result["warnings"]


def test_store_http_roundtrip_and_exact_journey_attachment(tmp_path, monkeypatch):
    from backend.app.main import app
    from backend.app.modules.medical_document_intelligence.api import understanding as api

    store = ReportCollectionStore(tmp_path)
    collection = store.create("Synthetic indicators", [report("a", [fact("edema")])])
    analysis = store.analyze(collection["collection_id"])
    monkeypatch.setattr(indicators, "collection_store", store)
    monkeypatch.setattr(api, "indicator_store", indicators.IndicatorStore())
    journey = JourneyStore()
    run = journey.create_run("SINGLE")
    item = JourneyDocument("document", "synthetic.txt", 0, "txt")
    item.stage_status[JourneyStage.ANALYZE] = StageStatus.COMPLETE
    item.stage_results[JourneyStage.ANALYZE] = {"analysis_run_id": analysis["analysis_run_id"]}
    run.documents.append(item)
    monkeypatch.setattr(api, "journey_store", journey)
    client = TestClient(app)
    response = client.post(f"/api/v1/understanding/analysis-runs/{analysis['analysis_run_id']}/indicators",
                           json={"journey_run_id": run.run_id})
    assert response.status_code == 200
    output = response.json()
    assert client.get(f"/api/v1/understanding/indicator-runs/{output['indicator_run_id']}").json() == output
    assert client.post(f"/api/v1/understanding/analysis-runs/{analysis['analysis_run_id']}/indicators",
                       json={}).json() == output
    assert item.stage_results[JourneyStage.INDICATORS]["analysis_run_id"] == analysis["analysis_run_id"]
    assert item.stage_status[JourneyStage.INDICATORS] is StageStatus.COMPLETE
    assert run.current_stage is JourneyStage.INDICATORS
    other = journey.create_run("SINGLE")
    other_item = JourneyDocument("other", "other.txt", 0, "txt")
    other_item.stage_results[JourneyStage.ANALYZE] = {"analysis_run_id": "different"}
    other.documents.append(other_item)
    journey.attach_collection_indicators(other.run_id, output)
    assert other_item.stage_status[JourneyStage.INDICATORS] is StageStatus.NOT_STARTED
    missing = client.post("/api/v1/understanding/analysis-runs/" + "f" * 32 + "/indicators", json={})
    assert missing.status_code == 404 and missing.json()["detail"] == "SOURCE_ANALYSIS_NOT_AVAILABLE"
    stale_journey = client.post(f"/api/v1/understanding/analysis-runs/{analysis['analysis_run_id']}/indicators",
                                json={"journey_run_id": "missing-journey"})
    assert stale_journey.status_code == 404 and stale_journey.json()["detail"] == "JOURNEY_CONTEXT_NOT_AVAILABLE"


def test_rejects_incompatible_analysis_contract():
    analysis = analyze([report("a")])
    analysis["contract"] = "mrj-radiology-analysis-v0.3"
    with pytest.raises(ValueError, match="INCOMPATIBLE_ANALYSIS_RUN"):
        indicators.build_indicator_run(analysis)
