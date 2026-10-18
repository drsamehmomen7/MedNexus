"""No ML runtime is loaded by these protected-boundary pilot tests."""
import json

from backend.app.modules.medical_document_intelligence.services.clinical_extraction import ClinicalExtractionService
from backend.app.modules.medical_document_intelligence.services.medgemma_adapter import (
    MODEL_ID, REVISION, MedGemmaCandidateAdapter, validate_candidates,
)


TEXT = "FINDINGS: Small left pleural effusion. No pneumothorax."
SECTIONS = [{"text": TEXT, "start": 0, "end": len(TEXT),
             "role": "FINDINGS_DESCRIPTION", "section_id": "one", "heading": "FINDINGS"}]


def item(quote="Small left pleural effusion."):
    return {"concept": "pleural effusion", "display_text": "Left pleural effusion",
            "assertion": "PRESENT", "anatomy": ["pleura"], "laterality": "LEFT",
            "measurement": None, "source_quote": quote, "confidence": None,
            "candidate_role": "FACT"}


def response(items):
    return {"status": "AVAILABLE", "raw_response": json.dumps({"candidate_items": items}),
            "input_tokens": 20, "output_tokens": 30}


def compact_item(quote="Small left pleural effusion.", **changes):
    return {**{"concept": "Left pleural effusion", "assertion": "PRESENT",
               "anatomy": ["pleura"], "laterality": "LEFT", "measurement": None,
               "source_quote": quote, "candidate_role": "FINDING"}, **changes}


def test_disabled_never_starts_worker(monkeypatch):
    monkeypatch.delenv("MRJ_MEDGEMMA_ENABLED", raising=False)
    calls = []
    result = MedGemmaCandidateAdapter(lambda text: calls.append(text)).extract(
        protected_text=TEXT, sections=SECTIONS)
    assert result["status"] == "DISABLED" and calls == []


def test_only_protected_representation_crosses_adapter_boundary(monkeypatch):
    monkeypatch.setenv("MRJ_MEDGEMMA_ENABLED", "true")
    original = "Patient: Identified Person. " + TEXT
    received = []
    adapter = MedGemmaCandidateAdapter(lambda text: (received.append(text), response([item()]))[1])
    result = adapter.extract(protected_text=TEXT, sections=SECTIONS)
    assert result["status"] == "AVAILABLE"
    assert received == [TEXT] and original not in received
    assert adapter.extract(protected_text=TEXT, sections=[{**SECTIONS[0], "text": original}])["status"] == "FAILED"
    assert received == [TEXT]


