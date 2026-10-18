"""Optional MedGemma candidate engine; the MRJ process imports no ML packages."""
import atexit
from collections import deque
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
import subprocess
from threading import Lock, Thread, Timer
import time


MODEL_ID = "google/medgemma-1.5-4b-it"
REVISION = "91850547d9f0b2fdd21aa7c5f4f3d1a8a52c243b"
EXECUTABLE = Path(r"D:\MedNexus\Environments\mrj-medgemma\Scripts\python.exe")
SNAPSHOT = Path(r"D:\MedNexus\Cache\MedGemma\models--google--medgemma-1.5-4b-it\snapshots") / REVISION
WORKER = Path(__file__).with_name("medgemma_worker.py")
ASSERTIONS = {"PRESENT", "ABSENT_NEGATED", "UNCERTAIN"}
ROLES = {"FACT", "PERTINENT_NEGATIVE", "MEASUREMENT", "CONTEXT",
         "DIAGNOSTIC_CONSIDERATION", "RECOMMENDATION"}
LATERALITIES = {"LEFT", "RIGHT", "BILATERAL", "MIDLINE", "UNSPECIFIED", None}
FIELDS = {"concept", "display_text", "assertion", "anatomy", "laterality",
          "measurement", "source_quote", "confidence", "candidate_role"}
COMPACT_FIELDS = {"concept", "assertion", "anatomy", "laterality",
                  "measurement", "source_quote", "candidate_role"}
COMPACT_ROLES = {"FINDING", "PERTINENT_NEGATIVE", "MEASUREMENT",
                 "DIAGNOSTIC_CONSIDERATION", "RECOMMENDATION"}
PHASE_FIELDS = ("worker_started", "model_load_started", "model_loaded", "inference_started",
                "generation_completed", "raw_response_received", "parsing_started",
                "parsing_completed", "validation_completed")


def _diagnostics(report_id=None, run_id=None):
    return {"report_id": report_id, "journey_id": run_id,
            **{field: False for field in PHASE_FIELDS}, "failure_stage": None,
            "exception_type": None, "exception_message": None, "stderr_tail": None,
            "elapsed_seconds": None, "raw_candidate_count": None,
            "validated_candidate_count": None}


def _private_message(value, protected_text):
    """Keep report content out of technical errors, including echoed snippets."""
    message = str(value or "")
    if not message:
        return None
    if protected_text and (protected_text in message or any(
            len(piece) >= 24 and piece in message
            for piece in re.split(r"[\r\n.!?]", protected_text))):
        return "[REDACTED_PROTECTED_TEXT]"
    return message[-2000:]


def enabled():
    return os.environ.get("MRJ_MEDGEMMA_ENABLED", "").strip().lower() in {"1", "true", "yes"}


