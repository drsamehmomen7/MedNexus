from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from threading import RLock
from time import monotonic
from typing import Any
from uuid import uuid4

from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import PolicyProfile
from backend.app.modules.medical_document_intelligence.services.deidentification import DeidentificationService

from .context_models import MedNexusDocumentContext


class JourneyMode(str, Enum):
    SINGLE = "SINGLE"
    BATCH = "BATCH"


class JourneyStage(str, Enum):
    UNDERSTAND = "UNDERSTAND"
    PROTECT = "PROTECT"
    EXTRACT = "EXTRACT"
    STANDARDIZE = "STANDARDIZE"
    ANALYZE = "ANALYZE"
    VISUALIZE = "VISUALIZE"
    INDICATORS = "INDICATORS"


class StageStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


PUBLIC_JOURNEY_STAGES = tuple(JourneyStage)
TERMINAL_UNDERSTAND_STATUSES = {
    StageStatus.COMPLETE,
    StageStatus.NEEDS_REVIEW,
    StageStatus.FAILED,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime | None = None) -> str:
    return (value or _utc_now()).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class JourneyRecord:
    """Backward-compatible single-document handoff record."""

    document: DocumentContent
    context: MedNexusDocumentContext


@dataclass(slots=True)
class JourneyDocument:
    document_id: str
    original_filename: str
    order: int
    source_type: str
    current_stage: JourneyStage = JourneyStage.UNDERSTAND
    stage_status: dict[JourneyStage, StageStatus] = field(default_factory=dict)
    stage_results: dict[JourneyStage, dict[str, Any]] = field(default_factory=dict)
    stage_history: list[dict[str, str]] = field(default_factory=list)
    warnings: tuple[str, ...] = ()
    review_status: str = "PENDING"
    error: str | None = None
    document: DocumentContent | None = field(default=None, repr=False)
    context: MedNexusDocumentContext | None = field(default=None, repr=False)
    content_digest: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.stage_status:
            self.stage_status = {
                stage: StageStatus.NOT_STARTED for stage in PUBLIC_JOURNEY_STAGES
            }
        if not self.stage_history:
            self.transition(JourneyStage.UNDERSTAND, StageStatus.QUEUED)

    def transition(self, stage: JourneyStage, status: StageStatus) -> None:
        self.stage_status[stage] = status
        self.current_stage = stage
        self.stage_history.append(
            {"stage": stage.value, "status": status.value, "at": _timestamp()}
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "original_filename": self.original_filename,
            "order": self.order,
            "source_type": self.source_type,
            "current_stage": self.current_stage.value,
            "stage_status": {
                stage.value: {"status": self.stage_status[stage].value}
                for stage in PUBLIC_JOURNEY_STAGES
            },
            "stage_results": {
                stage.value: result for stage, result in self.stage_results.items()
            },
            "stage_history": list(self.stage_history),
            "warnings": list(self.warnings),
            "review_status": self.review_status,
            "error": self.error,
        }


@dataclass(slots=True)
class JourneyRun:
    run_id: str
    mode: JourneyMode
    created_at: str
    expires_at: str
    current_stage: JourneyStage = JourneyStage.UNDERSTAND
    documents: list[JourneyDocument] = field(default_factory=list)
    _last_access: float = field(default_factory=monotonic, repr=False)


