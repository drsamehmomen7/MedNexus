from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.api import (
    understanding as understanding_api,
)


client = TestClient(app)


def _verify_frontend_cards(single: dict, run: dict) -> dict:
    root = Path(__file__).resolve().parents[2]
    checked = subprocess.run(
        ["node", str(root / "backend/tests/understanding_report_card_contract.cjs")],
        input=json.dumps({"single": single, "run": run}),
        capture_output=True, text=True, encoding="utf-8", cwd=root, check=False,
    )
    assert checked.returncode == 0, checked.stderr
    return json.loads(checked.stdout)

CT_REPORT = """RADIOLOGY REPORT
EXAMINATION: CT chest
TECHNIQUE: Axial CT images were obtained.
FINDINGS: The lungs are clear.
IMPRESSION: No acute finding.
"""

MRI_REPORT = """RADIOLOGY REPORT
EXAMINATION: MRI brain
TECHNIQUE: Multiplanar T1 and T2 weighted images were obtained.
FINDINGS: No restricted diffusion.
IMPRESSION: No acute intracranial finding.
"""


def _create_batch() -> str:
    response = client.post(
        "/api/v1/understanding/journey-runs", json={"mode": "batch"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "batch"
    assert payload["storage"] == {
        "kind": "ephemeral_process_memory",
        "ttl_seconds": 1800,
        "durable": False,
    }
    return payload["run_id"]


def _add_report(
    run_id: str,
    order: int,
    filename: str,
    content: bytes,
    media_type: str = "text/plain",
):
    return client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/documents",
        data={"order": str(order)},
        files={"file": (filename, content, media_type)},
    )


def test_batch_two_valid_reports_use_the_single_authoritative_result_schema():
    single = client.post(
        "/api/v1/understanding/analyze-file",
        files={"file": ("single.txt", CT_REPORT.encode(), "text/plain")},
    ).json()
    run_id = _create_batch()
    first = _add_report(run_id, 0, "ct.txt", CT_REPORT.encode())
    second = _add_report(run_id, 1, "mri.txt", MRI_REPORT.encode())

    assert first.status_code == second.status_code == 200
    payload = second.json()
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["analyzed"] == 2
    assert [item["original_filename"] for item in payload["documents"]] == [
        "ct.txt",
        "mri.txt",
    ]
    results = [item["stage_results"]["UNDERSTAND"] for item in payload["documents"]]
    assert [result["document_subtype"] for result in results] == ["CT", "MRI"]
    assert set(results[0]) == set(single)
    assert set(results[0]["journey"]) == set(single["journey"]) | {"document_id"}


def test_batch_accepts_ten_reports_and_rejects_an_eleventh_cleanly():
    run_id = _create_batch()
    payload = None
    for index in range(10):
        content = f"{CT_REPORT}\nACCESSION LABEL: {index}".encode()
        response = _add_report(run_id, index, f"report-{index}.txt", content)
        assert response.status_code == 200
        payload = response.json()

    assert payload["summary"]["total"] == 10
    assert payload["summary"]["analyzed"] == 10
    overflow = _add_report(
        run_id, 10, "report-10.txt", f"{CT_REPORT}\nACCESSION LABEL: 10".encode()
    )
    assert overflow.status_code == 400
    assert "at most 10 reports" in overflow.json()["detail"]
    retained = client.get(f"/api/v1/understanding/journey-runs/{run_id}").json()
    assert retained["summary"]["total"] == 10


def test_batch_five_valid_reports_all_reach_terminal_state():
    run_id = _create_batch()
    payload = None
    for index in range(5):
        content = f"{CT_REPORT}\nCONTROLLED REPORT NUMBER: {index}".encode()
        response = _add_report(run_id, index, f"ct-{index}.txt", content)
        assert response.status_code == 200
        payload = response.json()

    assert payload["summary"]["total"] == 5
    assert payload["summary"]["analyzed"] == 5
    assert all(
        item["stage_status"]["UNDERSTAND"]["status"]
        in {"COMPLETE", "NEEDS_REVIEW", "FAILED"}
        for item in payload["documents"]
    )


def test_unsupported_report_fails_individually_while_valid_reports_complete():
    run_id = _create_batch()
    _add_report(run_id, 0, "first.txt", CT_REPORT.encode())
    unsupported = _add_report(run_id, 1, "notes.csv", b"not,a,report", "text/csv")
    final = _add_report(run_id, 2, "second.txt", MRI_REPORT.encode()).json()

    assert unsupported.status_code == 200
    assert [item["stage_status"]["UNDERSTAND"]["status"] for item in final["documents"]] == [
        "COMPLETE",
        "FAILED",
        "COMPLETE",
    ]
    assert final["documents"][1]["stage_status"]["PROTECT"]["status"] == "BLOCKED"
    assert "Unsupported document extension" in final["documents"][1]["error"]
    assert final["summary"]["failed"] == 1
    assert final["summary"]["analyzed"] == 3


def test_individual_extraction_failure_does_not_destroy_the_batch_and_can_retry():
    run_id = _create_batch()
    failed = _add_report(run_id, 0, "empty.txt", b"").json()
    failed_id = failed["documents"][0]["document_id"]
    completed = _add_report(run_id, 1, "valid.txt", CT_REPORT.encode()).json()
    assert completed["summary"]["failed"] == 1
    assert completed["documents"][1]["stage_status"]["UNDERSTAND"]["status"] == "COMPLETE"

    retried = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/{failed_id}/retry",
        files={"file": ("recovered.txt", MRI_REPORT.encode(), "text/plain")},
    )
    assert retried.status_code == 200
    payload = retried.json()
    assert payload["summary"]["failed"] == 0
    assert payload["summary"]["analyzed"] == 2
    assert payload["documents"][0]["document_id"] == failed_id
    assert payload["documents"][0]["stage_results"]["UNDERSTAND"]["document_subtype"] == "MRI"
    assert payload["documents"][0]["stage_status"]["PROTECT"]["status"] == "NOT_STARTED"


