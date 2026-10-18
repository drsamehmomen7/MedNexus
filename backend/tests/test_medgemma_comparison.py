"""Evaluation-only comparisons use synthetic text and never import a model."""
import hashlib
import json
from pathlib import Path
from time import sleep

from backend.app.modules.medical_document_intelligence.services.medgemma_adapter import MedGemmaTextAdapter
from backend.app.modules.medical_document_intelligence.services.medgemma_comparison import (
    ComparisonEvaluationService, compare, project_markdown,
)
from backend.app.modules.medical_document_intelligence.services.medgemma_generation_guard import (
    LIMIT_CODE, MAX_NEW_TOKENS, repeated_text_block, repeated_token_block,
)


def fact(label, assertion="PRESENT", group="KEY"):
    return {"display_label": label, "assertion_state": assertion, "group": group}


def test_markdown_projection_preserves_every_bullet_and_unmapped_text():
    raw = "**Clinically Important Findings:**\n*   **Mass:** Right thigh mass.\n\n**Note:**\nUnmapped prose."
    assert project_markdown(raw) == [
        {"role": "FINDING", "text": "**Mass:** Right thigh mass."},
        {"role": "UNRESOLVED", "text": "**Note:**"},
        {"role": "UNRESOLVED", "text": "Unmapped prose."},
    ]


def test_all_comparison_categories_and_no_mention_is_not_conflict():
    native = [fact("Left pleural effusion"), fact("No pneumothorax", "ABSENT_NEGATED", "NEGATIVE"),
              fact("No consolidation", "ABSENT_NEGATED", "NEGATIVE"),
              fact("Right thigh mass"), fact("Aortic calcification")]
    projected = [
        {"role": "FINDING", "text": "Left pleural effusion"},
        {"role": "FINDING", "text": "Pneumothorax is present"},
        {"role": "RECOMMENDATION", "text": "Repeat ultrasound in six months"},
        {"role": "UNRESOLVED", "text": "Ambiguous clinical wording"},
    ]
    result = compare(native, projected)
    assert result["counts"] == {"AGREEMENT": 1, "MRJ_ONLY": 3, "MEDGEMMA_ONLY": 1,
                                "CONFLICT": 1, "UNRESOLVED": 1}
    assert all(row["mrj"] != "No consolidation" for row in result["groups"]["CONFLICT"])


def test_repeated_model_mention_is_not_model_only_and_refusal_is_unresolved():
    native = [fact("No deep vein thrombosis", "ABSENT_NEGATED", "NEGATIVE")]
    repeated = [{"role": "PERTINENT_NEGATIVE", "text": "No deep vein thrombosis"},
                {"role": "FINDING", "text": "No evidence of DVT"},
                {"role": "PERTINENT_NEGATIVE", "text": "The mass is superficial, not deep"}]
    result = compare(native, repeated)
    assert result["counts"]["MEDGEMMA_ONLY"] == 1
    assert result["counts"]["AGREEMENT"] == 2
    refusal = compare(native, [{"role": "UNRESOLVED", "text": "Unable to extract this report."}])
    assert refusal["counts"]["MRJ_ONLY"] == 0
    assert refusal["counts"]["UNRESOLVED"] == 2


def document(text, report_id="b" * 32):
    return {"review_status": "NEEDS_REVIEW", "stage_status": {
        "PROTECT": {"status": "NEEDS_REVIEW"}, "EXTRACT": {"status": "NEEDS_REVIEW"},
        "STANDARDIZE": {"status": "COMPLETE"}}, "stage_results": {
        "PROTECT": {"protected_document": {"protected_text": text, "report_id": report_id,
                                           "integrity_sha256": hashlib.sha256(text.encode()).hexdigest()}},
        "EXTRACT": {"clinical_synthesis": {"canonical_facts": [fact("Left pleural effusion")]}},
        "STANDARDIZE": {}}}


def test_independent_persistence_protected_input_and_failure(tmp_path):
    received = []
    adapter = MedGemmaTextAdapter(lambda text: (received.append(text),
        {"status": "AVAILABLE", "raw_response": "**Clinically Important Findings:**\n* Left pleural effusion",
         "output_tokens": 12})[1])
    service = ComparisonEvaluationService(tmp_path, adapter)
    identified = "Patient: Identified Name. "
    protected = "FINDINGS: Left pleural effusion."
    run, report = "a" * 32, "b" * 32
    service.start(run, report, document(protected))
    service.executor.shutdown(wait=True)
    for _ in range(100):
        result = service.get(run, report)
        if result["status"] != "PROCESSING":
            break
        sleep(.01)
    assert result["status"] == "AVAILABLE" and result["raw_response"].endswith("Left pleural effusion")
    assert received == [protected] and identified not in (tmp_path / f"{run}_{report}.json").read_text()
    assert result["comparison"]["counts"]["AGREEMENT"] == 1
    assert "reviewed_record_id" not in result and "UNDERSTAND" not in result["native_document"]["stage_results"]
    assert result["native_document"]["stage_results"]["PROTECT"]["protected_document"]["report_id"] == report
    assert len(service.list()) == 1
    failed = ComparisonEvaluationService(tmp_path / "failure", MedGemmaTextAdapter(
        lambda _: {"status": "FAILED", "code": "INFERENCE_FAILED"}))
    failed.start(run, report, document(protected))
    failed.executor.shutdown(wait=True)
    for _ in range(100):
        failure = failed.get(run, report)
        if failure["status"] != "PROCESSING":
            break
        sleep(.01)
    assert failure["status"] == "FAILED" and failure["comparison"]["status"] == "COMPARISON_NOT_VALID"
    assert failure["native_document"]["stage_results"]["EXTRACT"] == result["native_document"]["stage_results"]["EXTRACT"]


