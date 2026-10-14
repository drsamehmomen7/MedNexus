"""Phase F governed questions over synthetic, exact-version reviewed records."""

import hashlib
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.api import understanding as api
from backend.app.modules.medical_document_intelligence.contracts.clinical_intelligence import (
    ClinicalIntelligenceProfileRegistry,
)
from backend.app.modules.medical_document_intelligence.contracts.reviewed_clinical_record import (
    ReviewedClinicalRecord, build_reviewed_record,
)
from backend.app.modules.medical_document_intelligence.services.clinical_insights import ClinicalInsightEngine
from backend.app.modules.medical_document_intelligence.services.clinical_intelligence_profiles import (
    MRI_SHOULDER_INTELLIGENCE, REGISTRY, US_ABDOMEN_INTELLIGENCE,
)
from backend.app.modules.medical_document_intelligence.services.reviewed_collection_intelligence import (
    ReviewedCollectionIntelligence,
)
from backend.app.modules.medical_document_intelligence.services.reviewed_collection_repository import (
    SqliteReviewedCollectionRepository,
)
from backend.app.modules.medical_document_intelligence.services.reviewed_record_repository import (
    SqliteReviewedClinicalRecordRepository,
)


def reviewed(number, concepts, *, profile="MRJ_RAD_US_ABDOMEN", scope=None,
             pancreas="DOCUMENTED", version=1):
    """Each clause is synthetic and receives an exact protected evidence anchor."""
    clauses = [f"{concept} documented." if assertion == "PRESENT" else
               f"No {concept} documented." if assertion == "ABSENT_NEGATED" else
               f"{concept} uncertain."
               for concept, assertion, *_ in concepts]
    text = " ".join(clauses) or "Synthetic reviewed report."
    cursor = 0
    facts = []
    for index, ((concept, assertion, anatomy, laterality), clause) in enumerate(zip(concepts, clauses)):
        start = text.index(clause, cursor)
        cursor = start + len(clause)
        facts.append({"fact_id": f"fact-{index}", "fact_type": "FINDING",
                      "canonical_concept": concept, "display_label": concept,
                      "assertion_state": assertion, "group": "KEY",
                      "anatomy": list(anatomy), "laterality": laterality,
                      "evidence_anchors": [{"evidence_id": f"e-{index}", "start_offset": start,
                                            "end_offset": cursor, "quote": clause,
                                            "source_section": "FINDINGS_DESCRIPTION"}]})
    digest = hashlib.sha256(text.encode()).hexdigest()
    is_mri = profile == "MRJ_RAD_MRI_SHOULDER"
    evaluation = {"profile_id": profile, "profile_version": "0.1",
                  "scope": scope or ("ROUTINE_MRI" if is_mri else "COMPLETE"),
                  "status": "EVALUATED", "coverage": [] if is_mri else [{
                      "section_id": "pancreas", "coverage": pancreas,
                      "elements": [{"element_id": "pancreas.visualization", "coverage": pancreas}]}]}
    return build_reviewed_record(
        run_id=f"{number:032x}", document_id=f"{number + 1000:032x}",
        reviewed_at="2030-01-01T00:00:00Z", schema_version=3,
        protect={"protected_document": {"report_id": f"{number + 1000:032x}",
                 "protected_text": text, "integrity_sha256": digest}},
        extract={"clinical_synthesis": {"clinical_synthesis": text, "canonical_facts": facts}},
        standardized={"state": "COMPLETE", "standardized_study_context": {
            "normalized_modality": "MRI" if is_mri else "US",
            "normalized_body_region": "SHOULDER" if is_mri else "ABDOMEN",
            "normalized_laterality": None}, "standardized_facts": [],
            "unassigned_measurements": []},
        profile_evaluation=evaluation,
    )


def fact(concept, assertion="PRESENT", anatomy=(), laterality=None):
    return concept, assertion, anatomy, laterality


def setup(tmp_path, values):
    records = SqliteReviewedClinicalRecordRepository(tmp_path / "records.sqlite3")
    for value in values:
        records.save(value)
    repository = SqliteReviewedCollectionRepository(records, tmp_path / "collections.sqlite3")
    refs = [(value.to_dict()["reviewed_record_id"], value.to_dict()["record_version"]) for value in values]
    collection = repository.create_collection("Synthetic Insight review", refs)
    intelligence = ReviewedCollectionIntelligence(repository)
    engine = ClinicalInsightEngine(intelligence)
    return records, repository, collection, engine


def item(run, insight_id):
    return next(result for profile in run["profiles"] for result in profile["definitions"]
                if result["insight_id"] == insight_id)