def test_batch_result_order_is_stable_even_when_documents_arrive_out_of_order():
    run_id = _create_batch()
    _add_report(run_id, 1, "second.txt", MRI_REPORT.encode())
    payload = _add_report(run_id, 0, "first.txt", CT_REPORT.encode()).json()
    assert [(item["order"], item["original_filename"]) for item in payload["documents"]] == [
        (0, "first.txt"),
        (1, "second.txt"),
    ]


def test_batch_summary_uses_existing_confidence_and_review_semantics():
    run_id = _create_batch()
    _add_report(run_id, 0, "recognized.txt", CT_REPORT.encode())
    _add_report(run_id, 1, "review.txt", b"General administrative healthcare memo.")
    payload = _add_report(run_id, 2, "failed.txt", b"").json()

    assert payload["summary"] == {
        "total": 3,
        "analyzed": 3,
        "recognized": 1,
        "high_confidence": 1,
        "needs_review": 1,
        "failed": 1,
    }
    review = payload["documents"][1]
    assert review["review_status"] == "NEEDS_REVIEW"
    assert review["stage_status"]["UNDERSTAND"]["status"] == "NEEDS_REVIEW"
    assert review["stage_status"]["PROTECT"]["status"] == "NOT_STARTED"
    assert review["stage_status"]["EXTRACT"]["status"] == "BLOCKED"
    assert review["stage_results"]["UNDERSTAND"]["document_context"][
        "processing_context"
    ]["protect_ready"] is True
    assert payload["handoff"]["protect"]["eligible_count"] == 2


def test_reviewable_unknown_and_other_reports_can_protect_without_unlocking_extract(
    monkeypatch,
):
    class ControlledPrivacyService:
        def process(self, text, policy):
            return SimpleNamespace(
                success=True,
                data=SimpleNamespace(deidentified_text=text),
                metadata={
                    "requires_review": False,
                    "candidate_counts": {
                        "total": 0,
                        "accepted": 0,
                        "rejected": 0,
                        "review_required": 0,
                        "pending": 0,
                    },
                    "intelligence_result": {"accepted": []},
                    "output_owner": "MedNexus",
                    "external_engine_role": "candidate_detector",
                    "privacy_decision_path": "unified",
                },
                engine_name="controlled",
                engine_version="1.0",
                processing_time=0.001,
            )

    monkeypatch.setattr(
        understanding_api,
        "privacy_service",
        ControlledPrivacyService(),
    )
    run_id = _create_batch()
    other = """RADIOLOGY REPORT
TECHNIQUE: CT and MRI images were obtained.
FINDINGS: Combined appearances are documented.
IMPRESSION: Multimodality assessment.
"""
    assert _add_report(run_id, 0, "other.txt", other.encode()).status_code == 200
    before = _add_report(
        run_id,
        1,
        "unknown.txt",
        b"General administrative healthcare memo.",
    ).json()

    assert [
        item["stage_status"]["UNDERSTAND"]["status"]
        for item in before["documents"]
    ] == ["NEEDS_REVIEW", "NEEDS_REVIEW"]
    assert [
        item["stage_status"]["PROTECT"]["status"]
        for item in before["documents"]
    ] == ["NOT_STARTED", "NOT_STARTED"]
    assert all(
        item["stage_status"]["EXTRACT"]["status"] == "BLOCKED"
        for item in before["documents"]
    )
    assert before["handoff"]["protect"]["eligible_count"] == 2

    protected = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert protected.status_code == 200
    documents = protected.json()["documents"]
    assert [
        item["stage_status"]["UNDERSTAND"]["status"] for item in documents
    ] == ["NEEDS_REVIEW", "NEEDS_REVIEW"]
    assert [
        item["stage_status"]["PROTECT"]["status"] for item in documents
    ] == ["COMPLETE", "COMPLETE"]
    assert all(
        item["stage_status"]["EXTRACT"]["status"] == "BLOCKED"
        for item in documents
    )


