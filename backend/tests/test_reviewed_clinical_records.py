"""Synthetic acceptance, restart, version and privacy tests for C.3."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.api import understanding as api
from backend.app.modules.medical_document_intelligence.contracts.reviewed_clinical_record import (
    ReviewedClinicalRecord, build_reviewed_record,
)
from backend.app.modules.medical_document_intelligence.services.reviewed_record_repository import (
    SqliteReviewedClinicalRecordRepository, default_reviewed_record_path,
)
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyDocument, JourneyStage, JourneyStore, StageStatus,
)


PROTECTED = "No focal consolidation or pleural effusion."
IDENTIFIED = b"ORIGINAL_IDENTIFIED_PATIENT_MARKER_12345"


def _outputs(document_id: str, *, major: bool = False):
    digest = hashlib.sha256(PROTECTED.encode()).hexdigest()
    protect = {"protected_document": {"report_id": document_id, "protected_text": PROTECTED,
        "integrity_sha256": digest, "selected_policy_id": "synthetic", "selected_policy_version": "1"}}
    fact = {"fact_id": "fact-1", "display_label": "Pleural effusion", "assertion_state": "ABSENT_NEGATED",
            "group": "NEGATIVE", "anatomy": "pleura", "review_required": major,
            "review_reason": ["INTERNAL_SOURCE_CONFLICT"] if major else [],
            "evidence_anchors": [{"evidence_id": "e1", "start_offset": 26, "end_offset": 42,
                                  "quote": "pleural effusion"}]}
    if major:
        fact["group"] = "KEY"
    extract = {"report_id": document_id, "clinical_synthesis": {
        "clinical_synthesis": "No acute pleural finding.", "canonical_facts": [fact]}}
    standardize = {"report_id": document_id, "profile": "synthetic-v1",
        "standardized_study_context": {"original_exam_name": "ORIGINAL_IDENTIFIED_EXAM_MARKER",
            "normalized_modality": "X_RAY", "normalized_body_region": "CHEST",
            "normalized_laterality": "NOT_DETERMINED"},
        "standardized_facts": [{"source_fact_id": "fact-1", "standardization_status": "COMPLETE",
                                "standardized_measurements": []}], "unassigned_measurements": []}
    return protect, extract, standardize


def _prepared_store(tmp_path, *, major=False):
    repo = SqliteReviewedClinicalRecordRepository(tmp_path / "reviewed.sqlite3")
    store = JourneyStore(batch_root=tmp_path / "batches", reviewed_records=repo)
    run = store.create_run("single", run_id="f" * 32)
    document_id = "a" * 32
    item = JourneyDocument(document_id=document_id, original_filename="IDENTIFIED_FILENAME_MARKER.pdf",
                           order=0, source_type="pdf", source_artifact=IDENTIFIED)
    protect, extract, standardized = _outputs(document_id, major=major)
    for stage, result in ((JourneyStage.PROTECT, protect), (JourneyStage.EXTRACT, extract),
                          (JourneyStage.STANDARDIZE, standardized)):
        item.stage_results[stage] = result
        item.stage_status[stage] = StageStatus.NEEDS_REVIEW if major else StageStatus.COMPLETE
    run.documents.append(item)
    return store, run, item, repo


def test_save_list_reopen_evidence_and_no_original_payload(tmp_path):
    store, run, item, repo = _prepared_store(tmp_path)
    store.accept_clinical_review(run.run_id, item.document_id)
    record_id = item.reviewed_record_id
    assert item.review_status == "REVIEWED" and record_id and item.reviewed_at
    first = repo.get_current(record_id)
    assert first is not None
    assert repo.list()[0].to_json() == first.to_json()
    assert ReviewedClinicalRecord.from_json(first.to_json()).to_json() == first.to_json()
    assert first.evidence_context("fact-1", "e1")["exact_highlight"] is True
    assert first.evidence_context("fact-1", "e1")["anchor"]["quote"] == "pleural effusion"
    assert first.to_dict()["durably_reviewed"] is True
    repo.close()
    db_bytes = (tmp_path / "reviewed.sqlite3").read_bytes()
    assert IDENTIFIED not in db_bytes
    assert b"IDENTIFIED_FILENAME_MARKER" not in db_bytes
    assert b"ORIGINAL_IDENTIFIED_EXAM_MARKER" not in db_bytes
    reopened = SqliteReviewedClinicalRecordRepository(tmp_path / "reviewed.sqlite3")
    assert reopened.get_current(record_id).to_json() == first.to_json()
    assert reopened.list_versions(record_id)[0]["record_version"] == 1
    assert reopened.get(record_id, 1).evidence_context("fact-1", "e1")["exact_highlight"]
    reopened.close()


def test_new_process_reopens_review_without_journey_memory(tmp_path):
    create_script = ("import json,sys; from pathlib import Path; "
        "from backend.tests.test_reviewed_clinical_records import _prepared_store; "
        "store,run,item,repo=_prepared_store(Path(sys.argv[1])); "
        "store.accept_clinical_review(run.run_id,item.document_id); "
        "print(json.dumps({'reviewed_record_id':item.reviewed_record_id})); repo.close()")
    created = subprocess.run([sys.executable, "-B", "-c", create_script, str(tmp_path)],
                             cwd=os.getcwd(), text=True, capture_output=True, check=True)
    record_id = json.loads(created.stdout)["reviewed_record_id"]
    script = ("import json,sys; from backend.app.modules.medical_document_intelligence.services."
              "reviewed_record_repository import SqliteReviewedClinicalRecordRepository as R; "
              "r=R(sys.argv[1]); x=r.get_current(sys.argv[2]); "
              "print(json.dumps({'id':x.to_dict()['reviewed_record_id'],"
              "'facts':len(x.to_dict()['canonical_facts']),"
              "'accepted':x.to_dict()['review_decision']=='ACCEPTED',"
              "'evidence':x.evidence_context('fact-1','e1')['exact_highlight'],"
              "'version':r.list_versions(sys.argv[2])[0]['record_version']})); r.close()")
    process = subprocess.run([sys.executable, "-B", "-c", script, str(tmp_path / "reviewed.sqlite3"),
                              record_id], cwd=os.getcwd(), text=True, capture_output=True, check=True)
    result = json.loads(process.stdout)
    assert result == {"id": record_id, "facts": 1, "accepted": True, "evidence": True, "version": 1}


def test_versions_append_and_current_points_to_latest(tmp_path):
    store, run, item, repo = _prepared_store(tmp_path)
    store.accept_clinical_review(run.run_id, item.document_id)
    first = repo.get_current(item.reviewed_record_id)
    version_two = first.to_dict()
    version_two["record_version"] = 2
    version_two["reviewed_at"] = "2030-01-01T00:00:00Z"
    version_two["clinical_summary"] = "Corrected synthetic summary."
    second = ReviewedClinicalRecord.from_dict(version_two)
    repo.save(second)
    repo.close()
    reopened = SqliteReviewedClinicalRecordRepository(tmp_path / "reviewed.sqlite3")
    assert reopened.get(item.reviewed_record_id, 1).to_json() == first.to_json()
    assert reopened.get_current(item.reviewed_record_id).to_json() == second.to_json()
    assert [v["record_version"] for v in reopened.list_versions(item.reviewed_record_id)] == [1, 2]
    reopened.close()


def test_accept_retry_is_idempotent_and_major_acknowledgement_required(tmp_path):
    store, run, item, repo = _prepared_store(tmp_path, major=True)
    try:
        store.accept_clinical_review(run.run_id, item.document_id)
    except ValueError as exc:
        assert "acknowledgement" in str(exc)
    else:
        raise AssertionError("Major Review accepted without acknowledgement")
    assert item.review_status != "REVIEWED"
    store.accept_clinical_review(run.run_id, item.document_id, major_review_acknowledged=True)
    first_reviewed_at = item.reviewed_at
    store.accept_clinical_review(run.run_id, item.document_id, major_review_acknowledged=True)
    assert item.reviewed_at == first_reviewed_at
    assert len(repo.list_versions(item.reviewed_record_id)) == 1
    assert repo.get_current(item.reviewed_record_id).to_dict()["major_review_acknowledged"] is True


def test_failed_persistence_never_marks_reviewed_and_api_is_safe(monkeypatch, tmp_path):
    store, run, item, repo = _prepared_store(tmp_path)
    monkeypatch.setattr(api, "journey_store", store)
    original_save = repo.save
    def fail(_record):
        raise OSError("PRIVATE_SQL_PATH_AND_CONTENT")
    monkeypatch.setattr(repo, "save", fail)
    response = TestClient(app).post(
        f"/api/v1/understanding/journey-runs/{run.run_id}/documents/{item.document_id}/accept")
    assert response.status_code == 503
    assert "PRIVATE_SQL_PATH_AND_CONTENT" not in response.text
    assert item.review_status != "REVIEWED" and item.reviewed_record_id is None
    assert repo.list() == []
    monkeypatch.setattr(repo, "save", original_save)
    assert TestClient(app).post(
        f"/api/v1/understanding/journey-runs/{run.run_id}/documents/{item.document_id}/accept").status_code == 200
    assert item.review_status == "REVIEWED" and len(repo.list_versions(item.reviewed_record_id)) == 1


def test_read_apis_and_configured_location(monkeypatch, tmp_path):
    monkeypatch.setenv("MRJ_REVIEWED_RECORD_DB", str(tmp_path / "configured.sqlite3"))
    assert default_reviewed_record_path() == tmp_path / "configured.sqlite3"
    store, run, item, repo = _prepared_store(tmp_path)
    store.accept_clinical_review(run.run_id, item.document_id)
    monkeypatch.setattr(api, "journey_store", store)
    client = TestClient(app)
    prefix = "/api/v1/understanding/reviewed-records"
    record_id = item.reviewed_record_id
    assert client.get(prefix).json()["records"][0]["reviewed_record_id"] == record_id
    assert client.get(f"{prefix}/{record_id}").json()["record"]["durably_reviewed"] is True
    assert client.get(f"{prefix}/{record_id}?version=1").status_code == 200
    assert client.get(f"{prefix}/{record_id}/versions").json()["versions"][0]["record_version"] == 1
    assert client.get(f"/api/v1/understanding/journey-runs/{run.run_id}/documents/{item.document_id}/reviewed-record").status_code == 200


def test_default_storage_is_outside_repository_and_contract_rejects_original_fields(monkeypatch, tmp_path):
    monkeypatch.delenv("MRJ_REVIEWED_RECORD_DB", raising=False)
    repository_root = Path(__file__).resolve().parents[2]
    assert not default_reviewed_record_path().resolve().is_relative_to(repository_root)
    store, run, item, repo = _prepared_store(tmp_path)
    store.accept_clinical_review(run.run_id, item.document_id)
    record = repo.get_current(item.reviewed_record_id).to_dict()
    record["original_identified_text"] = IDENTIFIED.decode()
    try:
        ReviewedClinicalRecord.from_dict(record)
    except ValueError as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("Contract accepted original identified text")
    record.pop("original_identified_text")
    record["protected_source"]["original_filename"] = "IDENTIFIED_FILENAME_MARKER.pdf"
    try:
        ReviewedClinicalRecord.from_dict(record)
    except ValueError as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("Contract accepted original filename")


def test_real_synthesis_and_standardization_shapes_round_trip(tmp_path):
    from backend.tests.test_clinical_extraction_pilot import entity, synth
    from backend.tests.test_clinical_standardization import context, service

    protected = "pleural effusion"
    extracted = synth([protected], ["FINDINGS_DESCRIPTION"],
        [{"text": protected, "entities": {"1": entity("effusion", 1, 1)}}])
    standardized = service().standardize(extracted, context())
    digest = hashlib.sha256(protected.encode()).hexdigest()
    record = build_reviewed_record(
        run_id="f" * 32, document_id="report", reviewed_at="2030-01-01T00:00:00Z",
        protect={"protected_document": {"report_id": "report", "protected_text": protected,
                                        "integrity_sha256": digest}},
        extract=extracted, standardized=standardized)
    repo = SqliteReviewedClinicalRecordRepository(tmp_path / "real-shape.sqlite3")
    repo.save(record)
    repo.close()
    reopened = SqliteReviewedClinicalRecordRepository(tmp_path / "real-shape.sqlite3")
    recovered = reopened.get_current(record.to_dict()["reviewed_record_id"])
    assert recovered.to_json() == record.to_json()
    assert len(recovered.to_dict()["canonical_facts"]) == 1
    assert len(recovered.to_dict()["standardized_facts"]) == 1
    assert recovered.evidence_context(recovered.to_dict()["canonical_facts"][0]["fact_id"])["exact_highlight"]
    reopened.close()