def test_registry_exact_profile_version_and_unsupported():
    assert REGISTRY.resolve("MRJ_RAD_US_ABDOMEN", "0.1") == US_ABDOMEN_INTELLIGENCE
    assert REGISTRY.resolve("MRJ_RAD_MRI_SHOULDER", "0.1") == MRI_SHOULDER_INTELLIGENCE
    assert REGISTRY.resolve("MRJ_RAD_US_ABDOMEN", "0.2") is None
    assert REGISTRY.resolve("MRJ_RAD_CT_CHEST", "0.1") is None
    assert REGISTRY.get("MRJ_INTEL_US_ABDOMEN", "0.1") == US_ABDOMEN_INTELLIGENCE
    assert REGISTRY.get("MRJ_INTEL_US_ABDOMEN", "9.9") is None


def test_reference_roles_are_distinct_and_pending_is_honest():
    definitions = [*US_ABDOMEN_INTELLIGENCE.definitions, *MRI_SHOULDER_INTELLIGENCE.definitions]
    assert len(definitions) == 8
    assert {item.insight_id for item in definitions if item.relationship_reference_status == "VERIFIED"} == {
        "US_STEATOSIS_GALLSTONES", "MRI_CUFF_TEAR_RETRACTION", "MRI_CUFF_TEAR_MUSCLE"}
    for definition in definitions:
        assert definition.exam_profile_reference.role == "EXAM_PROFILE_REFERENCE"
        assert definition.support.policy_role == "MRJ_POLICY"
        assert definition.support.policy_label == "MRJ V1 descriptive support policy"
        if definition.relationship_reference_status == "VERIFIED":
            assert definition.clinical_relationship_reference is not None
            assert definition.clinical_relationship_reference.role == "CLINICAL_RELATIONSHIP_REFERENCE"
            assert definition.clinical_relationship_reference.url != definition.exam_profile_reference.url
        else:
            assert definition.relationship_reference_status == "PENDING_VERIFICATION"
            assert definition.clinical_relationship_reference is None
        with pytest.raises(ValueError, match="exam/profile reference"):
            replace(definition, exam_profile_reference=definition.clinical_relationship_reference
                    or replace(definition.exam_profile_reference, role="CLINICAL_RELATIONSHIP_REFERENCE"))
        with pytest.raises(ValueError, match="verified relationship"):
            replace(definition, relationship_reference_status="VERIFIED", clinical_relationship_reference=None)
    coverage = next(item for item in definitions if item.insight_type == "COVERAGE_QUALITY")
    assert coverage.relationship_reference_status == "PENDING_VERIFICATION"
    assert coverage.clinical_relationship_reference is None
    with pytest.raises(ValueError, match="Coverage-quality"):
        replace(coverage, clinical_relationship_reference=next(
            item.clinical_relationship_reference for item in definitions
            if item.relationship_reference_status == "VERIFIED"),
            relationship_reference_status="VERIFIED")


def test_support_thresholds_remain_mrj_descriptive_policy():
    for profile in (US_ABDOMEN_INTELLIGENCE, MRI_SHOULDER_INTELLIGENCE):
        for definition in profile.definitions:
            support = definition.support
            assert support.policy_role == "MRJ_POLICY"
            if definition.insight_type == "CO_DOCUMENTATION":
                assert (support.minimum_eligible_n, support.minimum_group_n,
                        support.minimum_event_support) == (6, 2, 2)
            elif definition.insight_type == "FINDING_CONTEXT":
                assert (support.minimum_eligible_n, support.minimum_group_n,
                        support.minimum_event_support) == (3, 1, 2)
            else:
                assert definition.insight_type == "COVERAGE_QUALITY"
                assert (support.minimum_eligible_n, support.minimum_group_n,
                        support.minimum_event_support) == (5, 1, 0)


def test_hepatomegaly_ascites_explicit_denominators_and_lineage(tmp_path):
    values = []
    for n in range(1, 5):
        values.append(reviewed(n, [fact("hepatomegaly"),
                                  fact("ascites", "PRESENT" if n <= 2 else "ABSENT_NEGATED"),
                                  fact("pancreas")]))
    for n in range(5, 9):
        values.append(reviewed(n, [fact("hepatomegaly", "ABSENT_NEGATED"),
                                  fact("ascites", "PRESENT" if n == 5 else "ABSENT_NEGATED"),
                                  fact("pancreas")]))
    values.append(reviewed(9, [fact("ascites"), fact("pancreas")]))
    values.append(reviewed(10, [fact("hepatomegaly"), fact("ascites", "UNCERTAIN"), fact("pancreas")]))
    records, repo, collection, engine = setup(tmp_path, values)
    run = engine.analyze(collection["collection_id"])
    result = item(run, "US_HEPATOMEGALY_ASCITES")
    assert result["state"] == "OBSERVATION_AVAILABLE"
    assert result["eligible_n"] == 8
    assert [(g["numerator"], g["denominator"]) for g in result["groups"]] == [(2, 4), (1, 4)]
    assert result["exclusions"]["NOT_DOCUMENTED"] == 1
    assert result["exclusions"]["INDETERMINATE"] == 1
    assert run["analysis_level"] == "REPORT"
    assert run["profiles"][0]["intelligence_profile_version"] == "0.1"
    lineage = engine.contributors(run["insight_run_id"], result["insight_id"], "with")
    assert len(lineage["contributors"]) == 4
    assert all(row["reviewed_record_version"] == 1 and len(row["facts"]) == 2
               and all(evidence["quote"] for evidence in row["facts"])
               for row in lineage["contributors"])
    assert repo.get_insights(run["insight_run_id"]) == run
    repo.close(); records.close()


