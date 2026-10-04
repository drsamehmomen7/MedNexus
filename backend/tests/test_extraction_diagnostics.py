import io
import json
import subprocess
import sys
import importlib.metadata
from types import SimpleNamespace

import pytest

from backend.app.modules.medical_document_intelligence.services import radgraph_adapter as adapter_module
from backend.app.modules.medical_document_intelligence.services import radgraph_worker as worker
from backend.app.modules.medical_document_intelligence.services.extraction_diagnostics import (
    BoundedTail, ExtractionDiagnosticError, diagnostic,
)
from backend.app.modules.medical_document_intelligence.services.clinical_extraction import ClinicalExtractionService
from backend.tests.test_clinical_extraction_pilot import make_store, Adapter, entity
from backend.app.modules.medical_document_intelligence.understanding.journey import JourneyStage, StageStatus

SECRET = "Identified Person patient MRN 123456 effusion [PATIENT_NAME]"


def test_worker_failure_structured_and_private(monkeypatch):
    def fail(state, stderr):
        state.update(stage="model_load", device="cuda:0")
        stderr.write(SECRET + " CUDA out of memory")
        raise RuntimeError(SECRET + " CUDA out of memory")
    monkeypatch.setattr(worker, "main", fail)
    output = io.StringIO()
    monkeypatch.setattr(worker.sys, "stdout", output)
    assert worker.run() == 1
    result = json.loads(output.getvalue())
    assert result["error_code"] == "CUDA_OUT_OF_MEMORY"
    assert result["exception_type"] == "RuntimeError"
    assert result["stage"] == "model_load"
    assert result["device"] == "cuda:0"
    assert SECRET not in output.getvalue()
    assert "effusion" not in output.getvalue()
    assert "Identified Person" not in output.getvalue()


@pytest.fixture
def adapter(monkeypatch):
    instance = adapter_module.RadGraphXLAdapter()
    monkeypatch.setattr(instance, "executable", SimpleNamespace(is_file=lambda: True))
    return instance


@pytest.mark.parametrize("failure,code", [
    (PermissionError(SECRET), "LAUNCH_FAILURE"),
    (subprocess.TimeoutExpired("worker", 180, output=SECRET, stderr=SECRET), "TIMEOUT"),
])
def test_process_failures(adapter, monkeypatch, failure, code):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(adapter_module.subprocess, "run", fail)
    with pytest.raises(ExtractionDiagnosticError) as caught:
        adapter.extract([{"text": SECRET}])
    assert caught.value.technical["code"] == code
    assert caught.value.technical["timeout"] == (code == "TIMEOUT")
    assert caught.value.__cause__ is failure
    assert SECRET not in json.dumps(caught.value.technical)


@pytest.mark.parametrize("stdout,code", [
    (SECRET, "MALFORMED_JSON"),
    ('[]', "INVALID_RESPONSE"),
    ('{"protocol":1,"sections":[]}', "INVALID_RESPONSE"),
])
def test_invalid_output(adapter, monkeypatch, stdout, code):
    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k:
        SimpleNamespace(stdout=stdout, stderr=SECRET, returncode=0))
    with pytest.raises(ExtractionDiagnosticError) as caught:
        adapter.extract([{"text": SECRET}])
    assert caught.value.technical["code"] == code
    assert SECRET not in json.dumps(caught.value.technical)


def test_adapter_worker_code_and_untrusted_fields(adapter, monkeypatch):
    payload = {"protocol": 1, "ok": False, "error_code": "CUDA_OUT_OF_MEMORY",
               "exception_type": "RuntimeError", "message": SECRET, "stage": "inference",
               "device": SECRET, "stderr_tail": SECRET}
    monkeypatch.setattr(adapter_module.subprocess, "run", lambda *a, **k:
        SimpleNamespace(stdout=json.dumps(payload), stderr=SECRET, returncode=1))
    with pytest.raises(ExtractionDiagnosticError) as caught:
        adapter.extract([{"text": SECRET}])
    d = caught.value.technical
    assert d["code"] == "CUDA_OUT_OF_MEMORY" and d["return_code"] == 1
    assert d["exception_type"] == "RuntimeError" and d["device"] is None
    assert SECRET not in json.dumps(d)


def test_adapter_success_unchanged(adapter, monkeypatch):
    expected = {"protocol": 1, "sections": [{"text": "effusion", "entities": {}}], "timing": {}}
    def complete(*args, **kwargs):
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        assert kwargs["env"]["TRANSFORMERS_OFFLINE"] == "1"
        return SimpleNamespace(stdout=json.dumps(expected), stderr="", returncode=0)
    monkeypatch.setattr(adapter_module.subprocess, "run", complete)
    assert adapter.extract([{"text": "effusion"}]) == expected


@pytest.mark.parametrize("structured", [True, False])
def test_journey_safe_failure_and_retry(structured, caplog):
    store, run, item = make_store()
    class Failure:
        def extract(self, **kwargs):
            if structured:
                raise ExtractionDiagnosticError(diagnostic("TIMEOUT", exception_type="TimeoutExpired"))
            raise ValueError(SECRET)
    store.extract_document(run.run_id, item.document_id, Failure())
    assert item.stage_status[JourneyStage.EXTRACT] == StageStatus.FAILED
    assert item.stage_errors[JourneyStage.EXTRACT] == "Clinical extraction failed; no clinical result was accepted."
    assert JourneyStage.EXTRACT not in item.stage_results
    assert item.to_dict()["technical_error"]["code"] == ("TIMEOUT" if structured else "SYNTHESIS_FAILURE")
    assert len(caplog.records) == 1
    for forbidden in (SECRET, "Identified Person", "effusion", "[PATIENT_NAME]", "123456"):
        assert forbidden not in json.dumps(item.technical_error) + caplog.text
    store.extract_document(run.run_id, item.document_id, ClinicalExtractionService(
        Adapter([{"text": "effusion", "entities": {"1": entity("effusion")}}])))
    assert item.stage_status[JourneyStage.EXTRACT] == StageStatus.NEEDS_REVIEW
    assert "technical_error" not in item.to_dict()