def test_exact_alignment_and_runner_metadata():
    result = validate_candidates(json.dumps({"candidate_items": [item()]}), TEXT, SECTIONS)
    assert result["status"] == "AVAILABLE"
    assert result["raw_candidate_count"] == result["validated_candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["candidate_id"] == "medgemma-0001"
    assert TEXT[candidate["source_start"]:candidate["source_end"]] == candidate["source_quote"]
    assert (candidate["model_id"], candidate["model_revision"]) == (MODEL_ID, REVISION)
    assert candidate["review_state"] == "NEEDS_REVIEW"


def test_compact_product_contract_receives_only_deterministic_mrj_fields():
    result = validate_candidates(json.dumps({"candidates": [compact_item()]}), TEXT, SECTIONS)
    assert result["status"] == "AVAILABLE"
    assert result["raw_candidates"][0] == compact_item()
    candidate = result["candidates"][0]
    assert candidate["display_text"] == "Left pleural effusion"
    assert candidate["assertion"] == "PRESENT" and candidate["candidate_role"] == "FACT"
    assert candidate["confidence"] is None
    assert TEXT[candidate["source_start"]:candidate["source_end"]] == candidate["source_quote"]


def test_compact_recommendation_and_negative_are_preserved():
    report = "No thrombosis. Recommend follow-up ultrasound in 3 to 6 months."
    sections = [{"text": report, "start": 0, "end": len(report), "role": "FINDINGS_DESCRIPTION"}]
    negative = compact_item("No thrombosis.", concept="Thrombosis", assertion="ABSENT",
                            candidate_role="PERTINENT_NEGATIVE", anatomy=["vein"], laterality="UNSPECIFIED")
    followup = compact_item("Recommend follow-up ultrasound in 3 to 6 months.",
                            concept="Follow-up ultrasound in 3 to 6 months",
                            candidate_role="RECOMMENDATION", anatomy=[], laterality="UNSPECIFIED")
    result = validate_candidates(json.dumps({"candidates": [negative, followup]}), report, sections)
    assert result["status"] == "AVAILABLE" and result["validated_candidate_count"] == 2
    assert result["candidates"][0]["assertion"] == "ABSENT_NEGATED"
    assert result["candidates"][1]["candidate_role"] == "RECOMMENDATION"
    assert result["candidates"][1]["source_quote"] == followup["source_quote"]


def test_compact_contract_rejects_extra_fields_and_nonverbatim_evidence():
    extra = compact_item(display_text="Model-supplied display")
    invented = compact_item("Unstated finding.")
    result = validate_candidates(json.dumps({"candidates": [extra, invented]}), TEXT, SECTIONS)
    assert result["status"] == "NO_VALID_CANDIDATES"
    assert [warning["code"] for warning in result["warnings"]] == [
        "INVALID_CANDIDATE_FIELDS", "EVIDENCE_QUOTE_NOT_FOUND"]


def test_repeated_quote_is_ambiguous_and_zero_match_is_rejected():
    repeated = TEXT + " " + item()["source_quote"]
    sections = [{**SECTIONS[0], "text": repeated, "end": len(repeated)}]
    ambiguous = validate_candidates(json.dumps({"candidate_items": [item()]}), repeated, sections)
    missing = validate_candidates(json.dumps({"candidate_items": [item("Invented finding.")]}), TEXT, SECTIONS)
    assert ambiguous["status"] == missing["status"] == "NO_VALID_CANDIDATES"
    assert ambiguous["warnings"][0]["code"] == "EVIDENCE_LOCATION_AMBIGUOUS"
    assert missing["warnings"][0]["code"] == "EVIDENCE_QUOTE_NOT_FOUND"


def test_raw_duplicates_retained_and_review_suggestions_deduplicated():
    result = validate_candidates(json.dumps([item(), item()]), TEXT, SECTIONS)
    assert result["normalization_actions"] == ["WRAP_TOP_LEVEL_ARRAY"]
    assert result["raw_candidate_count"] == 2
    assert result["validated_candidate_count"] == 2
    assert result["duplicate_candidate_count"] == 1
    assert result["final_governed_candidate_count"] == 1
    assert len(result["raw_candidates"]) == 2 and len(result["candidates"]) == 1


def test_malformed_or_wrong_field_type_fails_closed():
    assert validate_candidates("not json", TEXT, SECTIONS)["status"] == "FAILED"
    bad = item()
    bad["assertion"] = ["PRESENT"]
    result = validate_candidates(json.dumps({"candidate_items": [bad]}), TEXT, SECTIONS)
    assert result["status"] == "NO_VALID_CANDIDATES"
    assert result["warnings"][0]["code"] == "INVALID_CANDIDATE_FIELDS"


def test_single_complete_fenced_answer_is_validated_even_with_model_preface():
    answer = json.dumps([item()])
    raw = "<unused94>thought\ninternal preface\n```json\n" + answer + "\n```\ncontinued prose"
    result = validate_candidates(raw, TEXT, SECTIONS)
    assert result["status"] == "AVAILABLE"
    assert result["normalization_actions"] == ["EXTRACT_SINGLE_JSON_FENCE", "WRAP_TOP_LEVEL_ARRAY"]
    assert result["raw_response"] == raw
    assert len(result["candidates"]) == 1
    ambiguous = raw + "\n```json\n" + answer + "\n```"
    assert validate_candidates(ambiguous, TEXT, SECTIONS)["status"] == "FAILED"


class NativeAdapter:
    def extract(self, sections):
        return {"sections": [{"text": section["text"], "entities": {}} for section in sections],
                "engine_metadata": {"engine": "RadGraph-XL"}, "timing": {}}


def test_optional_failure_preserves_native_and_cannot_create_reviewed_record(monkeypatch):
    monkeypatch.setenv("MRJ_MEDGEMMA_ENABLED", "true")
    unavailable = MedGemmaCandidateAdapter(lambda text: {"status": "UNAVAILABLE", "code": "LOCAL_MODEL_UNAVAILABLE"})
    result = ClinicalExtractionService(NativeAdapter(), unavailable).extract(
        protected_text=TEXT, sections=SECTIONS, report_id="report", run_id="run",
        protected_document={"output_version": "1", "selected_policy_id": "test"})
    assert result["state"] == "NEEDS_REVIEW" and result["clinical_synthesis"]
    assert result["engine_metadata"]["engine"] == "RadGraph-XL"
    assert "reviewed_record_id" not in result
    assert "medgemma_pilot" not in result
    assert "medgemma" not in result["raw_engine_evidence"]


def test_worker_failure_cannot_change_native_result(monkeypatch):
    monkeypatch.setenv("MRJ_MEDGEMMA_ENABLED", "true")
    adapter = MedGemmaCandidateAdapter(lambda _: {
        "status": "FAILED", "code": "INFERENCE_FAILED",
        "diagnostics": {"report_id": None, "journey_id": None,
                        "worker_started": True, "model_loaded": True,
                        "inference_started": True, "failure_stage": "INFERENCE",
                        "exception_type": "RuntimeError", "exception_message": "CUDA launch failed",
                        "stderr_tail": "driver warning"}})
    result = ClinicalExtractionService(NativeAdapter(), adapter).extract(
        protected_text=TEXT, sections=SECTIONS, report_id="report", run_id="run",
        protected_document={"output_version": "1", "selected_policy_id": "test"})
    assert result["state"] == "NEEDS_REVIEW" and result["clinical_synthesis"]
    assert "medgemma_pilot" not in result
    assert "medgemma" not in result["raw_engine_evidence"]


def test_parse_and_validation_phases_are_recorded_without_changing_results(monkeypatch):
    monkeypatch.setenv("MRJ_MEDGEMMA_ENABLED", "true")
    valid = MedGemmaCandidateAdapter(lambda _: response([item()])).extract(
        protected_text=TEXT, sections=SECTIONS, report_id="report", run_id="run")
    assert valid["status"] == "AVAILABLE"
    assert all(valid["diagnostics"][name] for name in
               ("raw_response_received", "parsing_started", "parsing_completed", "validation_completed"))
    assert valid["diagnostics"]["raw_candidate_count"] == 1
    assert valid["diagnostics"]["validated_candidate_count"] == 1
    malformed = MedGemmaCandidateAdapter(lambda _: {"status": "AVAILABLE", "raw_response": "not json"}).extract(
        protected_text=TEXT, sections=SECTIONS)
    assert malformed["status"] == "FAILED"
    assert malformed["diagnostics"]["failure_stage"] == "JSON_PARSING"
    assert malformed["diagnostics"]["exception_type"] == "JSONDecodeError"
    assert malformed["diagnostics"]["parsing_started"] and not malformed["diagnostics"]["parsing_completed"]


def test_protected_text_echo_is_redacted_from_diagnostics(monkeypatch):
    monkeypatch.setenv("MRJ_MEDGEMMA_ENABLED", "true")
    adapter = MedGemmaCandidateAdapter(lambda _: {
        "status": "FAILED", "code": "INFERENCE_FAILED",
        "diagnostics": {"exception_message": "bad input: " + TEXT,
                        "stderr_tail": "bad input: " + TEXT}})
    result = adapter.extract(protected_text=TEXT, sections=SECTIONS)
    assert result["diagnostics"]["exception_message"] == "[REDACTED_PROTECTED_TEXT]"
    assert result["diagnostics"]["stderr_tail"] == "[REDACTED_PROTECTED_TEXT]"
