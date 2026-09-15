from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from fastapi.testclient import TestClient

from backend.app.main import app


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
    assert review["stage_status"]["PROTECT"]["status"] == "BLOCKED"


def test_duplicate_content_is_rejected_before_a_second_analysis_result_is_created():
    run_id = _create_batch()
    _add_report(run_id, 0, "first.txt", CT_REPORT.encode())
    payload = _add_report(run_id, 1, "copy.txt", CT_REPORT.encode()).json()
    assert payload["documents"][1]["stage_status"]["UNDERSTAND"]["status"] == "FAILED"
    assert payload["documents"][1]["stage_results"] == {}
    assert payload["documents"][1]["error"] == "Duplicate report rejected before analysis."


def test_batch_handoff_never_silently_drops_documents():
    run_id = _create_batch()
    _add_report(run_id, 0, "ct.txt", CT_REPORT.encode())
    payload = _add_report(run_id, 1, "mri.txt", MRI_REPORT.encode()).json()
    assert payload["handoff"]["protect"]["available"] is False
    assert payload["handoff"]["protect"]["document_count"] == 2
    assert "all reports remain retained" in payload["handoff"]["protect"]["reason"]
    assert all(
        item["stage_results"]["UNDERSTAND"]["journey"]["continue_to_protect"] is None
        for item in payload["documents"]
    )


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
    assert "Continue Batch to Privacy Protection" in page
    assert "Previous Report" in page and "Next Report" in page
    assert "MAX_BATCH_REPORTS = 10" in script
    assert "/api/v1/understanding/journey-runs" in script
    assert "stage_results?.UNDERSTAND" in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


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
assert.equal(buildReportViewModel(payload).handoff, null);
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
