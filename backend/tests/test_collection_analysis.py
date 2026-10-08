"""R4.0A governed collection contracts; all records are synthetic."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from backend.app.modules.medical_document_intelligence.services.collection_analysis import (
    ReportCollectionStore, _age_band, _report_year, analyze_collection, eligibility, governed_report_snapshot,
)
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyDocument, JourneyStage, JourneyStore, StageStatus,
)


def fact(name="edema", *, assertion="PRESENT", hypothesis=None, mapping="UNMAPPED", code=None,
         scope="WHOLE_LABEL", anatomy=None, laterality=None, components=0, measures=None, kind="FINDING"):
    return {"fact_id": "fact-" + name, "canonical_concept": name, "display_label": name,
            "fact_type": kind, "assertion_state": assertion, "hypothesis_status": hypothesis,
            "anatomy": anatomy or [], "laterality": laterality, "review_required": False,
            "mapping": {"terminology_system": "RADLEX_CURRENT", "code": code,
                        "mapping_status": mapping, "lookup_scope": scope},
            "component_mapping_count": components, "measurements": measures or []}


def report(identifier, facts=None, *, extract="COMPLETE", standardize="COMPLETE", protect="COMPLETE",
           modality="CT", body="HEAD", batch=None, review="CLEAR", coverage_failure=False):
    return {"report_id": identifier, "origin_run_id": "run-" + identifier,
            "origin_document_id": identifier, "batch_id": batch, "domain": "RADIOLOGY",
            "stage_status": {"PROTECT": protect, "EXTRACT": extract, "STANDARDIZE": standardize},
            "review_status": review, "synthesis_coverage_failure": coverage_failure,
            "dimensions": {"modality": modality, "body_region": body, "laterality": None,
                           "report_year": None, "sex": None, "age_band": None, "facility": None,
                           "region": None, "batch_id": batch, "standardization_status": standardize},
            "facts": facts if facts is not None else [fact()]}


def analyze(reports, *, include=False, filters=None):
    collection = {"collection_id": "a" * 32, "name": "Synthetic validation collection",
                  "domain": "RADIOLOGY", "inclusion_policy": "EXPLICIT_REPORT_MEMBERSHIP"}
    snapshot = {"version": 1, "created_at": "2026-10-05T00:00:00Z", "reports": reports}
    return analyze_collection(collection, snapshot, include_review_required=include, filters=filters)


def test_collection_is_separate_from_batch_and_versions_are_immutable(tmp_path):
    store = ReportCollectionStore(tmp_path)
    first = store.create("Synthetic validation", [report("a", batch="batch-1")])
    before = store.analyze(first["collection_id"])
    added = store.add_reports(first["collection_id"], [report("b", batch="batch-2")])
    after = store.analyze(first["collection_id"])
    old_collection, old_snapshot = store.get(first["collection_id"], version=1)
    assert first["report_count"] == 1 and added["report_count"] == 2
    assert old_snapshot["reports"][0]["batch_id"] == "batch-1"
    assert {item["batch_id"] for item in store.get(first["collection_id"])[1]["reports"]} == {"batch-1", "batch-2"}
    assert before["collection_version"] == 1 and after["collection_version"] == 2
    assert store.get_analysis(before["analysis_run_id"]) == before
    assert store.analyze(first["collection_id"], version=1) == before
    assert store.list()[0]["collection_id"] == first["collection_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        store.add_reports(first["collection_id"], [report("a")])
    assert store.get(first["collection_id"])[0]["version"] == 2
    with pytest.raises(ValueError, match="INVALID_COLLECTION_VERSION"):
        store.get(first["collection_id"], version=999)


def test_eligibility_and_explicit_validation_policy_keep_denominator_honest():
    rows = [report("eligible"), report("review", standardize="NEEDS_REVIEW"),
            report("failed", extract="FAILED"), report("blocked", extract="BLOCKED"),
            report("coverage", coverage_failure=True), report("empty", facts=[]),
            report("std-failed", standardize="FAILED")]
    assert [eligibility(item)["status"] for item in rows] == [
        "ELIGIBLE", "NEEDS_REVIEW", "EXCLUDED", "EXCLUDED", "EXCLUDED", "EXCLUDED", "EXCLUDED"]
    default = analyze(rows)
    explicit = analyze(rows, include=True)
    assert default["collection_summary"]["included_reports"] == 1
    assert explicit["collection_summary"]["included_reports"] == 2
    assert explicit["collection_summary"]["included_review_required_reports"] == 1
    assert explicit["eligibility_policy"]["human_review_asserted"] is False
    assert {row["report_id"] for row in explicit["eligibility_summary"]["reports"] if row["status"] == "EXCLUDED"} == {
        "failed", "blocked", "coverage", "empty", "std-failed"}
    assert default["finding_frequencies"][0]["denominator"] == 1
    assert explicit["finding_frequencies"][0]["denominator"] == 2
    assert explicit["patient_level_analysis"] == "NOT_AVAILABLE"


def test_report_frequency_deduplicates_facts_ignores_raw_mentions_and_preserves_assertions():
    duplicate = fact("edema")
    first = report("one", [duplicate, {**duplicate, "fact_id": "different-anchor"},
                           fact("thrombosis", assertion="ABSENT_NEGATED"),
                           fact("tumor", assertion="UNCERTAIN", hypothesis="FAVORED", kind="DIAGNOSTIC_HYPOTHESIS")])
    first["raw_engine_candidate_count"] = 218
    second = report("two", [fact("edema"), fact("tumor", assertion="UNCERTAIN",
                                                 hypothesis="LESS_LIKELY", kind="DIAGNOSTIC_HYPOTHESIS")])
    output = analyze([first, second])
    edema = output["finding_frequencies"][0]
    assert edema["numerator"] == 2 and edema["denominator"] == 2
    assert output["pertinent_negative_frequencies"][0]["assertion"] == "ABSENT"
    assert {row["assertion"] for row in output["diagnostic_hypothesis_frequencies"]} == {"FAVORED", "LESS_LIKELY"}
    assert all(row["numerator"] <= row["denominator"] for row in output["finding_frequencies"])
    assert all("raw_engine" not in str(row) for row in output["finding_frequencies"])
    assert output["collection_summary"]["facts_total"] == 6  # facts and report occurrences are different counts


def test_unmapped_and_component_only_do_not_overcollapse_or_lose_anatomy():
    fracture = fact("coracoid_fracture", mapping="NEEDS_REVIEW", components=1,
                    anatomy=["coracoid process"], laterality="LEFT")
    other = fact("femur_fracture", mapping="NEEDS_REVIEW", components=1,
                 anatomy=["femur"], laterality="RIGHT")
    output = analyze([report("a", [fracture]), report("b", [other])])
    assert len(output["finding_frequencies"]) == 2
    assert {row["concept_identity"] for row in output["finding_frequencies"]} == {
        "MRJ:coracoid_fracture", "MRJ:femur_fracture"}
    assert output["standardization_coverage"]["component_mappings_available"] == 2
    assert output["standardization_coverage"]["whole_fact_matched"] == 0
    matched = fact("fracture", mapping="MATCHED", code="RID4650", scope="WHOLE_LABEL")
    assert analyze([report("c", [matched])])["finding_frequencies"][0]["concept_identity"] == "RADLEX_CURRENT:RID4650"


def test_measurement_distribution_requires_type_dimension_and_normalized_unit():
    a = {"source_measurement_id": "m1", "original_text": "1.4 cm", "normalized_value": "14",
         "normalized_unit": "mm", "mapping_status": "MATCHED", "measurement_type": "diameter", "dimension": "length"}
    b = {**a, "source_measurement_id": "m2", "original_text": "14 mm"}
    c = {**a, "source_measurement_id": "m3", "normalized_value": "20", "measurement_type": "depth"}
    unknown = {**a, "source_measurement_id": "m4", "measurement_type": None}
    unitless = {**a, "source_measurement_id": "m5", "original_text": "5", "normalized_value": None,
                "normalized_unit": None, "mapping_status": "NEEDS_REVIEW"}
    output = analyze([report("a", [fact("lesion", measures=[a, c, unknown, unitless]),
                                   fact("lesion", assertion="ABSENT_NEGATED", measures=[a])]),
                      report("b", [fact("lesion", measures=[b])])])
    diameter = next(row for row in output["measurement_distributions"] if row["measurement_type"] == "diameter")
    assert diameter["sample_count"] == 2 and diameter["minimum"] == "14" and diameter["maximum"] == "14"
    assert diameter["mean"] == "14" and diameter["median"] == "14"
    assert {row["measurement_type"] for row in output["measurement_distributions"]} == {"diameter", "depth"}
    assert output["measurement_coverage"]["unclassified_measurements"] == 3
    assert {item["original_text"] for item in diameter["original_measurements"]} == {"1.4 cm", "14 mm"}


def test_present_cooccurrence_only_and_filters_recompute_denominator():
    first = report("one", [fact("edema"), fact("mass"), fact("thrombosis", assertion="ABSENT_NEGATED")], modality="MRI")
    second = report("two", [fact("edema"), fact("mass")], modality="CT")
    third = report("three", [fact("edema"), fact("tumor", hypothesis="POSSIBLE",
                                                       kind="DIAGNOSTIC_HYPOTHESIS")], modality=None)
    output = analyze([first, second, third])
    pairs = output["cooccurrences"]
    assert len(pairs) == 1 and pairs[0]["numerator"] == 2 and pairs[0]["denominator"] == 3
    assert pairs[0]["metric_type"] == "report_level_cooccurrence"
    assert output["cooccurrence_presentation"]["repeated_patterns"] == pairs
    assert "association" not in str(pairs).lower()
    filtered = analyze([first, second, third], filters={"modality": "MRI"})
    assert filtered["collection_summary"]["included_reports"] == 1
    assert filtered["cooccurrences"][0]["denominator"] == 1
    assert filtered["cooccurrence_presentation"]["repeated_patterns"] == []
    assert filtered["cooccurrence_presentation"]["total_valid_pairs"] == 1
    assert filtered["eligibility_policy"]["filters"] == {"modality": "MRI"}
    assert {row["category"] for row in output["stratifications"] if row["dimension"] == "modality"} == {"MRI", "CT", "MISSING"}
    assert next(row for row in output["coverage_metrics"] if row["field"] == "modality")["missing"] == 1
    assert next(row for row in output["coverage_metrics"] if row["field"] == "report_service_date")["missing"] == 3
    assert {row["category"] for row in output["stratifications"] if row["dimension"] == "assertion"} == {"PRESENT", "ABSENT"}


def test_only_known_safe_age_and_report_date_supply_analytic_buckets():
    assert _age_band({"age": {"state": "KNOWN", "value": 17}}) == "0-17"
    assert _age_band({"age": {"state": "KNOWN", "value": 65}}) == "65+"
    assert _age_band({"age": {"state": "NOT_AVAILABLE", "value": 42}}) is None
    assert _report_year({"safe_time_context": {"state": "KNOWN", "value": "2024-06-12"}}) == 2024
    assert _report_year({"safe_time_context": {"state": "UNKNOWN", "value": "2024-06-12"}}) is None


def test_zero_denominator_has_no_fabricated_percentage_or_frequency():
    output = analyze([report("review", standardize="NEEDS_REVIEW")])
    assert "ALL_REPORTS_REQUIRE_REVIEW" in output["diagnostics"]
    assert output["finding_frequencies"] == []
    assert output["coverage_metrics"][0]["denominator"] == 0
    assert output["coverage_metrics"][0]["value"] is None


def test_all_hypothesis_statuses_remain_distinct_and_never_become_present_findings():
    statuses = ("FAVORED", "POSSIBLE", "LESS_FAVORED", "LESS_LIKELY")
    rows = [report(str(index), [fact("tumor", assertion="UNCERTAIN", hypothesis=status,
                                     kind="DIAGNOSTIC_HYPOTHESIS")]) for index, status in enumerate(statuses)]
    output = analyze(rows)
    assert {row["assertion"] for row in output["diagnostic_hypothesis_frequencies"]} == set(statuses)
    assert output["finding_frequencies"] == []
    assert all(row["numerator"] == 1 and row["denominator"] == 4 for row in output["diagnostic_hypothesis_frequencies"])


def test_findings_in_different_reports_do_not_cooccur():
    output = analyze([report("a", [fact("edema")]), report("b", [fact("mass")])])
    assert output["cooccurrences"] == []


def test_cooccurrence_default_hides_one_off_but_preserves_full_analytical_rows():
    rows = [report("a", [fact("edema"), fact("mass")]),
            report("b", [fact("edema"), fact("mass")]),
            report("c", [fact("edema"), fact("mass")]),
            report("d", [fact("edema"), fact("one_off"),
                         fact("negative", assertion="ABSENT_NEGATED"),
                         fact("possible", assertion="UNCERTAIN", hypothesis="POSSIBLE",
                              kind="DIAGNOSTIC_HYPOTHESIS")])]
    output = analyze(rows)
    pairs = output["cooccurrences"]
    presentation = output["cooccurrence_presentation"]
    assert [(row["numerator"], row["denominator"]) for row in pairs] == [(3, 4), (1, 4)]
    assert presentation["minimum_support"] == 2 and presentation["top_n"] == 20
    assert presentation["repeated_patterns"] == pairs[:1]
    assert presentation["total_valid_pairs"] == 2 and presentation["one_off_pairs"] == 1
    assert len(output["finding_frequencies"]) == 3
    assert output["eligibility_summary"]["included_report_ids"] == ["a", "b", "c", "d"]
    assert len(output["pertinent_negative_frequencies"]) == 1
    assert len(output["diagnostic_hypothesis_frequencies"]) == 1
    assert all("negative" not in str(row) and "possible" not in str(row) for row in pairs)


def test_cooccurrence_full_result_and_deterministic_top_twenty():
    concepts = [fact(f"finding_{index:02}") for index in range(23)]
    rows = [report("a", concepts), report("b", concepts),
            report("c", concepts[:2])]
    output = analyze(rows)
    full = output["cooccurrences"]
    displayed = output["cooccurrence_presentation"]["repeated_patterns"]
    assert len(full) == 253 and len(displayed) == 20
    assert displayed[0]["numerator"] == 3 and displayed[0]["denominator"] == 3
    assert all(row["numerator"] >= 2 and row["denominator"] == 3 for row in displayed)
    assert displayed == sorted(displayed, key=lambda row: (-row["numerator"], -row["value"],
                                                      row["concept_a"], row["concept_b"]))
    assert output["cooccurrence_presentation"]["total_valid_pairs"] == 253
    reordered = analyze(list(reversed(rows)))["cooccurrence_presentation"]
    assert [(row["concept_a"], row["concept_b"], row["numerator"], row["denominator"], row["value"])
            for row in reordered["repeated_patterns"]] == [
                (row["concept_a"], row["concept_b"], row["numerator"], row["denominator"], row["value"])
                for row in displayed]


def test_journey_snapshot_excludes_source_and_engine_evidence_and_stage_05_attaches(tmp_path):
    store = JourneyStore()
    run = store.create_run("BATCH")
    context = SimpleNamespace(identity=SimpleNamespace(healthcare_domain="RADIOLOGY"),
        clinical_context=SimpleNamespace(modality="MRI", body_region="HEAD", domain_extension=None))
    item = JourneyDocument("document", "synthetic.txt", 0, "txt", context=context)
    item.content_digest = "abc"
    item.stage_status[JourneyStage.PROTECT] = StageStatus.COMPLETE
    item.stage_status[JourneyStage.EXTRACT] = StageStatus.COMPLETE
    item.stage_status[JourneyStage.STANDARDIZE] = StageStatus.COMPLETE
    item.review_status = "CLEAR"
    item.stage_results[JourneyStage.EXTRACT] = {"raw_candidates": [{"quote": "SECRET"}],
        "clinical_synthesis": {"canonical_facts": [{"fact_id": "f1", "canonical_concept": "edema",
            "display_label": "edema", "fact_type": "FINDING", "assertion_state": "PRESENT",
            "evidence_anchors": [{"quote": "SECRET"}], "anatomy": [], "observations": []}]}}
    item.stage_results[JourneyStage.STANDARDIZE] = {"standardized_facts": [{"source_fact_id": "f1",
        "concept_mappings": [{"mapping_status": "UNMAPPED"}], "component_mappings": [],
        "standardized_measurements": []}], "standardized_study_context": {}}
    run.documents.append(item)
    snapshot = store.governed_report_snapshots([(run.run_id, item.document_id)])[0]
    assert snapshot["report_id"] == "source:abc"
    assert "SECRET" not in str(snapshot) and "raw_candidates" not in str(snapshot)
    collection_store = ReportCollectionStore(tmp_path)
    collection = collection_store.create("Synthetic", [snapshot])
    analysis = collection_store.analyze(collection["collection_id"])
    store.attach_collection_analysis(run.run_id, analysis, {snapshot["report_id"]})
    assert item.stage_status[JourneyStage.ANALYZE] is StageStatus.COMPLETE
    assert item.stage_results[JourneyStage.ANALYZE]["analysis_run_id"] == analysis["analysis_run_id"]
    assert run.current_stage is JourneyStage.ANALYZE


def test_journey_snapshot_uses_governed_protect_context_fields():
    store = JourneyStore()
    run = store.create_run("SINGLE")
    item = JourneyDocument("document", "synthetic.txt", 0, "txt")
    item.stage_results[JourneyStage.PROTECT] = {"patient_analytic_context": {"fields": {
        "sex": {"state": "KNOWN", "value": "FEMALE"},
        "facility_context": {"state": "KNOWN", "value": "Facility A"},
        "safe_time_context": {"state": "KNOWN", "value": {"report_year": 2024}},
    }}}
    run.documents.append(item)
    dimensions = governed_report_snapshot(run, item)["dimensions"]
    assert dimensions["sex"] == "FEMALE"
    assert dimensions["facility"] == "Facility A"
    assert dimensions["report_year"] == 2024


def test_atomic_source_identity_prevents_cross_journey_duplicate_membership(tmp_path):
    store = JourneyStore()
    one = store.create_run("SINGLE")
    two = store.create_run("SINGLE")
    for run in (one, two):
        item = JourneyDocument("document", "synthetic.pdf", 0, "pdf")
        item.source_artifact = b"same synthetic PDF bytes"
        run.documents.append(item)
    first = store.governed_report_snapshots([(one.run_id, "document")])[0]
    second = store.governed_report_snapshots([(two.run_id, "document")])[0]
    assert first["report_id"] == second["report_id"]
    collection_store = ReportCollectionStore(tmp_path)
    collection = collection_store.create("Duplicate check", [first])
    with pytest.raises(ValueError, match="Duplicate"):
        collection_store.add_reports(collection["collection_id"], [second])


def test_v0_scientific_language_is_report_frequency_not_population_claim():
    output = analyze([report("a")])
    text = str(output).lower()
    for forbidden in ("population prevalence", "incidence", "caused by", "association"):
        assert forbidden not in text
    required = {"metric_type", "analysis_level", "numerator", "denominator", "value",
                "eligibility_rule", "exclusions", "collection_id", "collection_version", "analysis_run_id"}
    for section in ("finding_frequencies", "diagnostic_hypothesis_frequencies", "pertinent_negative_frequencies",
                    "measurement_distributions", "stratifications", "cooccurrences", "coverage_metrics"):
        assert all(required <= set(metric) for metric in output[section])


def test_collection_http_creation_analysis_and_version_readback(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.modules.medical_document_intelligence.api import understanding as api

    store = ReportCollectionStore(tmp_path)
    synthetic = report("one")
    monkeypatch.setattr(api, "collection_store", store)
    monkeypatch.setattr(api.journey_store, "governed_report_snapshots", lambda refs: [deepcopy(synthetic)])
    client = TestClient(app)
    created = client.post("/api/v1/understanding/analysis-collections", json={
        "name": "Synthetic validation", "report_refs": [{"run_id": "r", "document_id": "d"}]})
    assert created.status_code == 200
    identifier = created.json()["collection_id"]
    assert client.get("/api/v1/understanding/analysis-collections").json()["collections"][0]["collection_id"] == identifier
    response = client.post(f"/api/v1/understanding/analysis-collections/{identifier}/analyze", json={})
    assert response.status_code == 200
    analysis = response.json()
    assert analysis["collection_version"] == 1
    assert client.get(f"/api/v1/understanding/analysis-runs/{analysis['analysis_run_id']}").json() == analysis
    assert client.post(f"/api/v1/understanding/analysis-collections/{identifier}/analyze", json={}).json() == analysis
    bad = client.post(f"/api/v1/understanding/analysis-collections/{identifier}/analyze",
                      json={"collection_version": 99})
    assert bad.status_code == 409 and bad.json()["detail"] == "INVALID_COLLECTION_VERSION"
    monkeypatch.setattr(store, "analyze", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("synthetic internal detail")))
    failed = client.post(f"/api/v1/understanding/analysis-collections/{identifier}/analyze", json={})
    assert failed.status_code == 500 and failed.json()["detail"] == "ANALYSIS_RUNTIME_FAILURE"