def test_bounded_stderr():
    buffer = BoundedTail()
    buffer.write("x" * 100000)
    assert len(buffer.tail) == 2048


def test_unknown_exception_name_is_not_a_text_channel():
    exc = type(SECRET, (Exception,), {})(SECRET)
    assert SECRET not in json.dumps(diagnostic(exception=exc))


def provision_test_model(cache_root):
    model = cache_root / worker.MODEL_TYPE
    vocabulary = model / "vocabulary"
    vocabulary.mkdir(parents=True)
    for path in (model / "config.json", model / "weights.th",
                 *(vocabulary / name for name in worker.VOCABULARY_FILES)):
        path.write_bytes(b"test artifact")


@pytest.mark.parametrize("failure_stage", [None, "model_load", "inference"])
def test_actual_worker_control_flow(monkeypatch, tmp_path, failure_stage):
    provision_test_model(tmp_path)
    monkeypatch.setenv(worker.MODEL_CACHE_ENV, str(tmp_path))
    class Engine:
        device = SimpleNamespace(type="cpu", __str__=lambda: "cpu")
        model = SimpleNamespace(parameters=lambda: [SimpleNamespace(device="cpu")])
        def __init__(self, **kwargs):
            assert kwargs == {"model_type": worker.MODEL_TYPE,
                              "model_cache_dir": str(tmp_path)}
            if failure_stage == "model_load":
                raise FileNotFoundError(SECRET)
        def __call__(self, texts):
            if failure_stage == "inference":
                raise ValueError(SECRET)
            return {"0": {"text": texts[0], "entities": {}}}
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "radgraph", SimpleNamespace(RadGraph=Engine))
    monkeypatch.setattr(importlib.metadata, "version", lambda name:
        {"torch": "2.12.1+cu130", "radgraph": "0.1.18", "transformers": "4.48.1"}[name])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"protocol": 1, "sections": [{"text": "effusion"}]})))
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    assert worker.run() == int(failure_stage is not None)
    result = json.loads(output.getvalue())
    if failure_stage:
        assert result["stage"] == failure_stage
        assert result["exception_type"] == ("FileNotFoundError" if failure_stage == "model_load" else "ValueError")
        assert "effusion" not in output.getvalue() and SECRET not in output.getvalue()
    else:
        assert result["sections"] == [{"text": "effusion", "entities": {}}]
        assert "ok" not in result and "error_code" not in result


def test_configured_local_model_preflight_and_no_download(monkeypatch, tmp_path):
    provision_test_model(tmp_path)
    monkeypatch.setenv(worker.MODEL_CACHE_ENV, str(tmp_path))
    assert worker.verify_local_model(worker.local_model_cache_dir()) == tmp_path
    assert not (tmp_path / "modern-radgraph-xl.tar.gz").exists()


@pytest.mark.parametrize("incomplete", ["absent", "empty", "missing_weights", "empty_vocab"])
def test_missing_local_model_is_safe_and_explicit(monkeypatch, tmp_path, incomplete):
    if incomplete != "absent":
        provision_test_model(tmp_path)
    if incomplete == "empty":
        (tmp_path / worker.MODEL_TYPE / "config.json").write_bytes(b"")
    elif incomplete == "missing_weights":
        (tmp_path / worker.MODEL_TYPE / "weights.th").unlink()
    elif incomplete == "empty_vocab":
        (tmp_path / worker.MODEL_TYPE / "vocabulary" / worker.VOCABULARY_FILES[0]).write_bytes(b"")
    monkeypatch.setenv(worker.MODEL_CACHE_ENV, str(tmp_path))
    with pytest.raises(worker.RadGraphLocalModelUnavailable) as caught:
        worker.verify_local_model(worker.local_model_cache_dir())
    assert str(caught.value) == "Provisioned RadGraph model is unavailable."
    assert SECRET not in str(caught.value)


def test_missing_model_worker_protocol_contains_no_clinical_text(monkeypatch, tmp_path):
    monkeypatch.setenv(worker.MODEL_CACHE_ENV, str(tmp_path))
    monkeypatch.setattr(importlib.metadata, "version", lambda name:
        {"torch": "2.12.1+cu130", "radgraph": "0.1.18", "transformers": "4.48.1"}[name])
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "radgraph", SimpleNamespace(RadGraph=lambda **kwargs: None))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"protocol": 1, "sections": [{"text": SECRET}]})))
    output = io.StringIO()
    monkeypatch.setattr(sys, "stdout", output)
    assert worker.run() == 1
    payload = json.loads(output.getvalue())
    assert payload["error_code"] == "RADGRAPH_LOCAL_MODEL_UNAVAILABLE"
    assert payload["stage"] == "model_load"
    assert payload["exception_type"] == "RadGraphLocalModelUnavailable"
    assert SECRET not in output.getvalue()


def test_default_cache_root_when_unconfigured(monkeypatch):
    monkeypatch.delenv(worker.MODEL_CACHE_ENV, raising=False)
    assert worker.local_model_cache_dir() == worker.DEFAULT_MODEL_CACHE_DIR
