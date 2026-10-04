"""Explicit pilot subprocess boundary; no ML dependency in the application."""
import json
import os
from pathlib import Path
import subprocess
from threading import Lock

from .extraction_diagnostics import ExtractionDiagnosticError, diagnostic


class RadGraphXLAdapter:
    executable = Path(r"D:\MedNexus\Environments\mrj-radgraph\Scripts\python.exe")
    _runtime_lock = Lock()

    def extract(self, sections):
        if not self.executable.is_file():
            raise ExtractionDiagnosticError(diagnostic("LAUNCH_FAILURE", exception=FileNotFoundError(), stage="launch"))
        # Serialize GPU jobs. Report text is stdin only, never command arguments/files.
        with self._runtime_lock:
            try:
                completed = subprocess.run(
                    [str(self.executable), "-B", str(Path(__file__).with_name("radgraph_worker.py"))],
                    input=json.dumps({"protocol": 1, "sections": [{"text": s["text"]} for s in sections]}),
                    capture_output=True, text=True, encoding="utf-8", timeout=180,
                    env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except subprocess.TimeoutExpired as exc:
                raise ExtractionDiagnosticError(diagnostic("TIMEOUT", exception=exc, stage="response")) from exc
            except OSError as exc:
                raise ExtractionDiagnosticError(diagnostic("LAUNCH_FAILURE", exception=exc, stage="launch")) from exc
            try:
                payload = json.loads(completed.stdout)
            except (ValueError, TypeError) as exc:
                raise ExtractionDiagnosticError(diagnostic("MALFORMED_JSON", exception=exc,
                    return_code=completed.returncode, stderr=completed.stderr)) from exc
            if isinstance(payload, dict) and (payload.get("ok") is False or payload.get("error")):
                raise ExtractionDiagnosticError(diagnostic(payload.get("error_code", "WORKER_FAILURE"),
                    exception_type=payload.get("exception_type"), stage=payload.get("stage"),
                    device=payload.get("device"), return_code=completed.returncode,
                    stderr=completed.stderr or payload.get("stderr_tail", "")))
            if completed.returncode:
                raise ExtractionDiagnosticError(diagnostic("WORKER_FAILURE", return_code=completed.returncode,
                    stderr=completed.stderr))
            if (not isinstance(payload, dict) or payload.get("protocol") != 1
                    or not isinstance(payload.get("sections"), list) or len(payload["sections"]) != len(sections)):
                raise ExtractionDiagnosticError(diagnostic("INVALID_RESPONSE", return_code=completed.returncode,
                    stderr=completed.stderr))
            return payload