class JourneyStore:
    """Bounded process-local journey storage for the current POC.

    Extracted clinical content lives only in application memory. It is never
    written to Git, logs, browser storage, or a durable database. Runs expire
    after a sliding TTL and are also evicted by capacity or process restart.
    """

    def __init__(
        self,
        capacity: int = 32,
        ttl_seconds: int = 30 * 60,
        max_batch_documents: int = 10,
    ) -> None:
        if capacity < 1 or ttl_seconds < 1 or max_batch_documents < 1:
            raise ValueError("Journey store limits must be positive integers.")
        self._capacity = capacity
        self._ttl_seconds = ttl_seconds
        self._max_batch_documents = max_batch_documents
        self._runs: OrderedDict[str, JourneyRun] = OrderedDict()
        self._lock = RLock()

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    @property
    def max_batch_documents(self) -> int:
        return self._max_batch_documents

    def create_run(
        self, mode: JourneyMode | str, *, run_id: str | None = None
    ) -> JourneyRun:
        selected_mode = mode if isinstance(mode, JourneyMode) else JourneyMode(mode.upper())
        created = _utc_now()
        run = JourneyRun(
            run_id=run_id or uuid4().hex,
            mode=selected_mode,
            created_at=_timestamp(created),
            expires_at=_timestamp(created + timedelta(seconds=self._ttl_seconds)),
        )
        with self._lock:
            self._cleanup_locked()
            self._runs[run.run_id] = run
            self._runs.move_to_end(run.run_id)
            while len(self._runs) > self._capacity:
                self._runs.popitem(last=False)
        return run

    def retain(
        self,
        document: DocumentContent,
        context: MedNexusDocumentContext,
        result: dict[str, Any] | None = None,
    ) -> str:
        """Retain the existing one-document journey contract unchanged."""

        journey_id = context.document.document_id
        run = self.create_run(JourneyMode.SINGLE, run_id=journey_id)
        item = JourneyDocument(
            document_id=journey_id,
            original_filename=document.source_name,
            order=0,
            source_type=document.extension.lstrip(".") or "text",
            document=document,
            context=context,
        )
        item.transition(JourneyStage.UNDERSTAND, StageStatus.PROCESSING)
        self._complete_item(
            item, document, context, result or {"document_context": context.to_dict()}
        )
        with self._lock:
            run.documents.append(item)
            self._touch_locked(run)
        return journey_id

    def get(self, journey_id: str) -> JourneyRecord:
        run = self.get_run(journey_id)
        if run.mode is not JourneyMode.SINGLE or len(run.documents) != 1:
            raise LookupError("Journey session was not found or has expired.")
        item = run.documents[0]
        if item.document is None or item.context is None:
            raise LookupError("Journey session was not found or has expired.")
        return JourneyRecord(item.document, item.context)

    def get_run(self, run_id: str) -> JourneyRun:
        with self._lock:
            self._cleanup_locked()
            try:
                run = self._runs[run_id]
            except KeyError as exc:
                raise LookupError("Journey run was not found or has expired.") from exc
            self._touch_locked(run)
            return run

    def begin_document(
        self,
        run_id: str,
        *,
        original_filename: str,
        order: int,
        source_type: str,
        content_digest: str | None,
    ) -> JourneyDocument:
        with self._lock:
            run = self._get_batch_run_locked(run_id)
            self._assert_new_document_allowed(run, order)
            item = JourneyDocument(
                document_id=uuid4().hex,
                original_filename=original_filename,
                order=order,
                source_type=source_type,
                content_digest=content_digest,
            )
            run.documents.append(item)
            run.documents.sort(key=lambda value: value.order)
            if content_digest and any(
                existing is not item and existing.content_digest == content_digest
                for existing in run.documents
            ):
                self._fail_item(item, "Duplicate report rejected before analysis.")
            else:
                item.transition(JourneyStage.UNDERSTAND, StageStatus.PROCESSING)
            self._touch_locked(run)
            return item

    def retry_document(
        self,
        run_id: str,
        document_id: str,
        *,
        original_filename: str,
        source_type: str,
        content_digest: str | None,
    ) -> JourneyDocument:
        with self._lock:
            run = self._get_batch_run_locked(run_id)
            item = self._find_document(run, document_id)
            if item.stage_status[JourneyStage.UNDERSTAND] is not StageStatus.FAILED:
                raise ValueError("Only a failed report can be retried.")
            item.original_filename = original_filename
            item.source_type = source_type
            item.content_digest = content_digest
            item.error = None
            item.warnings = ()
            item.review_status = "PENDING"
            item.stage_results.pop(JourneyStage.UNDERSTAND, None)
            for stage in PUBLIC_JOURNEY_STAGES[1:]:
                if item.stage_status[stage] is StageStatus.BLOCKED:
                    item.transition(stage, StageStatus.NOT_STARTED)
            if content_digest and any(
                existing is not item and existing.content_digest == content_digest
                for existing in run.documents
            ):
                self._fail_item(item, "Duplicate report rejected before analysis.")
            else:
                item.transition(JourneyStage.UNDERSTAND, StageStatus.PROCESSING)
            self._touch_locked(run)
            return item

    def complete_document(
        self,
        run_id: str,
        document_id: str,
        *,
        document: DocumentContent,
        context: MedNexusDocumentContext,
        result: dict[str, Any],
    ) -> JourneyDocument:
        with self._lock:
            run = self._get_batch_run_locked(run_id)
            item = self._find_document(run, document_id)
            self._complete_item(item, document, context, result)
            self._touch_locked(run)
            return item

    def fail_document(self, run_id: str, document_id: str, error: str) -> JourneyDocument:
        with self._lock:
            run = self._get_batch_run_locked(run_id)
            item = self._find_document(run, document_id)
            self._fail_item(item, error)
            self._touch_locked(run)
            return item

    def run_payload(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        documents = sorted(run.documents, key=lambda value: value.order)
        status_counts = {
            stage.value: {
                status.value: sum(
                    item.stage_status[stage] is status for item in documents
                )
                for status in StageStatus
            }
            for stage in PUBLIC_JOURNEY_STAGES
        }
        understand_statuses = [
            item.stage_status[JourneyStage.UNDERSTAND] for item in documents
        ]
        successful = [
            item for item in documents if JourneyStage.UNDERSTAND in item.stage_results
        ]
        recognized = sum(
            item.stage_results[JourneyStage.UNDERSTAND].get("domain") != "UNKNOWN"
            for item in successful
        )
        high_confidence = sum(
            item.stage_results[JourneyStage.UNDERSTAND].get("confidence_band") == "HIGH"
            for item in successful
        )
        needs_review = sum(
            status is StageStatus.NEEDS_REVIEW for status in understand_statuses
        )
        failed = sum(status is StageStatus.FAILED for status in understand_statuses)
        analyzed = sum(status in TERMINAL_UNDERSTAND_STATUSES for status in understand_statuses)
        return {
            "run_id": run.run_id,
            "mode": run.mode.value.lower(),
            "created_at": run.created_at,
            "expires_at": run.expires_at,
            "storage": {
                "kind": "ephemeral_process_memory",
                "ttl_seconds": self._ttl_seconds,
                "durable": False,
            },
            "current_stage": run.current_stage.value,
            "documents": [item.to_dict() for item in documents],
            "summary": {
                "total": len(documents),
                "analyzed": analyzed,
                "recognized": recognized,
                "high_confidence": high_confidence,
                "needs_review": needs_review,
                "failed": failed,
            },
            "stage_summary": status_counts,
            "handoff": {
                "protect": {
                    "available": run.mode is JourneyMode.SINGLE and len(documents) == 1,
                    "document_count": len(documents),
                    "reason": (
                        None
                        if run.mode is JourneyMode.SINGLE and len(documents) == 1
                        else "Batch Privacy Protection is not implemented in this checkpoint; all reports remain retained in this journey run."
                    ),
                }
            },
        }

    def protect(self, journey_id: str, policy: PolicyProfile, service: DeidentificationService):
        return service.process(self.get(journey_id).document.text, policy=policy)

    def _complete_item(
        self,
        item: JourneyDocument,
        document: DocumentContent,
        context: MedNexusDocumentContext,
        result: dict[str, Any],
    ) -> None:
        item.document = document
        item.context = context
        item.stage_results[JourneyStage.UNDERSTAND] = result
        item.warnings = tuple(result.get("warnings", ()))
        item.error = None
        review_required = context.processing_context.document_review_required
        if review_required:
            item.review_status = "NEEDS_REVIEW"
            item.transition(JourneyStage.UNDERSTAND, StageStatus.NEEDS_REVIEW)
            self._block_downstream(item)
        else:
            item.review_status = "CLEAR"
            item.transition(JourneyStage.UNDERSTAND, StageStatus.COMPLETE)

    def _fail_item(self, item: JourneyDocument, error: str) -> None:
        item.error = error
        item.review_status = "FAILED"
        item.transition(JourneyStage.UNDERSTAND, StageStatus.FAILED)
        self._block_downstream(item)

    @staticmethod
    def _block_downstream(item: JourneyDocument) -> None:
        for stage in PUBLIC_JOURNEY_STAGES[1:]:
            if item.stage_status[stage] is StageStatus.NOT_STARTED:
                item.stage_status[stage] = StageStatus.BLOCKED
                item.stage_history.append(
                    {"stage": stage.value, "status": StageStatus.BLOCKED.value, "at": _timestamp()}
                )

    def _assert_new_document_allowed(self, run: JourneyRun, order: int) -> None:
        if len(run.documents) >= self._max_batch_documents:
            raise ValueError(
                f"A batch journey supports at most {self._max_batch_documents} reports."
            )
        if order < 0:
            raise ValueError("Report order must be zero or greater.")
        if any(item.order == order for item in run.documents):
            raise ValueError("A report already exists at this batch order.")

    def _get_batch_run_locked(self, run_id: str) -> JourneyRun:
        self._cleanup_locked()
        try:
            run = self._runs[run_id]
        except KeyError as exc:
            raise LookupError("Journey run was not found or has expired.") from exc
        if run.mode is not JourneyMode.BATCH:
            raise ValueError("This operation requires a batch journey run.")
        return run

    @staticmethod
    def _find_document(run: JourneyRun, document_id: str) -> JourneyDocument:
        for item in run.documents:
            if item.document_id == document_id:
                return item
        raise LookupError("Journey document was not found in this run.")

    def _touch_locked(self, run: JourneyRun) -> None:
        run._last_access = monotonic()
        run.expires_at = _timestamp(_utc_now() + timedelta(seconds=self._ttl_seconds))
        self._runs.move_to_end(run.run_id)

    def _cleanup_locked(self) -> None:
        now = monotonic()
        expired = [
            run_id
            for run_id, run in self._runs.items()
            if now - run._last_access >= self._ttl_seconds
        ]
        for run_id in expired:
            self._runs.pop(run_id, None)


journey_store = JourneyStore()