def test_duplicate_content_is_rejected_before_a_second_analysis_result_is_created():
    run_id = _create_batch()
    _add_report(run_id, 0, "first.txt", CT_REPORT.encode())
    payload = _add_report(run_id, 1, "copy.txt", CT_REPORT.encode()).json()
    assert payload["documents"][1]["stage_status"]["UNDERSTAND"]["status"] == "FAILED"
    assert payload["documents"][1]["stage_results"] == {}
    assert payload["documents"][1]["error"] == "Duplicate report rejected before analysis."


def test_batch_handoff_retains_every_report_and_exposes_all_eligible_documents():
    run_id = _create_batch()
    _add_report(run_id, 0, "ct.txt", CT_REPORT.encode())
    payload = _add_report(run_id, 1, "mri.txt", MRI_REPORT.encode()).json()
    assert payload["handoff"]["protect"]["available"] is True
    assert payload["handoff"]["protect"]["document_count"] == 2
    assert payload["handoff"]["protect"]["eligible_count"] == 2
    assert payload["handoff"]["protect"]["eligible_document_ids"] == [
        item["document_id"] for item in payload["documents"]
    ]
    assert all(
        item["stage_results"]["UNDERSTAND"]["journey"]["continue_to_protect"] is None
        for item in payload["documents"]
    )


def test_journey_protect_preserves_engine_zero_phi_and_review_semantics(monkeypatch):
    class ControlledPrivacyService:
        def process(self, text, policy):
            review_required = "CONTROLLED REVIEW" in text
            return SimpleNamespace(
                success=True,
                data=SimpleNamespace(deidentified_text=text),
                metadata={
                    "requires_review": review_required,
                    "candidate_counts": {
                        "total": 1 if review_required else 0,
                        "accepted": 0,
                        "rejected": 0,
                        "review_required": 1 if review_required else 0,
                        "pending": 0,
                    },
                    "intelligence_result": {"accepted": []},
                    "output_owner": "MedNexus",
                    "external_engine_role": "candidate_detector",
                    "privacy_decision_path": "unified",
                },
                engine_name="controlled",
                engine_version="1.0",
                processing_time=0.001,
            )

    monkeypatch.setattr(
        understanding_api,
        "privacy_service",
        ControlledPrivacyService(),
    )
    run_id = _create_batch()
    assert _add_report(
        run_id, 0, "zero-phi.txt", f"{CT_REPORT}\nZERO-PHI CASE".encode()
    ).status_code == 200
    assert _add_report(
        run_id, 1, "review.txt", f"{CT_REPORT}\nCONTROLLED REVIEW".encode()
    ).status_code == 200

    response = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [
        item["stage_status"]["PROTECT"]["status"]
        for item in payload["documents"]
    ] == ["COMPLETE", "NEEDS_REVIEW"]
    assert [
        item["stage_results"]["PROTECT"]["protection_result"]["review_required"]
        for item in payload["documents"]
    ] == [False, True]
    assert payload["documents"][1]["stage_results"]["PROTECT"][
        "protection_result"
    ]["review_signal_summary"] == [
        {
            "category": "unclassified_identity_like",
            "human_label": "Unclassified identity-like signal",
            "count": 1,
        }
    ]
    assert payload["protection_summary"]["complete"] == 1
    assert payload["protection_summary"]["needs_review"] == 1