def test_steatosis_gallstones_and_no_clear_pattern(tmp_path):
    values = [reviewed(n, [fact("hepatic steatosis", "PRESENT" if n <= 3 else "ABSENT_NEGATED"),
                           fact("gallstones", "PRESENT" if n in {1, 2, 4, 5} else "ABSENT_NEGATED")])
              for n in range(1, 7)]
    _, _, collection, engine = setup(tmp_path, values)
    result = item(engine.analyze(collection["collection_id"]), "US_STEATOSIS_GALLSTONES")
    assert result["state"] == "NO_CLEAR_DESCRIPTIVE_PATTERN"
    assert [(g["numerator"], g["denominator"]) for g in result["groups"]] == [(2, 3), (2, 3)]
    assert "No clear descriptive difference" in result["summary"]


def test_renal_same_side_and_explicit_outcome(tmp_path):
    values = [reviewed(n, [fact("right renal calculus", anatomy=("right kidney",), laterality="RIGHT"),
                           fact("left hydronephrosis", anatomy=("left kidney",), laterality="LEFT"),
                           fact("right hydronephrosis", "PRESENT" if n <= 2 else "ABSENT_NEGATED",
                                anatomy=("right kidney",), laterality="RIGHT")])
              for n in range(1, 5)]
    _, _, collection, engine = setup(tmp_path, values)
    result = item(engine.analyze(collection["collection_id"]), "US_RENAL_CALCULUS_HYDRONEPHROSIS")
    assert result["state"] == "OBSERVATION_AVAILABLE"
    assert result["groups"][0]["numerator"] == 2
    assert result["groups"][0]["denominator"] == 4


def test_pancreas_coverage_and_out_of_scope(tmp_path):
    values = [reviewed(n, [fact("pancreas")], pancreas="DOCUMENTED" if n <= 4 else
                       "LIMITED_OR_NOT_VISUALIZED") for n in range(1, 7)]
    values.append(reviewed(7, [], pancreas="NOT_APPLICABLE"))
    values.append(reviewed(8, [], pancreas="NOT_DOCUMENTED"))
    _, _, collection, engine = setup(tmp_path, values)
    run = engine.analyze(collection["collection_id"])
    result = item(run, "US_PANCREAS_VISUALIZATION")
    assert result["state"] == "OBSERVATION_AVAILABLE"
    assert result["eligible_n"] == 7
    assert [(g["numerator"], g["denominator"]) for g in result["groups"]] == [(4, 7), (2, 7), (1, 7)]
    assert result["exclusions"]["NOT_APPLICABLE"] == 1
    contributors = engine.contributors(run["insight_run_id"], result["insight_id"], "documented")
    assert len(contributors["contributors"]) == 4
    assert all(not row["facts"] and row["coverage"] == "DOCUMENTED"
               for row in contributors["contributors"])


@pytest.mark.parametrize("insight_id,exposure,outcome", [
    ("MRI_LABRAL_TEAR_HILL_SACHS", "labral tear", "hill-sachs lesion"),
    ("MRI_BANKART_HILL_SACHS", "bony bankart", "hill-sachs lesion"),
    ("MRI_CUFF_TEAR_RETRACTION", "supraspinatus tear", "tendon retraction"),
    ("MRI_CUFF_TEAR_MUSCLE", "supraspinatus tear", "fatty degeneration"),
])
def test_mri_questions_keep_specific_anatomy(tmp_path, insight_id, exposure, outcome):
    anatomy = ("supraspinatus", "muscle") if outcome == "fatty degeneration" else (
        ("supraspinatus", "tendon") if outcome == "tendon retraction" else ())
    values = [reviewed(n, [fact(exposure), fact(outcome, "PRESENT" if n <= 2 else "ABSENT_NEGATED",
                                               anatomy=anatomy)], profile="MRJ_RAD_MRI_SHOULDER")
              for n in range(1, 5)]
    _, _, collection, engine = setup(tmp_path, values)
    result = item(engine.analyze(collection["collection_id"]), insight_id)
    assert result["state"] == "OBSERVATION_AVAILABLE"
    assert (result["groups"][0]["numerator"], result["groups"][0]["denominator"]) == (2, 4)


