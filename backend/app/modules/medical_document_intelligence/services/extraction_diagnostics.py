"""Allowlisted diagnostics: never serialize arbitrary exception or library text."""
import builtins
import io

EXECUTABLE = r"D:\MedNexus\Environments\mrj-radgraph\Scripts\python.exe"
MESSAGES = {
    "WORKER_FAILURE": "External runtime failed; inspect stage and exception type.",
    "RUNTIME_VERSION_MISMATCH": "External runtime package versions do not match the validated versions.",
    "CUDA_OUT_OF_MEMORY": "CUDA memory allocation failed.",
    "OFFLINE_CACHE_MISS": "Required model resources are unavailable in the offline cache.",
    "RADGRAPH_LOCAL_MODEL_UNAVAILABLE": "Provisioned RadGraph model is unavailable.",
    "LAUNCH_FAILURE": "External runtime could not be started.",
    "TIMEOUT": "External runtime exceeded the 180 second timeout.",
    "MALFORMED_JSON": "External runtime returned invalid JSON.",
    "INVALID_RESPONSE": "External runtime returned an invalid protocol or section ownership.",
    "SYNTHESIS_FAILURE": "Clinical extraction service failed before result acceptance.",
}
TYPES = {name for name, value in vars(builtins).items()
         if isinstance(value, type) and issubclass(value, BaseException)} | {
    "OutOfMemoryError", "LocalEntryNotFoundError", "OfflineModeIsEnabled",
    "JSONDecodeError", "TimeoutExpired", "HFValidationError", "SafetensorError",
    "ConfigurationError", "PackageNotFoundError", "RepositoryNotFoundError",
    "EntryNotFoundError", "RevisionNotFoundError", "GatedRepoError", "UnpicklingError",
    "RadGraphLocalModelUnavailable",
}
STAGES = {"request", "imports", "versions", "model_load", "inference", "serialization", "launch", "response", "synthesis"}


def classify(text):
    if text in MESSAGES.values():
        return next(key for key, value in MESSAGES.items() if value == text)
    text = str(text).lower()
    if "cuda out of memory" in text:
        return "CUDA_OUT_OF_MEMORY"
    if "outgoing traffic has been disabled" in text or "localentrynotfounderror" in text:
        return "OFFLINE_CACHE_MISS"
    return None


def diagnostic(code="WORKER_FAILURE", *, exception=None, stage="response", device=None,
               return_code=None, stderr="", exception_type=None):
    code = code if code in MESSAGES else "WORKER_FAILURE"
    name = type(exception).__name__ if exception is not None else exception_type
    stderr_code = classify(stderr)
    return {"code": code, "component": "ClinicalExtractionService" if stage == "synthesis" else "RadGraphXLAdapter",
            "exception_type": name if name in TYPES else "Exception",
            "message": MESSAGES[code], "stage": stage if stage in STAGES else "response",
            "return_code": return_code if type(return_code) is int else None,
            "timeout": code == "TIMEOUT", "runtime_executable": EXECUTABLE,
            "device": device if device in {"cpu", "cuda", "cuda:0"} else None,
            "model_type": "modern-radgraph-xl",
            "stderr_tail": MESSAGES[stderr_code] if stderr_code else ""}


class BoundedTail(io.TextIOBase):
    """Retain at most 2048 characters internally; publish only recognized categories."""
    def __init__(self):
        self.tail = ""

    def write(self, text):
        self.tail = (self.tail + text[-2048:])[-2048:]
        return len(text)


class ExtractionDiagnosticError(RuntimeError):
    def __init__(self, technical):
        self.technical = diagnostic(technical.get("code"), exception_type=technical.get("exception_type"),
            stage=technical.get("stage"), device=technical.get("device"),
            return_code=technical.get("return_code"))
        # Already sanitized at the adapter boundary; do not trust arbitrary messages.
        if technical.get("stderr_tail") in MESSAGES.values():
            self.technical["stderr_tail"] = technical["stderr_tail"]
        super().__init__(self.technical["message"])
