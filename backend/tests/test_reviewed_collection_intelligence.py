"""Phase E reviewed-only, version-pinned collection and analysis checks."""

import hashlib
import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.api import understanding as api
from backend.app.modules.medical_document_intelligence.contracts.reviewed_clinical_record import (
    ReviewedClinicalRecord, build_reviewed_record,
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


def record_for(number: int, *, profile="MRJ_RAD_US_ABDOMEN", coverage="DOCUMENTED", major=False):
    source = f"Right kidney measures {10 + number} cm."
    digest = hashlib.sha256(source.encode()).hexdigest()
    fact = {"fact_id": "renal-length", "fact_type": "MEASURED_OBSERVATION",
            "canonical_concept": "renal dimension", "display_label": "Right kidney dimension",
            "assertion_state": "PRESENT", "group": "KEY", "anatomy": ["right kidney"],
            "laterality": "RIGHT", "review_required": major,
            "review_reason": ["INTERNAL_SOURCE_CONFLICT"] if major else [],
            "evidence_anchors": [{"evidence_id": "e1", "start_offset": 0, "end_offset": len(source),
                                  "quote": source, "source_section": "FINDINGS_DESCRIPTION"}],
            "observations": [{"measurements": [f"{10 + number} cm"]}]}
    profile_data = {"profile_id": profile, "profile_version": "0.1", "scope": "COMPLETE",
                    "status": "EVALUATED", "coverage": [{"section_id": "right_kidney",
                    "coverage": coverage, "elements": [{"element_id": "right_kidney.length",
                    "coverage": coverage}, {"element_id": "left_kidney.length",
                    "coverage": "NOT_APPLICABLE"}]}]}
    return build_reviewed_record(
        run_id=f"{number:032x}", document_id=f"{number + 100:032x}",
        reviewed_at="2030-01-01T00:00:00Z",
        protect={"protected_document": {"report_id": f"{number + 100:032x}",
                "protected_text": source, "integrity_sha256": digest}},
        extract={"clinical_synthesis": {"clinical_synthesis": source, "canonical_facts": [fact]}},
        standardized={"state": "COMPLETE", "standardized_study_context": {
                "normalized_modality": "US", "normalized_body_region": "ABDOMEN",
                "normalized_laterality": "RIGHT"}, "standardized_facts": [{
                "source_fact_id": "renal-length", "concept_mappings": [],
                "standardized_measurements": [{"source_measurement_id": "m1",
                "original_text": f"{10 + number} cm", "normalized_value": 100 + 10 * number,
                "normalized_unit": "mm", "measurement_type": "ORGAN_LENGTH",
                "dimension": "LENGTH", "mapping_status": "MATCHED"}]}],
                "unassigned_measurements": []},
        profile_evaluation=profile_data, major_review_acknowledged=major)


def setup(tmp_path):
    records = SqliteReviewedClinicalRecordRepository(tmp_path / "records.sqlite3")
    repo = SqliteReviewedCollectionRepository(records, tmp_path / "collections.sqlite3")
    return records, repo, ReviewedCollectionIntelligence(repo)


def test_reviewed_gate_and_durable_major_acknowledgement(tmp_path):
    records, repo, _ = setup(tmp_path)
    first = record_for(1, major=True)
    records.save(first)
    rid = first.to_dict()["reviewed_record_id"]
    with pytest.raises(ValueError, match="unavailable"):
        repo.create_collection("Reject transient", [("f" * 32, 1)])
    with pytest.raises(ValueError, match="unavailable"):
        repo.create_collection("Reject missing version", [(rid, 2)])
    bad = first.to_dict()
    bad["major_review_acknowledged"] = False
    with pytest.raises(ValueError, match="acknowledgement"):
        ReviewedClinicalRecord.from_dict(bad)
    made = repo.create_collection("Reviewed renal", [(rid, 1)], creation_method="REVIEW_SESSION")
    assert made["member_count"] == 1 and made["state"] == "READY_FOR_ANALYSIS"
    assert repo.list_collections()[0]["collection_id"] == made["collection_id"]
    assert repo.get_members(made["collection_id"])[0].to_json() == first.to_json()


def test_draft_and_archived_states_preserve_membership_history(tmp_path):
    records, repo, intelligence = setup(tmp_path)
    record = record_for(7)
    records.save(record)
    rid = record.to_dict()["reviewed_record_id"]
    draft = repo.create_collection("Draft reviewed", [])
    cid = draft["collection_id"]
    assert draft["state"] == "DRAFT" and draft["member_count"] == 0
    with pytest.raises(ValueError, match="no reviewed records"):
        intelligence.analyze(cid)
    ready = repo.add_member(cid, rid, 1)
    assert ready["state"] == "READY_FOR_ANALYSIS" and ready["version"] == 2
    archived = repo.archive_collection(cid)
    assert archived["state"] == "ARCHIVED"
    assert repo.get_version(cid, 2)["members"][0]["reviewed_record_id"] == rid
    assert intelligence.analyze(cid)["collection_version"] == 2
    with pytest.raises(ValueError, match="Archived"):
        repo.remove_member(cid, rid)


def test_exact_version_pinning_restart_and_integrity(tmp_path):
    records, repo, intelligence = setup(tmp_path)
    first = record_for(1)
    records.save(first)
    rid = first.to_dict()["reviewed_record_id"]
    made = repo.create_collection("Versioned renal", [(rid, 1)])
    cid = made["collection_id"]
    first_run = intelligence.analyze(cid)
    second_data = first.to_dict()
    second_data["record_version"] = 2
    second_data["reviewed_at"] = "2030-01-02T00:00:00Z"
    second_data["clinical_summary"] = "Corrected summary."
    records.save(ReviewedClinicalRecord.from_dict(second_data))
    assert repo.get_version(cid, 1)["members"][0]["reviewed_record_version"] == 1
    assert repo.get_members(cid, 1)[0].to_json() == first.to_json()
    updated = repo.create_version(cid, [(rid, 2)])
    assert updated["version"] == 2
    second_run = intelligence.analyze(cid)
    assert first_run["analysis_run_id"] != second_run["analysis_run_id"]
    assert repo.get_analysis(first_run["analysis_run_id"])["collection_version"] == 1
    assert repo.get_analysis(first_run["analysis_run_id"]) == first_run
    repo.close(); records.close()
    reopened_records, reopened, _ = setup(tmp_path)
    assert reopened.get_version(cid, 1)["members"][0]["reviewed_record_version"] == 1
    assert reopened.get_collection(cid)["version"] == 2
    reopened_records._db().execute("DELETE FROM reviewed_record_versions WHERE record_id=? AND version=1", (rid,))
    reopened_records._db().commit()
    with pytest.raises(ValueError, match="unavailable"):
        reopened.get_version(cid, 1)
    reopened._db().execute("UPDATE reviewed_collection_heads SET current_version=999 WHERE collection_id=?", (cid,))
    reopened._db().commit()
    assert reopened.list_collections()[0]["integrity"] == "FAILED"


def test_analysis_denominators_measurement_lineage_and_scope_quality(tmp_path):
    records, repo, intelligence = setup(tmp_path)
    first, second = record_for(1), record_for(2, coverage="LIMITED_OR_NOT_VISUALIZED")
    for record in (first, second):
        records.save(record)
    made = repo.create_collection("Renal analysis", [
        (record.to_dict()["reviewed_record_id"], 1) for record in (first, second)])
    analysis = intelligence.analyze(made["collection_id"])
    assert analysis["collection_summary"]["included_reports"] == 2
    finding = analysis["finding_frequencies"][0]
    assert (finding["numerator"], finding["denominator"]) == (2, 2)
    assert analysis["eligibility_policy"]["human_review_asserted"] is True
    assert "cooccurrences" not in analysis
    contributors = intelligence.contributors(analysis["analysis_run_id"], "findings", 0)
    assert len(contributors["contributors"]) == 2
    assert all(row["evidence"]["quote"].startswith("Right kidney measures") for row in contributors["contributors"])
    measure = analysis["measurement_distributions"][0]
    assert measure["sample_count"] == 2 and measure["median"] == "115"
    assert measure["profile_context"] == "MRJ_RAD_US_ABDOMEN"
    measurement_rows = intelligence.contributors(analysis["analysis_run_id"], "measurements", 0)
    assert len(measurement_rows["contributors"]) == 2
    assert all(row["measurements"][0]["original_text"].endswith("cm") for row in measurement_rows["contributors"])
    quality = analysis["data_quality"]["profile_coverage"]
    length = next(row for row in quality if row["element_id"] == "right_kidney.length")
    assert (length["denominator"], length["documented"], length["limited"]) == (2, 1, 1)
    left = next(row for row in quality if row["element_id"] == "left_kidney.length")
    assert left["denominator"] == 0 and left["not_applicable"] == 2


def test_mixed_profile_quality_stays_separate(tmp_path):
    records, repo, intelligence = setup(tmp_path)
    first, second = record_for(1), record_for(2, profile="MRJ_RAD_MRI_SHOULDER")
    records.save(first); records.save(second)
    cid = repo.create_collection("Mixed", [(first.to_dict()["reviewed_record_id"], 1),
                                            (second.to_dict()["reviewed_record_id"], 1)])["collection_id"]
    analysis = intelligence.analyze(cid)
    groups = [row for row in analysis["data_quality"]["profile_coverage"]
              if row["element_id"] == "right_kidney.length"]
    assert len(groups) == 2 and all(row["denominator"] == 1 for row in groups)
    assert len(analysis["measurement_distributions"]) == 2


def test_profile_quality_keeps_not_documented_limited_and_out_of_scope_distinct(tmp_path):
    records, repo, intelligence = setup(tmp_path)
    values = [record_for(11, coverage="DOCUMENTED"),
              record_for(12, coverage="NOT_DOCUMENTED"),
              record_for(13, coverage="LIMITED_OR_NOT_VISUALIZED")]
    for record in values:
        records.save(record)
    refs = [(record.to_dict()["reviewed_record_id"], 1) for record in values]
    cid = repo.create_collection("Coverage variation", refs)["collection_id"]
    quality = intelligence.analyze(cid)["data_quality"]["profile_coverage"]
    renal = next(item for item in quality if item["element_id"] == "right_kidney.length")
    assert (renal["denominator"], renal["documented"], renal["not_documented"], renal["limited"]) == (3, 1, 1, 1)
    out_of_scope = next(item for item in quality if item["element_id"] == "left_kidney.length")
    assert out_of_scope["denominator"] == 0 and out_of_scope["not_applicable"] == 3


def test_reviewed_collection_http_and_legacy_route(monkeypatch, tmp_path):
    records, repo, intelligence = setup(tmp_path)
    record = record_for(1)
    records.save(record)
    monkeypatch.setattr(api, "reviewed_collection_intelligence", intelligence)
    client = TestClient(app)
    prefix = "/api/v1/understanding/reviewed-collections"
    rid = record.to_dict()["reviewed_record_id"]
    assert client.post(prefix, json={"name": "Invalid", "members": [
        {"reviewed_record_id": "f" * 32, "reviewed_record_version": 1}]}).status_code == 409
    created = client.post(prefix, json={"name": "Reviewed renal", "members": [
        {"reviewed_record_id": rid, "reviewed_record_version": 1}]}).json()
    cid = created["collection_id"]
    assert client.get(prefix).json()["collections"][0]["collection_id"] == cid
    assert client.get(f"{prefix}/{cid}").json()["member_count"] == 1
    assert client.get(f"{prefix}/{cid}/versions/1").json()["members"][0]["reviewed_record_id"] == rid
    result = client.post(f"{prefix}/{cid}/analyze").json()
    assert result["collection_summary"]["included_reports"] == 1
    aid = result["analysis_run_id"]
    assert client.get(f"/api/v1/understanding/reviewed-collection-analyses/{aid}/findings/0/contributors").status_code == 200
    assert client.get("/api/v1/understanding/analysis-collections").status_code == 200