def test_multiple_reports_are_independent_and_queued(tmp_path):
    received = []
    adapter = MedGemmaTextAdapter(lambda text: (received.append(text),
        {"status": "AVAILABLE", "raw_response": "**Clinically Important Findings:**\n* " + text})[1])
    service = ComparisonEvaluationService(tmp_path, adapter)
    first, second = "b" * 32, "c" * 32
    service.start("a" * 32, first, document("Left pleural effusion", first))
    service.start("a" * 32, second, document("No pneumothorax", second))
    service.executor.shutdown(wait=True)
    assert received == ["Left pleural effusion", "No pneumothorax"]
    assert service.get("a" * 32, first)["raw_response"] != service.get("a" * 32, second)["raw_response"]
    assert len(service.list()) == 2


def test_repetition_guard_detects_blocks_without_flagging_distinct_report_items():
    assert MAX_NEW_TOKENS == 2000
    assert repeated_token_block(list(range(20)) + list(range(20)) + list(range(20)))
    assert not repeated_token_block(list(range(60)))
    assert repeated_text_block("Findings:\n" + ("The same clinical sentence repeats here.\n" * 3))
    assert not repeated_text_block("Findings:\n- Left effusion\n- Right mass\n- No pneumothorax")


def test_guarded_generation_keeps_raw_but_invalidates_comparison(tmp_path):
    raw = "Findings:\n" + ("The same clinical sentence repeats here.\n" * 3)
    adapter = MedGemmaTextAdapter(lambda _: {"status": "FAILED", "code": LIMIT_CODE,
        "raw_response": raw, "input_tokens": 100, "output_tokens": MAX_NEW_TOKENS,
        "token_limit_reached": True, "repetition_detected": True})
    service = ComparisonEvaluationService(tmp_path, adapter)
    run, report = "a" * 32, "b" * 32
    service.start(run, report, document("Left pleural effusion"))
    service.executor.shutdown(wait=True)
    stored = json.loads((tmp_path / f"{run}_{report}.json").read_text(encoding="utf-8"))
    response = service.get(run, report)
    assert stored["raw_response"] == raw
    assert response["status"] == "FAILED" and response["failure_code"] == LIMIT_CODE
    assert response["raw_response"] == raw
    assert response["comparison"]["status"] == "COMPARISON_NOT_VALID"
    assert response["comparison"]["comparison_valid"] is False
    assert response["native_document"]["stage_results"]["EXTRACT"] == document("Left pleural effusion")["stage_results"]["EXTRACT"]


def test_prior_available_token_limit_is_invalid_without_rewriting_technical_history(tmp_path):
    raw = "Findings:\n" + ("The same clinical sentence repeats here.\n" * 3)
    service = ComparisonEvaluationService(tmp_path, MedGemmaTextAdapter(lambda _: {
        "status": "AVAILABLE", "raw_response": raw, "output_tokens": MAX_NEW_TOKENS}))
    run, report = "a" * 32, "b" * 32
    service.start(run, report, document("Left pleural effusion"))
    service.executor.shutdown(wait=True)
    path = tmp_path / f"{run}_{report}.json"
    before = path.read_bytes()
    response = service.get(run, report)
    assert response["status"] == "FAILED" and response["failure_code"] == LIMIT_CODE
    assert response["raw_response"] == raw
    assert response["comparison"]["status"] == "COMPARISON_NOT_VALID"
    assert path.read_bytes() == before
    assert json.loads(before)["raw_response"] == raw


def test_official_worker_contract_is_plain_text_and_offline():
    worker = Path(__file__).parents[1] / "app/modules/medical_document_intelligence/services/medgemma_worker.py"
    source = worker.read_text(encoding="utf-8")
    assert 'max_new_tokens=MAX_NEW_TOKENS' in source
    assert 'device_map="auto"' in source and 'do_sample=False' in source
    assert 'repetition_penalty=1.3' in source and 'no_repeat_ngram_size=4' in source
    assert 'local_files_only=True' in source and 'processor.decode(output_ids' in source
    assert 'prompt = INSTRUCTION + "\\n\\n" + text' in source
    assert 'medgemma_product_prompt.txt' not in source