class _WorkerClient:
    """One GPU worker per server process, reused between nearby reports."""
    def __init__(self):
        self.lock = Lock()
        self.process = None
        self.responses = Queue()
        self.idle_timer = None
        self.stderr_lines = deque(maxlen=40)

    def _stop_locked(self):
        if self.idle_timer:
            self.idle_timer.cancel()
            self.idle_timer = None
        process = self.process
        self.process = None
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    def close(self):
        with self.lock:
            self._stop_locked()

    def _read_stdout(self, process, responses):
        for line in process.stdout:
            responses.put(line)
        responses.put(None)

    def _read_stderr(self, process, lines):
        for line in process.stderr:
            lines.append(line.rstrip("\r\n")[-500:])

    def _stderr_tail(self):
        return "\n".join(self.stderr_lines)[-2000:] or None

    def _next_payload(self, deadline, diagnostics):
        while True:
            line = self.responses.get(timeout=max(0, deadline - time.monotonic()))
            payload = json.loads(line) if line else {}
            if payload.get("kind") != "PHASE":
                return payload
            phase = payload.get("phase")
            field = {"MODEL_LOAD_STARTED": "model_load_started",
                     "INFERENCE_STARTED": "inference_started",
                     "GENERATION_COMPLETED": "generation_completed"}.get(phase)
            if field:
                diagnostics[field] = True

    def _start_locked(self, diagnostics):
        if self.process and self.process.poll() is None:
            diagnostics.update(worker_started=True, model_loaded=True)
            return {"status": "AVAILABLE"}
        self._stop_locked()
        if not EXECUTABLE.is_file() or not SNAPSHOT.is_dir():
            diagnostics.update(failure_stage="MODEL_LOAD", exception_type="FileNotFoundError",
                               exception_message="Pinned local runtime or model snapshot unavailable")
            return {"status": "UNAVAILABLE", "code": "LOCAL_MODEL_UNAVAILABLE"}
        env = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
               "HF_HUB_DISABLE_TELEMETRY": "1", "PYTHONNOUSERSITE": "1",
               "PYTHONDONTWRITEBYTECODE": "1", "TOKENIZERS_PARALLELISM": "false"}
        try:
            self.stderr_lines = deque(maxlen=40)
            self.process = subprocess.Popen(
                [str(EXECUTABLE), "-B", str(WORKER)], cwd=str(WORKER.parents[5]),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", bufsize=1, env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as exc:
            diagnostics.update(failure_stage="WORKER_LAUNCH", exception_type=type(exc).__name__,
                               exception_message=str(exc))
            return {"status": "UNAVAILABLE", "code": "WORKER_LAUNCH_FAILED"}
        diagnostics["worker_started"] = True
        self.responses = Queue()
        Thread(target=self._read_stdout, args=(self.process, self.responses), daemon=True).start()
        Thread(target=self._read_stderr, args=(self.process, self.stderr_lines), daemon=True).start()
        try:
            payload = self._next_payload(time.monotonic() + 120, diagnostics)
        except (Empty, ValueError, TypeError) as exc:
            diagnostics.update(failure_stage="MODEL_LOAD", exception_type=type(exc).__name__,
                               exception_message=str(exc) or "Worker exited or startup timed out",
                               stderr_tail=self._stderr_tail())
            self._stop_locked()
            return {"status": "UNAVAILABLE", "code": "WORKER_START_FAILED"}
        if payload.get("kind") != "READY" or payload.get("protocol") != 1 or (
                payload.get("model_id"), payload.get("model_revision")) != (MODEL_ID, REVISION):
            diagnostics.update(failure_stage=payload.get("failure_stage") or "MODEL_LOAD",
                               exception_type=payload.get("exception_type"),
                               exception_message=payload.get("exception_message"),
                               stderr_tail=self._stderr_tail())
            self._stop_locked()
            return {"status": "UNAVAILABLE", "code": payload.get("code", "WORKER_START_FAILED")}
        diagnostics["model_loaded"] = True
        return {"status": "AVAILABLE"}

    def _expire(self):
        with self.lock:
            self._stop_locked()

    def _arm_idle_locked(self):
        self.idle_timer = Timer(300, self._expire)
        self.idle_timer.daemon = True
        self.idle_timer.start()

    def request(self, protected_text):
        with self.lock:
            diagnostics = _diagnostics()
            if self.idle_timer:
                self.idle_timer.cancel()
                self.idle_timer = None
            ready = self._start_locked(diagnostics)
            if ready["status"] != "AVAILABLE":
                return {**ready, "diagnostics": diagnostics}
            try:
                self.process.stdin.write(json.dumps({"protocol": 1, "protected_text": protected_text},
                                                    ensure_ascii=False) + "\n")
                self.process.stdin.flush()
                payload = self._next_payload(time.monotonic() + 240, diagnostics)
            except Empty:
                diagnostics.update(failure_stage="INFERENCE", exception_type="TimeoutError",
                                   exception_message="Worker response timed out", stderr_tail=self._stderr_tail())
                self._stop_locked()
                return {"status": "TIMEOUT", "code": "INFERENCE_TIMEOUT", "diagnostics": diagnostics}
            except (OSError, ValueError, TypeError) as exc:
                diagnostics.update(failure_stage="WORKER_PROTOCOL", exception_type=type(exc).__name__,
                                   exception_message=str(exc) or "Worker stream closed",
                                   stderr_tail=self._stderr_tail())
                self._stop_locked()
                return {"status": "FAILED", "code": "WORKER_PROTOCOL_FAILURE", "diagnostics": diagnostics}
            if payload.get("protocol") != 1:
                diagnostics.update(failure_stage="WORKER_PROTOCOL", stderr_tail=self._stderr_tail())
                self._stop_locked()
                return {"status": "FAILED", "code": "WORKER_PROTOCOL_FAILURE", "diagnostics": diagnostics}
            if payload.get("kind") == "ERROR":
                diagnostics.update(failure_stage=payload.get("failure_stage") or "WORKER",
                                   exception_type=payload.get("exception_type"),
                                   exception_message=payload.get("exception_message"),
                                   stderr_tail=self._stderr_tail())
                if self.process.poll() is not None:
                    self._stop_locked()
                else:
                    self._arm_idle_locked()
                return {"status": "FAILED", "code": payload.get("code", "WORKER_FAILURE"),
                        "diagnostics": diagnostics}
            if payload.get("kind") != "RESULT" or not isinstance(payload.get("raw_response"), str):
                diagnostics.update(failure_stage="WORKER_PROTOCOL", stderr_tail=self._stderr_tail())
                self._stop_locked()
                return {"status": "FAILED", "code": "WORKER_PROTOCOL_FAILURE", "diagnostics": diagnostics}
            diagnostics.update(raw_response_received=True, stderr_tail=self._stderr_tail())
            self._arm_idle_locked()
            if payload.get("code") == "GENERATION_REPETITION_LIMIT":
                diagnostics["failure_stage"] = "GENERATION"
                return {"status": "FAILED", **payload, "diagnostics": diagnostics}
            return {"status": "AVAILABLE", **payload, "diagnostics": diagnostics}


_WORKER_CLIENT = _WorkerClient()
atexit.register(_WORKER_CLIENT.close)


class MedGemmaTextAdapter:
    """Independent plain-text evaluation lane; no candidate validation or MRJ mutation."""

    def __init__(self, transport=None):
        self.transport = transport or _WORKER_CLIENT.request

    def extract(self, protected_text):
        if not isinstance(protected_text, str) or not protected_text.strip():
            return {"status": "FAILED", "code": "PROTECTED_INPUT_INVALID"}
        started = time.perf_counter()
        response = self.transport(protected_text)
        response["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        return response


def _parse_raw(raw):
    text = raw.strip()
    actions = []
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) < 3 or lines[0].lower() not in {"```", "```json"} or lines[-1] != "```":
            raise ValueError("Invalid Markdown fence")
        text = "\n".join(lines[1:-1]).strip()
        actions.append("STRIP_MARKDOWN_FENCE")
    elif "```" in text:
        # Some local generations include a reasoning preface and continue past
        # a complete fenced answer. Accept only one unambiguous JSON block;
        # the original response remains available in technical evidence.
        blocks = re.findall(r"(?m)^```(?:json)?[ \t]*\r?\n(.*?)\r?\n```[ \t]*(?:\r?\n|$)",
                            text, flags=re.I | re.S)
        if len(blocks) != 1:
            raise ValueError("Ambiguous fenced candidate payload")
        text = blocks[0].strip()
        actions.append("EXTRACT_SINGLE_JSON_FENCE")
    value = json.loads(text)
    if isinstance(value, list):
        actions.append("WRAP_TOP_LEVEL_ARRAY")
        value = {"candidate_items": value}
    if not isinstance(value, dict) or set(value) not in ({"candidate_items"}, {"candidates"}):
        raise ValueError("Invalid candidate payload")
    key = next(iter(value))
    if not isinstance(value[key], list):
        raise ValueError("Invalid candidate payload")
    return value[key], actions


def _normalized_item(item):
    """Add deterministic MRJ-owned fields to the compact product contract."""
    if not isinstance(item, dict):
        return item
    if set(item) != COMPACT_FIELDS:
        return item
    if (not isinstance(item["assertion"], str) or
            item["assertion"] not in {"PRESENT", "ABSENT", "UNCERTAIN"} or
            not isinstance(item["candidate_role"], str) or
            item["candidate_role"] not in COMPACT_ROLES or
            not isinstance(item["laterality"], str) or
            item["laterality"] not in {"LEFT", "RIGHT", "BILATERAL", "UNSPECIFIED"} or
            item["measurement"] is not None):
        return item
    return {**item, "display_text": item["concept"], "confidence": None,
            "assertion": "ABSENT_NEGATED" if item["assertion"] == "ABSENT" else item["assertion"],
            "candidate_role": "FACT" if item["candidate_role"] == "FINDING" else item["candidate_role"]}


def _valid_item(item):
    if not isinstance(item, dict) or set(item) != FIELDS:
        return False
    if not all(isinstance(item[key], str) and item[key].strip()
               for key in ("concept", "display_text", "source_quote")):
        return False
    if (not isinstance(item["assertion"], str) or item["assertion"] not in ASSERTIONS or
            not isinstance(item["candidate_role"], str) or item["candidate_role"] not in ROLES):
        return False
    if item["laterality"] is not None and (not isinstance(item["laterality"], str) or
            item["laterality"] not in LATERALITIES):
        return False
    anatomy = item["anatomy"]
    if not isinstance(anatomy, list) or any(not isinstance(value, str) or not value.strip() for value in anatomy):
        return False
    measurement = item["measurement"]
    if measurement is not None:
        if not isinstance(measurement, dict) or set(measurement) != {"value", "unit", "anatomy", "laterality", "dimensions"}:
            return False
        if (type(measurement["value"]) not in {int, float} or
                not all(isinstance(measurement[key], str) and measurement[key].strip()
                        for key in ("unit", "anatomy")) or
                (measurement["laterality"] is not None and (
                    not isinstance(measurement["laterality"], str) or
                    measurement["laterality"] not in LATERALITIES)) or
                not isinstance(measurement["dimensions"], list) or
                any(type(value) not in {int, float} for value in measurement["dimensions"])):
            return False
    confidence = item["confidence"]
    return confidence is None or (type(confidence) in {int, float} and 0 <= confidence <= 1)


def validate_candidates(raw, protected_text, sections, diagnostics=None):
    """Validate exact protected evidence; retain every raw model item for audit."""
    audit = {"raw_response": raw, "raw_response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
             "raw_candidates": [], "candidates": [], "warnings": [], "normalization_actions": [],
             "raw_candidate_count": 0, "validated_candidate_count": 0,
             "duplicate_candidate_count": 0, "final_governed_candidate_count": 0}
    if diagnostics is not None:
        diagnostics["parsing_started"] = True
    try:
        items, actions = _parse_raw(raw)
    except (ValueError, TypeError) as exc:
        if diagnostics is not None:
            diagnostics.update(failure_stage="JSON_PARSING", exception_type=type(exc).__name__,
                               exception_message=_private_message(exc, protected_text))
        audit.update(status="FAILED", code="MALFORMED_MODEL_OUTPUT")
        return audit
    if diagnostics is not None:
        diagnostics.update(parsing_completed=True, raw_candidate_count=len(items))
    audit["raw_candidates"] = items
    audit["normalization_actions"] = actions
    audit["raw_candidate_count"] = len(items)
    seen_raw, seen_valid = set(), set()
    for index, item in enumerate(items, 1):
        candidate_id = f"medgemma-{index:04d}"
        if isinstance(item, dict):
            fingerprint = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if fingerprint in seen_raw:
                audit["duplicate_candidate_count"] += 1
            seen_raw.add(fingerprint)
        item = _normalized_item(item)
        if not _valid_item(item):
            audit["warnings"].append({"candidate_id": candidate_id, "code": "INVALID_CANDIDATE_FIELDS"})
            continue
        quote = item["source_quote"]
        occurrences = []
        start = protected_text.find(quote)
        while start != -1:
            occurrences.append(start)
            start = protected_text.find(quote, start + 1)
        if not occurrences:
            audit["warnings"].append({"candidate_id": candidate_id, "code": "EVIDENCE_QUOTE_NOT_FOUND"})
            continue
        if len(occurrences) != 1:
            audit["warnings"].append({"candidate_id": candidate_id, "code": "EVIDENCE_LOCATION_AMBIGUOUS"})
            continue
        start = occurrences[0]
        end = start + len(quote)
        section = next((part for part in sections if part["start"] <= start < end <= part["end"]), None)
        if section is None or protected_text[start:end] != quote:
            audit["warnings"].append({"candidate_id": candidate_id, "code": "EVIDENCE_OUTSIDE_ELIGIBLE_SECTION"})
            continue
        audit["validated_candidate_count"] += 1
        if fingerprint in seen_valid:
            continue
        seen_valid.add(fingerprint)
        audit["candidates"].append({**item, "candidate_id": candidate_id,
            "source_start": start, "source_end": end, "source_section_role": section["role"],
            "engine_name": "MedGemma Candidate Engine", "model_id": MODEL_ID,
            "model_revision": REVISION, "review_state": "NEEDS_REVIEW"})
    audit["final_governed_candidate_count"] = len(audit["candidates"])
    audit["status"] = "AVAILABLE" if audit["candidates"] else "NO_VALID_CANDIDATES"
    if diagnostics is not None:
        diagnostics.update(validation_completed=True,
                           validated_candidate_count=audit["validated_candidate_count"])
    return audit


class MedGemmaCandidateAdapter:
    def __init__(self, transport=None):
        self.transport = transport or _WORKER_CLIENT.request

    def extract(self, *, protected_text, sections, report_id=None, run_id=None):
        started = time.perf_counter()
        diagnostics = _diagnostics(report_id, run_id)

        def finish(result):
            diagnostics["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            for field in ("exception_message", "stderr_tail"):
                diagnostics[field] = _private_message(diagnostics[field], protected_text)
            result["diagnostics"] = diagnostics
            return result

        if not enabled():
            return finish({"status": "DISABLED", "candidates": [], "raw_candidate_count": 0,
                    "validated_candidate_count": 0, "duplicate_candidate_count": 0,
                    "final_governed_candidate_count": 0})
        if (not isinstance(protected_text, str) or not protected_text.strip() or
                not sections or any(not isinstance(part, dict) or
                    type(part.get("start")) is not int or type(part.get("end")) is not int or
                    not 0 <= part["start"] < part["end"] <= len(protected_text) or
                    not isinstance(part.get("text"), str) or
                    protected_text[part["start"]:part["end"]] != part["text"]
                    for part in sections)):
            diagnostics["failure_stage"] = "INPUT_VALIDATION"
            return finish({"status": "FAILED", "code": "PROTECTED_INPUT_INVALID", "candidates": []})
        try:
            response = self.transport(protected_text)
        except Exception as exc:
            diagnostics.update(failure_stage="ADAPTER_TRANSPORT", exception_type=type(exc).__name__,
                               exception_message=str(exc))
            return finish({"status": "FAILED", "code": "WORKER_FAILURE", "candidates": []})
        diagnostics.update({key: value for key, value in (response.get("diagnostics") or {}).items()
                            if key not in {"report_id", "journey_id"}})
        if response.get("status") != "AVAILABLE":
            return finish({"status": response.get("status", "FAILED"),
                    "code": response.get("code", "WORKER_FAILURE"), "candidates": []})
        if not isinstance(response.get("raw_response"), str):
            diagnostics.update(failure_stage="WORKER_PROTOCOL", exception_type="TypeError",
                               exception_message="Worker response has no raw_response string")
            return finish({"status": "FAILED", "code": "WORKER_PROTOCOL_FAILURE", "candidates": []})
        diagnostics["raw_response_received"] = True
        audit = validate_candidates(response["raw_response"], protected_text, sections, diagnostics)
        audit["runtime"] = {"model_id": MODEL_ID, "model_revision": REVISION,
            "input_tokens": response.get("input_tokens"), "output_tokens": response.get("output_tokens"),
            "latency_seconds": response.get("latency_seconds"),
            "peak_gpu_memory_bytes": response.get("peak_gpu_memory_bytes"),
            "token_limit_reached": response.get("token_limit_reached", False)}
        return finish(audit)