def test_single_journey_continues_to_protect_in_the_same_run_with_real_phi():
    source = f"""Patient Name: Nadia Hassan
MRN: 99887766
Phone: +1 202 555 0199
{CT_REPORT}"""
    understood = client.post(
        "/api/v1/understanding/analyze-text", json={"text": source}
    )
    assert understood.status_code == 200
    run_id = understood.json()["journey"]["run_id"]
    retained = client.get(f"/api/v1/understanding/journey-runs/{run_id}").json()
    document_id = retained["documents"][0]["document_id"]

    compare_before_protect = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/compare-source"
    )
    assert compare_before_protect.status_code == 409

    protected = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert protected.status_code == 200
    payload = protected.json()
    assert payload["run_id"] == run_id
    assert payload["mode"] == "single"
    assert len(payload["documents"]) == 1
    report = payload["documents"][0]
    assert report["stage_status"]["PROTECT"]["status"] in {
        "COMPLETE",
        "NEEDS_REVIEW",
    }
    result = report["stage_results"]["PROTECT"]
    protected_text = result["protected_document"]["protected_text"]
    assert protected_text != source
    assert "Nadia Hassan" not in protected_text
    assert "99887766" not in protected_text
    assert "+1 202 555 0199" not in protected_text
    assert "The lungs are clear." in protected_text
    assert "No acute finding." in protected_text
    assert result["protection_result"]["policy_id"] == "mednexus_clinical"
    assert result["protection_result"]["accepted_decisions"]
    assert result["patient_analytic_context"]["populated_fields"] == []
    assert all(
        field["state"] == "NOT_AVAILABLE"
        for field in result["patient_analytic_context"]["fields"].values()
    )
    serialized = json.dumps(result)
    assert "original_text" not in serialized
    assert "detection_text" not in serialized
    assert "Nadia Hassan" not in serialized

    compared = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/compare-source"
    )
    assert compared.status_code == 200
    assert compared.json() == {"source_text": source}
    assert compared.headers["cache-control"] == "no-store, private"
    assert compared.headers["pragma"] == "no-cache"
    assert compared.headers["x-content-type-options"] == "nosniff"


def test_batch_protects_five_reports_and_retains_independent_results():
    run_id = _create_batch()
    for index in range(5):
        source = (
            f"Patient Name: Controlled Person {index}\n"
            f"MRN: 70000{index}\n{CT_REPORT}\nCONTROLLED REPORT: {index}"
        )
        response = _add_report(
            run_id,
            index,
            f"controlled-{index}.txt",
            source.encode(),
        )
        assert response.status_code == 200

    protected = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_research"},
    )
    assert protected.status_code == 200
    payload = protected.json()
    assert payload["run_id"] == run_id
    assert payload["protection_summary"] == {
        "eligible": 5,
        "submitted": 5,
        "terminal": 5,
        "results_stored": 5,
        "complete": 5,
        "needs_review": 0,
        "failed": 0,
        "blocked": 0,
    }
    report_ids = {item["document_id"] for item in payload["documents"]}
    result_report_ids = {
        item["stage_results"]["PROTECT"]["protected_document"]["report_id"]
        for item in payload["documents"]
    }
    assert result_report_ids == report_ids
    assert len(
        {
            item["stage_results"]["PROTECT"]["protected_document"][
                "integrity_sha256"
            ]
            for item in payload["documents"]
        }
    ) == 5


def test_one_protect_failure_does_not_stop_remaining_reports(monkeypatch):
    class ControlledPrivacyService:
        def process(self, text, policy):
            if "CONTROLLED PROTECT FAILURE" in text:
                raise RuntimeError("controlled failure")
            review_required = "CONTROLLED REVIEW" in text
            return SimpleNamespace(
                success=True,
                data=SimpleNamespace(deidentified_text=text.replace("Patient Name", "[PATIENT_NAME]")),
                metadata={
                    "requires_review": review_required,
                    "candidate_counts": {
                        "total": 1 if review_required else 0,
                        "review_required": 1 if review_required else 0,
                        "pending": 0,
                    },
                    "intelligence_result": {"accepted": []},
                    "output_owner": "MedNexus",
                    "external_engine_role": "candidate_detector",
                    "privacy_decision_path": "unified",
                },
                engine_name="controlled",
                engine_version="1.0",
                processing_time=0.001,
            )

    monkeypatch.setattr(
        understanding_api,
        "privacy_service",
        ControlledPrivacyService(),
    )
    run_id = _create_batch()
    reports = (
        f"Patient Name: First\n{CT_REPORT}\nREPORT: 1",
        f"Patient Name: Second\n{CT_REPORT}\nCONTROLLED REVIEW",
        f"Patient Name: Third\n{CT_REPORT}\nREPORT: 3",
        f"Patient Name: Fourth\n{CT_REPORT}\nCONTROLLED PROTECT FAILURE",
        f"Patient Name: Fifth\n{CT_REPORT}\nREPORT: 5",
    )
    for index, source in enumerate(reports):
        assert _add_report(
            run_id, index, f"isolation-{index}.txt", source.encode()
        ).status_code == 200

    response = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [
        item["stage_status"]["PROTECT"]["status"]
        for item in payload["documents"]
    ] == ["COMPLETE", "NEEDS_REVIEW", "COMPLETE", "FAILED", "COMPLETE"]
    assert ["PROTECT" in item["stage_results"] for item in payload["documents"]] == [
        True,
        True,
        True,
        False,
        True,
    ]
    assert payload["protection_summary"]["submitted"] == 5
    assert payload["protection_summary"]["terminal"] == 5
    assert payload["protection_summary"]["results_stored"] == 4
    assert payload["protection_summary"]["complete"] == 3
    assert payload["protection_summary"]["needs_review"] == 1
    assert payload["protection_summary"]["failed"] == 1
    stored_report_ids = {
        item["stage_results"]["PROTECT"]["protected_document"]["report_id"]
        for item in payload["documents"]
        if "PROTECT" in item["stage_results"]
    }
    assert stored_report_ids == {
        item["document_id"]
        for item in payload["documents"]
        if item["stage_status"]["PROTECT"]["status"] != "FAILED"
    }