def test_sparse_support_abstains_without_false_claim(tmp_path):
    values = [reviewed(n, [fact("hepatomegaly"), fact("ascites", "PRESENT" if n == 1 else "ABSENT_NEGATED")])
              for n in range(1, 4)]
    _, _, collection, engine = setup(tmp_path, values)
    result = item(engine.analyze(collection["collection_id"]), "US_HEPATOMEGALY_ASCITES")
    assert result["state"] == "INSUFFICIENT_DATA"
    assert result["eligible_n"] == 3
    assert result["groups"][0]["denominator"] == 3
    assert "no relationship" not in result["summary"].lower()


def test_mixed_profile_groups_and_unsupported_excluded(tmp_path):
    values = [reviewed(1, [fact("hepatomegaly"), fact("ascites")]),
              reviewed(2, [fact("labral tear"), fact("hill-sachs lesion")],
                       profile="MRJ_RAD_MRI_SHOULDER"),
              reviewed(3, [fact("other finding")], profile="MRJ_RAD_CT_CHEST")]
    _, _, collection, engine = setup(tmp_path, values)
    run = engine.analyze(collection["collection_id"])
    assert len(run["profiles"]) == 2 and run["unsupported_profile_records"] == 1
    assert all(group["compatible_reviewed_reports"] == 1 for group in run["profiles"])
    assert run["summary"]["relationships_evaluated"] == 8


def test_collection_and_intelligence_versions_are_immutable(tmp_path):
    first = reviewed(1, [fact("hepatomegaly"), fact("ascites")])
    records, repo, collection, engine = setup(tmp_path, [first])
    cid = collection["collection_id"]
    old = engine.analyze(cid)
    data = first.to_dict()
    data["record_version"] = 2
    data["reviewed_at"] = "2030-01-02T00:00:00Z"
    records.save(ReviewedClinicalRecord.from_dict(data))
    assert engine.analyze(cid) == old
    repo.create_version(cid, [(data["reviewed_record_id"], 2)])
    newer = engine.analyze(cid)
    assert newer["insight_run_id"] != old["insight_run_id"]
    changed = replace(US_ABDOMEN_INTELLIGENCE, version="0.2")
    registry = ClinicalIntelligenceProfileRegistry((US_ABDOMEN_INTELLIGENCE, changed),
                                                    {"MRJ_INTEL_US_ABDOMEN": "0.2"})
    next_profile = ClinicalInsightEngine(engine.intelligence, registry).analyze(cid)
    assert next_profile["insight_run_id"] != newer["insight_run_id"]
    assert repo.get_insights(old["insight_run_id"]) == old
    repo.close(); records.close()


def test_http_insights_and_contributor_route(monkeypatch, tmp_path):
    values = [reviewed(n, [fact("hepatomegaly"), fact("ascites")]) for n in range(1, 4)]
    _, _, collection, engine = setup(tmp_path, values)
    monkeypatch.setattr(api, "reviewed_collection_intelligence", engine.intelligence)
    client = TestClient(app)
    cid = collection["collection_id"]
    response = client.post(f"/api/v1/understanding/reviewed-collections/{cid}/insights")
    assert response.status_code == 200
    run = response.json()
    assert client.get(f"/api/v1/understanding/reviewed-collection-insights/{run['insight_run_id']}").json() == run
    path = (f"/api/v1/understanding/reviewed-collection-insights/{run['insight_run_id']}"
            "/US_HEPATOMEGALY_ASCITES/with/contributors")
    result = client.get(path)
    assert result.status_code == 200 and len(result.json()["contributors"]) == 3


def test_language_is_report_level_descriptive_and_reference_metadata_present(tmp_path):
    _, _, collection, engine = setup(tmp_path, [reviewed(1, [fact("pancreas")])])
    run = engine.analyze(collection["collection_id"])
    for result in run["profiles"][0]["definitions"]:
        for field in ("summary", "question"):
            assert not any(word in result[field].lower()
                           for word in ("prevalence", "risk", "causes", "predicts", "significant", "reliably"))
        assert result["analysis_level"] == "REPORT"
        assert result["exam_profile_reference"]["url"].startswith("https://")
        assert result["exam_profile_reference"]["role"] == "EXAM_PROFILE_REFERENCE"
        assert result["support_policy"]["policy_role"] == "MRJ_POLICY"
        if result["relationship_reference_status"] == "PENDING_VERIFICATION":
            assert result["clinical_relationship_reference"] is None
        else:
            assert result["clinical_relationship_reference"]["role"] == "CLINICAL_RELATIONSHIP_REFERENCE"
        if result["state"] == "INSUFFICIENT_DATA":
            assert result["summary"] == "Not enough eligible reviewed reports under the current MRJ support policy."
