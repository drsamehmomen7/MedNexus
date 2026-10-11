"""Review decisions belong to a prepared Journey document, never to a queue row."""

import json
import hashlib

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.api import understanding as api
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyDocument,
    JourneyStage,
    JourneyStore,
    StageStatus,
)
from backend.app.modules.medical_document_intelligence.services.reviewed_record_repository import SqliteReviewedClinicalRecordRepository


def _ready_document(document_id: str, order: int) -> JourneyDocument:
    item = JourneyDocument(document_id=document_id, original_filename=f"Synthetic {order}.txt",
                           order=order, source_type="txt")
    item.stage_status[JourneyStage.PROTECT] = StageStatus.NEEDS_REVIEW
    item.stage_status[JourneyStage.EXTRACT] = StageStatus.NEEDS_REVIEW
    item.stage_status[JourneyStage.STANDARDIZE] = StageStatus.COMPLETE
    protected_text = "No focal consolidation."
    item.stage_results[JourneyStage.PROTECT] = {"protected_document": {
        "report_id": document_id, "protected_text": protected_text,
        "integrity_sha256": hashlib.sha256(protected_text.encode()).hexdigest()}}
    item.stage_results[JourneyStage.EXTRACT] = {"report_id": document_id,
                                                "clinical_synthesis": {"canonical_facts": []}}
    item.stage_results[JourneyStage.STANDARDIZE] = {"report_id": document_id}
    return item


def test_accept_requires_current_record_and_is_independent_per_report(monkeypatch, tmp_path):
    store = JourneyStore(batch_root=tmp_path / "batches",
                         reviewed_records=SqliteReviewedClinicalRecordRepository(tmp_path / "reviewed.sqlite3"))
    run = store.create_run("batch", display_name="Synthetic review test")
    first = _ready_document("a" * 32, 0)
    second = _ready_document("b" * 32, 1)
    second.stage_results.pop(JourneyStage.STANDARDIZE)
    second.stage_status[JourneyStage.STANDARDIZE] = StageStatus.NOT_STARTED
    run.documents.extend([first, second])
    monkeypatch.setattr(api, "journey_store", store)
    client = TestClient(app)

    path = f"/api/v1/understanding/journey-runs/{run.run_id}/documents"
    assert client.post(f"{path}/{second.document_id}/accept").status_code == 409
    accepted = client.post(f"{path}/{first.document_id}/accept")
    assert accepted.status_code == 200
    documents = accepted.json()["documents"]
    assert documents[0]["review_status"] == "REVIEWED"
    assert documents[0]["reviewed_at"]
    assert documents[1]["review_status"] == "PENDING"
    assert documents[1]["reviewed_at"] is None

    repeated = client.post(f"{path}/{first.document_id}/accept")
    assert repeated.status_code == 200
    assert repeated.json()["documents"][0]["reviewed_at"] == documents[0]["reviewed_at"]
    metadata = json.loads((tmp_path / "batches" / f"{run.run_id}.json").read_text(encoding="utf-8"))
    assert metadata["documents"][0]["review_status"] == "REVIEWED"
    assert metadata["documents"][1]["review_status"] == "PENDING"
    assert "clinical_synthesis" not in json.dumps(metadata)
    archived = JourneyStore(batch_root=tmp_path / "batches").run_payload(run.run_id)
    assert archived["archived"] is True
    assert archived["documents"][0]["review_status"] == "REVIEWED"


def test_accept_rejects_stale_standardization_and_unknown_report(monkeypatch, tmp_path):
    store = JourneyStore(batch_root=tmp_path / "batches",
                         reviewed_records=SqliteReviewedClinicalRecordRepository(tmp_path / "reviewed.sqlite3"))
    run = store.create_run("single")
    item = _ready_document("c" * 32, 0)
    item.stage_results[JourneyStage.STANDARDIZE]["report_id"] = "d" * 32
    run.documents.append(item)
    monkeypatch.setattr(api, "journey_store", store)
    client = TestClient(app)
    path = f"/api/v1/understanding/journey-runs/{run.run_id}/documents"
    assert client.post(f"{path}/{item.document_id}/accept").status_code == 409
    assert client.post(f"{path}/{'e' * 32}/accept").status_code == 404
    assert item.review_status == "PENDING"