def test_understanding_workspace_exposes_two_modes_without_browser_phi_persistence():
    page = client.get("/understanding").text
    script = client.get("/understanding.js").text
    assert "Single Report" in page
    assert "Batch Reports" in page
    assert "Analyze up to 10 clinical reports together" in page
    assert "Drop up to 10 reports here" in page
    assert "Choose Report" in page
    assert "No file chosen" not in page
    assert 'id="fileTab" type="button" role="tab" aria-selected="true"' in page
    assert "Continue to PROTECT" in page
    assert "Previous Report" in page and "Next Report" in page
    assert "MAX_BATCH_REPORTS = 10" in script
    assert "/api/v1/understanding/journey-runs" in script
    assert "stage_results?.UNDERSTAND" in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script
    assert "cache: 'no-store'" in script
    assert 'id="protectedViewBtn"' in page
    assert 'id="protectedPdfViewer"' in page
    assert 'id="protectedPdfDownloadBtn"' in page
    assert 'id="compareViewBtn"' in page
    assert 'id="textViewBtn"' in page
    assert 'id="comparePanel" hidden' in page
    assert 'id="originalComparePdf"' in page
    assert 'id="protectedComparePdf"' in page
    assert 'id="originalCompareText"' in page


def test_frontend_has_no_document_global_shadowing_and_exposes_mode_switching():
    root = Path(__file__).resolve().parents[2]
    script = (root / "frontend" / "understanding.js").read_text(encoding="utf-8")
    page = (root / "frontend" / "understanding.html").read_text(encoding="utf-8")

    shadowing = re.compile(
        r"(?:"
        r"(?:const|let|var)\s+(?:document|window|event|location|history)\b|"
        r"function\s+\w+\([^)]*\b(?:document|window|event|location|history)\b|"
        r"(?:forEach|map|find|findIndex|filter|reduce)\(\s*"
        r"(?:document|window|event|location|history)\b"
        r")"
    )
    assert shadowing.search(script) is None
    assert "setWorkflowMode('single')" in script
    assert "setWorkflowMode('batch')" in script
    assert 'id="singleWorkspace"' in page and 'id="batchWorkspace"' in page


