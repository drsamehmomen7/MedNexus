"""One-report isolated worker. stdin/stdout are an ephemeral JSON protocol.

Run only with the external RadGraph Python; never import ML packages in MRJ.
"""
import contextlib
import json
import os
from pathlib import Path
import sys
import time

if __package__:
    from .extraction_diagnostics import BoundedTail, classify, diagnostic
else:
    from extraction_diagnostics import BoundedTail, classify, diagnostic


MODEL_CACHE_ENV = "MRJ_RADGRAPH_MODEL_CACHE_DIR"
DEFAULT_MODEL_CACHE_DIR = Path(r"D:\MedNexus\Cache\RadGraph\0.1.18")
MODEL_TYPE = "modern-radgraph-xl"
VOCABULARY_FILES = (
    "modern-radgraph-xl__ner_labels.txt",
    "modern-radgraph-xl__relation_labels.txt",
    "non_padded_namespaces.txt",
)


class RadGraphLocalModelUnavailable(RuntimeError):
    """The configured extracted model is incomplete or inaccessible."""


def local_model_cache_dir():
    """Use the one MRJ cache setting; never discover the model via appdirs."""
    configured = os.environ.get(MODEL_CACHE_ENV)
    return Path(configured) if configured is not None else DEFAULT_MODEL_CACHE_DIR


def verify_local_model(cache_dir):
    """Fail closed before RadGraph can try its download fallback."""
    model_dir = cache_dir / MODEL_TYPE
    try:
        required = [model_dir / "config.json", model_dir / "weights.th"]
        required.extend(model_dir / "vocabulary" / name for name in VOCABULARY_FILES)
        if not model_dir.is_dir() or not all(
            path.is_file() and path.stat().st_size > 0 for path in required
        ):
            raise RadGraphLocalModelUnavailable("Provisioned RadGraph model is unavailable.")
    except OSError as exc:
        raise RadGraphLocalModelUnavailable("Provisioned RadGraph model is unavailable.") from exc
    return cache_dir


def main(state=None, stderr=None):
    state = state if state is not None else {}
    state.update(stage="request", device=None)
    stderr = stderr if stderr is not None else BoundedTail()
    request = json.load(sys.stdin)
    if request.get("protocol") != 1 or not isinstance(request.get("sections"), list):
        raise ValueError("Invalid worker request")
    # Raw library diagnostics stay bounded and internal; only categories escape.
    with contextlib.redirect_stdout(BoundedTail()), contextlib.redirect_stderr(stderr):
        state["stage"] = "imports"
        import importlib.metadata as metadata
        import torch
        from radgraph import RadGraph

        state["stage"] = "versions"
        expected = {"radgraph": "0.1.18", "transformers": "4.48.1", "torch": "2.12.1+cu130"}
        if any(metadata.version(name) != version for name, version in expected.items()):
            raise RuntimeError("Runtime version mismatch")
        started = time.perf_counter()
        state["stage"] = "model_load"
        cache_dir = verify_local_model(local_model_cache_dir())
        engine = RadGraph(model_type=MODEL_TYPE, model_cache_dir=str(cache_dir))
        initialization = time.perf_counter() - started
        devices = {str(p.device) for p in engine.model.parameters()}
        started = time.perf_counter()
        state.update(stage="inference", device=str(engine.device))
        results = [engine([section["text"]])["0"] for section in request["sections"]]
        if engine.device.type == "cuda":
            torch.cuda.synchronize()
        inference = time.perf_counter() - started
        response = {
            "protocol": 1, "sections": results,
            "engine_metadata": {"engine": "RadGraph-XL", "package": "radgraph 0.1.18",
                "model_type": "modern-radgraph-xl", "transformers": "4.48.1",
                "execution": "external isolated runtime", "device": next(iter(devices)) if len(devices) == 1 else "UNKNOWN",
                "gpu": torch.cuda.get_device_name(0) if engine.device.type == "cuda" else None},
            "timing": {"initialization_seconds": initialization, "inference_seconds": inference},
            "peak_gpu_memory_bytes": torch.cuda.max_memory_allocated() if engine.device.type == "cuda" else None,
        }
    state["stage"] = "serialization"
    json.dump(response, sys.stdout, ensure_ascii=True)


def run():
    state, stderr = {}, BoundedTail()
    try:
        main(state, stderr)
        return 0
    except Exception as exc:
        if isinstance(exc, RadGraphLocalModelUnavailable):
            code = "RADGRAPH_LOCAL_MODEL_UNAVAILABLE"
        elif state.get("stage") == "versions" and str(exc) == "Runtime version mismatch":
            code = "RUNTIME_VERSION_MISMATCH"
        else:
            code = classify(exc) or "WORKER_FAILURE"
        technical = diagnostic(code, exception=exc, stage=state.get("stage"),
                               device=state.get("device"), stderr=stderr.tail)
        json.dump({"protocol": 1, "ok": False, "error_code": code, **technical}, sys.stdout)
        return 1


if __name__ == "__main__":
    sys.exit(run())