def test_frontend_sequential_processor_survives_first_result_rendering_failure():
    root = Path(__file__).resolve().parents[2]
    runtime = root / "frontend" / "understanding.js"
    program = f"""
const {{ processSequentialBatch }} = require({json.dumps(str(runtime))});
(async () => {{
  const entries = Array.from({{ length: 5 }}, (_, index) => ({{ index, status: 'WAITING' }}));
  const attempted = [];
  await processSequentialBatch(
    entries,
    async (entry, index) => {{
      attempted.push(index);
      if (index === 2) throw new Error('isolated report failure');
      entry.status = 'COMPLETE';
    }},
    (_entry, index) => {{
      if (index === 0) throw new Error('detail renderer failure');
    }},
  );
  if (attempted.length !== 5) throw new Error(`attempted ${{attempted.length}} reports`);
  if (entries.some(entry => !['COMPLETE', 'FAILED'].includes(entry.status))) {{
    throw new Error('non-terminal entry remains');
  }}
}})().catch(error => {{ console.error(error.message); process.exit(1); }});
"""
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_frontend_retains_five_independent_results_and_builds_five_report_rows():
    root = Path(__file__).resolve().parents[2]
    runtime = root / "frontend" / "understanding.js"
    program = f"""
const {{
  activeWorkflowResult,
  adjacentRunDocumentId,
  buildBatchReportRows,
  createBatchDataTrace,
  getRunDocumentResult,
}} = require({json.dumps(str(runtime))});

const documents = Array.from({{ length: 5 }}, (_, index) => ({{
  document_id: `report-${{index + 1}}`,
  order: index,
  original_filename: `report-${{index + 1}}.pdf`,
  current_stage: 'UNDERSTAND',
  stage_status: {{ UNDERSTAND: {{ status: 'COMPLETE' }} }},
  stage_results: {{
    UNDERSTAND: {{
      marker: `result-${{index + 1}}`,
      document_type: 'RADIOLOGY_REPORT',
      document_subtype: 'CT',
      confidence: 1,
      confidence_band: 'HIGH',
      document_context: {{ identity: {{ domain: 'RADIOLOGY', subdomain_or_family: 'CT' }} }},
    }},
  }},
}}));
const run = {{ documents }};
const rows = buildBatchReportRows(run);
const trace = createBatchDataTrace({{ selectedCount: 5, submittedCount: 5, run }});

if (rows.length !== 5 || new Set(rows.map(row => row.documentId)).size !== 5) {{
  throw new Error('five unique report rows were not built');
}}
for (let index = 0; index < 5; index += 1) {{
  const result = getRunDocumentResult(run, `report-${{index + 1}}`);
  if (result?.marker !== `result-${{index + 1}}`) throw new Error('report result ownership was lost');
}}
if (Object.values(trace).some(value => value !== 5)) throw new Error(JSON.stringify(trace));
const single = {{ marker: 'single-result' }};
if (activeWorkflowResult('single', single, run, 'report-5') !== single) throw new Error('single state was replaced');
if (activeWorkflowResult('batch', single, run, 'report-5')?.marker !== 'result-5') throw new Error('batch state was replaced');
let current = 'report-1';
for (let index = 2; index <= 5; index += 1) {{
  current = adjacentRunDocumentId(run, current, 1);
  if (current !== `report-${{index}}`) throw new Error('next navigation did not traverse the batch');
}}
for (let index = 4; index >= 1; index -= 1) {{
  current = adjacentRunDocumentId(run, current, -1);
  if (current !== `report-${{index}}`) throw new Error('previous navigation did not traverse the batch');
}}
"""
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_frontend_protect_contract_retains_results_and_reports_real_stage_counts():
    root = Path(__file__).resolve().parents[2]
    runtime = root / "frontend" / "understanding.js"
    page = (root / "frontend" / "understanding.html").read_text(encoding="utf-8")
    script = runtime.read_text(encoding="utf-8")
    program = f"""
const {{
  buildBatchReportRows,
  buildCompareLines,
  buildNextStagePresentation,
  buildProtectionViewModel,
  createProtectionDataTrace,
  getRunDocumentStageResult,
  stageDisplay,
}} = require({json.dumps(str(runtime))});

const documents = Array.from({{ length: 5 }}, (_, index) => ({{
  document_id: `protected-${{index + 1}}`,
  order: index,
  original_filename: `protected-${{index + 1}}.pdf`,
  stage_status: {{
    UNDERSTAND: {{ status: 'COMPLETE' }},
    PROTECT: {{ status: index === 2 ? 'NEEDS_REVIEW' : 'COMPLETE' }},
  }},
  stage_results: {{
    UNDERSTAND: {{ marker: `understand-${{index + 1}}` }},
    PROTECT: {{
      protected_document: {{
        report_id: `protected-${{index + 1}}`,
        protected_text: `Protected report ${{index + 1}}`,
      }},
      patient_analytic_context: {{ fields: {{}}, populated_fields: [] }},
      protection_result: {{
        status: index === 2 ? 'NEEDS_REVIEW' : 'COMPLETE',
        policy_display_name: 'Clinical Workflow',
        protected_entity_category_summary: {{ Names: index + 1 }},
        review_required: index === 2,
        warnings: index === 2 ? ['Review required.'] : [],
      }},
      protection_provenance: {{
        output_owner: 'MedNexus',
        external_engine_role: 'candidate_detector',
        privacy_decision_path: 'unified',
      }},
    }},
  }},
}}));
const run = {{
  documents,
  protection_summary: {{ eligible: 5 }},
}};
const rows = buildBatchReportRows(run, 'PROTECT');
const trace = createProtectionDataTrace({{ selectedCount: 5, submittedCount: 5, run }});
if (rows.length !== 5 || new Set(rows.map(row => row.documentId)).size !== 5) {{
  throw new Error('PROTECT navigator did not retain five independent rows');
}}
for (let index = 0; index < 5; index += 1) {{
  const result = getRunDocumentStageResult(run, `protected-${{index + 1}}`, 'PROTECT');
  const view = buildProtectionViewModel(result);
  if (view.protectedText !== `Protected report ${{index + 1}}`) {{
    throw new Error('selected report protection result was overwritten');
  }}
  if ('provenance' in view) throw new Error('technical engine provenance entered the normal UI model');
}}
const reviewView = buildProtectionViewModel({{
  protected_document: {{ protected_text: 'Protected review output' }},
  patient_analytic_context: {{ fields: {{}}, populated_fields: [] }},
  protection_result: {{
    status: 'NEEDS_REVIEW',
    protected_entity_category_summary: {{}},
    review_signal_summary: [
      {{category:'ambiguous_date_time', human_label:'Ambiguous date/time signal', count:2}},
      {{category:'possible_person_name', human_label:'Possible person-name signal', count:1}},
    ],
    review_required: true,
  }},
  protection_provenance: {{
    candidate_counts: {{ total: 3, review_required: 3, pending: 0 }},
  }},
}});
if (reviewView.zeroPhi || reviewView.unresolvedCount !== 3) {{
  throw new Error('unresolved candidates were misrepresented as zero PHI');
}}
if (reviewView.summaryRows[0][1] !== 'None applied' || reviewView.reviewMessage !== 'Ambiguous date/time signal: 2 · Possible person-name signal: 1') {{
  throw new Error('review state is not explained in human language');
}}
if (reviewView.reviewSignals.some(item => 'text' in item || 'source' in item || 'confidence' in item)) {{
  throw new Error('technical or PHI-bearing review data entered the normal UI model');
}}
const zeroPhiView = buildProtectionViewModel({{
  protected_document: {{ protected_text: 'Already de-identified report' }},
  patient_analytic_context: {{ fields: {{}}, populated_fields: [] }},
  protection_result: {{
    status: 'COMPLETE',
    protected_entity_category_summary: {{}},
    review_required: false,
  }},
  protection_provenance: {{
    candidate_counts: {{ total: 0, accepted: 0, rejected: 0, review_required: 0, pending: 0 }},
  }},
}});
if (!zeroPhiView.zeroPhi || zeroPhiView.summaryRows[0][1] !== 'No PHI detected') {{
  throw new Error('true zero-PHI result is not presented clearly');
}}
const transformedView = buildProtectionViewModel({{
  protected_document: {{ protected_text: 'Protected result' }},
  patient_analytic_context: {{ fields: {{}}, populated_fields: [] }},
  protection_result: {{
    status: 'COMPLETE',
    protected_entity_category_summary: {{ Identifiers: 2, Names: 1 }},
    review_required: false,
  }},
  protection_provenance: {{ candidate_counts: {{ total: 3, accepted: 3 }} }},
}});
if (!transformedView.summaryRows.some(row => row[0] === 'Patient identifiers' && row[1] === '2 protected')) {{
  throw new Error('protection categories are not human-readable');
}}
const compareLines = buildCompareLines('Patient: Sarah Miller\\nFinding: normal', 'Patient: [PATIENT]\\nFinding: normal');
if (!compareLines[0].changed || compareLines[1].changed) {{
  throw new Error('simple compare highlighting does not isolate changed lines');
}}
const nextStage = buildNextStagePresentation({{
  mode: 'batch',
  documents,
  protection_summary: {{ complete: 3, needs_review: 1, failed: 1, blocked: 0 }},
}}, transformedView);
if (!nextStage.message.includes('3 reports are ready') || !nextStage.message.includes('1 requires review') || !nextStage.buttonLabel.includes('3 Eligible Reports')) {{
  throw new Error('mixed batch continuation does not preserve unaffected reports');
}}
if (Object.values(trace).some(value => value !== 5)) throw new Error(JSON.stringify(trace));
if (stageDisplay(run, 'PROTECT').label !== '5 / 5') throw new Error('terminal aggregate is wrong');
documents[4].stage_status.PROTECT.status = 'PROCESSING';
if (stageDisplay(run, 'PROTECT').label !== '4 / 5') throw new Error('in-progress aggregate is wrong');
"""
    completed = subprocess.run(
        ["node", "-e", program],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert 'id="protectionCard"' in page
    assert 'id="protectedText"' in page
    assert 'id="protectedPdfPanel" hidden' in page
    assert 'id="protectedPdfViewer"' in page
    assert 'id="protectedPdfDownloadBtn"' in page
    assert 'id="protectedViewBtn" type="button" aria-pressed="true"' in page
    assert 'id="textViewBtn" type="button" aria-pressed="false"' in page
    assert 'id="comparePanel" hidden' in page
    assert 'id="originalCompareText"' in page
    assert 'id="protectionReview"' in page
    assert 'id="reviewProtectionBtn"' in page
    assert 'id="nextStageSummary"' in page
    assert 'id="continueExtractBtn"' in page
    assert 'id="continueExtractBtn" type="button" disabled' in page
    assert "MRJ-owned protected output" not in page
    assert "External engines" not in page
    assert "PROTECT unavailable" not in script
    assert "MedNexus Clinical" not in page
    assert "/protected-artifact" in script
    assert "/compare-artifact" in script
    assert "globalThis.URL?.revokeObjectURL" in script
    assert page.index('id="protectedDocumentSection"') < page.index(
        'id="protectedEntitiesTitle"'
    ) < page.index('id="protectionReview"') < page.index('id="analyticContextTitle"')
    for policy_id in (
        "mednexus_clinical",
        "mednexus_research",
        "mednexus_analytics_public_health",
        "mednexus_strict_privacy",
    ):
        assert page.count(f'value="{policy_id}"') == 2


def test_shared_report_card_renders_actual_api_results_and_navigates_all_five():
    single = client.post(
        "/api/v1/understanding/analyze-file",
        files={"file": ("single.txt", CT_REPORT.encode(), "text/plain")},
    ).json()
    run_id = _create_batch()
    for index in range(5):
        report = CT_REPORT if index % 2 == 0 else MRI_REPORT
        response = _add_report(
            run_id, index, f"report-{index}.txt", f"{report}\nRecord: {index}".encode()
        )
        assert response.status_code == 200
    rendered = _verify_frontend_cards(single, response.json())
    assert rendered["navigatorCards"] == 5
    assert [card["modality"] for card in rendered["selectedCardsVerified"]] == [
        "CT", "MRI", "CT", "MRI", "CT"
    ]
    assert rendered["runPreserved"] is True


def test_shared_card_has_bounded_metadata_and_safe_review_failure_states():
    root = Path(__file__).resolve().parents[2]
    program = """
const assert = require('node:assert/strict');
const {buildReportViewModel} = require('./frontend/understanding.js');
const payload = {
  document_context: {
    identity: {domain:'RADIOLOGY', document_type:'RADIOLOGY_REPORT', subdomain_or_family:'CT', language:'ENGLISH', confidence:0.98, confidence_band:'HIGH'},
    light_context: {domain_type:'RADIOLOGY', family_context:{subdomain:'CT', study_family:'CTA', body_region:'ABDOMEN', contrast:'WITH_CONTRAST', acquisition_summary:['ANGIOGRAPHIC']}},
    processing_context: {document_review_required:false, protect_ready:true},
  },
  journey:{continue_to_protect:'/privacy?journey=example'},
};
const model = buildReportViewModel(payload);
assert.deepEqual(model.metadata, [['Body Region','Abdomen'], ['Contrast','With contrast'], ['Language','English'], ['Study Family','CTA']]);
assert.equal(model.confidence, '98%');
assert.equal(model.state, 'COMPLETE');
assert.equal(model.metadata.length + 3, 7);
payload.document_context.light_context.family_context.study_family = 'CT';
assert.equal(buildReportViewModel(payload).metadata.at(-1)[0], 'Acquisition Context');
payload.document_context.light_context.family_context.subdomain = 'MRI';
assert.deepEqual(buildReportViewModel(payload).metadata, [['Language','English']]);
payload.document_context.identity.subdomain_or_family = 'OTHER';
assert.equal(buildReportViewModel(payload).state, 'NEEDS_REVIEW');
assert.equal(buildReportViewModel(payload).handoff, '/privacy?journey=example');
assert.match(buildReportViewModel(payload).readiness, /ready for Privacy Protection/);
payload.document_context.identity.domain = 'UNKNOWN';
assert.equal(buildReportViewModel(payload).modality, 'Report needs review');
assert.equal(buildReportViewModel(null).state, 'FAILED');
assert.deepEqual(buildReportViewModel(null).metadata, []);
"""
    result = subprocess.run(["node", "-e", program], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_shared_renderer_supports_ten_compact_cards_including_review_and_failure():
    result = {
        "document_context": {
            "identity": {"domain": "RADIOLOGY", "document_type": "RADIOLOGY_REPORT", "subdomain_or_family": "CT", "language": "ENGLISH", "confidence": 0.95, "confidence_band": "HIGH"},
            "processing_context": {"document_review_required": False, "protect_ready": True},
        },
        "journey": {"continue_to_protect": "/privacy?journey=contract"},
    }
    documents = []
    for index in range(10):
        payload = json.loads(json.dumps(result))
        state = "COMPLETE"
        if index == 7:
            payload["document_context"]["identity"].update(domain="UNKNOWN", document_type="UNKNOWN", subdomain_or_family=None)
            payload["document_context"]["processing_context"]["document_review_required"] = True
            state = "NEEDS_REVIEW"
        if index == 9:
            state = "FAILED"
        documents.append({
            "document_id": f"contract-{index}", "order": index,
            "original_filename": f"contract-{index}.txt",
            "stage_status": {"UNDERSTAND": {"status": state}},
            "stage_results": {"UNDERSTAND": payload} if state != "FAILED" else {},
            "error": "The report could not be read." if state == "FAILED" else None,
        })
    run = {"mode": "batch", "documents": documents, "summary": {"total": 10, "analyzed": 10, "high_confidence": 8, "needs_review": 1, "failed": 1}, "handoff": {"protect": {"available": False}}}
    rendered = _verify_frontend_cards(result, run)
    assert rendered["navigatorCards"] == 10
    assert rendered["selectedCardsVerified"][7]["modality"] == "Report needs review"
    assert rendered["selectedCardsVerified"][9]["status"] == "! Failed"
