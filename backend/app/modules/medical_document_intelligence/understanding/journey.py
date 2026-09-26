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
from backend.app.modules.medical_document_intelligence.contracts.protection import (
    ProtectedArtifact,
    build_protect_output,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import PolicyProfile
from backend.app.modules.medical_document_intelligence.services.deidentification import DeidentificationService
from backend.app.modules.medical_document_intelligence.services.protected_document_builder import (
    protected_document_builder,
)

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
TERMINAL_PROTECT_STATUSES = {
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


@dataclass(frozen=True, slots=True)
class EphemeralDocumentArtifact:
    filename: str
    media_type: str
    content: bytes = field(repr=False)


@dataclass(slots=True)
class JourneyDocument:
    document_id: str
    original_filename: str
    order: int
    source_type: str
    current_stage: JourneyStage = JourneyStage.UNDERSTAND
    stage_status: dict[JourneyStage, StageStatus] = field(default_factory=dict)
    stage_results: dict[JourneyStage, dict[str, Any]] = field(default_factory=dict)
    stage_errors: dict[JourneyStage, str] = field(default_factory=dict)
    stage_history: list[dict[str, str]] = field(default_factory=list)
    warnings: tuple[str, ...] = ()
    review_status: str = "PENDING"
    error: str | None = None
    document: DocumentContent | None = field(default=None, repr=False)
    context: MedNexusDocumentContext | None = field(default=None, repr=False)
    content_digest: str | None = field(default=None, repr=False)
    source_artifact: bytes | None = field(default=None, repr=False)
    protected_artifact: bytes | None = field(default=None, repr=False)
    protected_artifact_filename: str | None = field(default=None, repr=False)
    protected_artifact_media_type: str | None = field(default=None, repr=False)

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
            "stage_errors": {
                stage.value: error for stage, error in self.stage_errors.items()
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
        source_artifact: bytes | None = None,
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
            item,
            document,
            context,
            result or {"document_context": context.to_dict()},
            source_artifact=source_artifact,
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
            item.source_artifact = None
            item.protected_artifact = None
            item.protected_artifact_filename = None
            item.protected_artifact_media_type = None
            item.error = None
            item.warnings = ()
            item.review_status = "PENDING"
            item.stage_results.pop(JourneyStage.UNDERSTAND, None)
            item.stage_errors.pop(JourneyStage.UNDERSTAND, None)
            for stage in PUBLIC_JOURNEY_STAGES[1:]:
                item.stage_results.pop(stage, None)
                item.stage_errors.pop(stage, None)
                if item.stage_status[stage] is not StageStatus.NOT_STARTED:
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
        source_artifact: bytes | None = None,
    ) -> JourneyDocument:
        with self._lock:
            run = self._get_batch_run_locked(run_id)
            item = self._find_document(run, document_id)
            self._complete_item(
                item,
                document,
                context,
                result,
                source_artifact=source_artifact,
            )
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
        protect_eligible = [
            item for item in documents if self._protect_eligibility(item)[0]
        ]
        protect_submitted = sum(
            any(
                event["stage"] == JourneyStage.PROTECT.value
                and event["status"] == StageStatus.PROCESSING.value
                for event in item.stage_history
            )
            for item in documents
        )
        protect_terminal = sum(
            item.stage_status[JourneyStage.PROTECT] in TERMINAL_PROTECT_STATUSES
            for item in protect_eligible
        )
        protect_results = sum(
            JourneyStage.PROTECT in item.stage_results for item in documents
        )
        understand_terminal = bool(documents) and all(
            status in TERMINAL_UNDERSTAND_STATUSES for status in understand_statuses
        )
        protect_not_started = [
            item
            for item in protect_eligible
            if item.stage_status[JourneyStage.PROTECT] is StageStatus.NOT_STARTED
        ]
        protect_available = understand_terminal and bool(protect_not_started)
        if protect_available:
            protect_reason = None
        elif not documents:
            protect_reason = "Add and understand at least one report first."
        elif not understand_terminal:
            protect_reason = "UNDERSTAND must reach a terminal state for every report first."
        elif protect_eligible and protect_terminal == len(protect_eligible):
            protect_reason = "Privacy Protection has reached a terminal state for every eligible report."
        else:
            protect_reason = "No retained report is currently eligible for Privacy Protection."
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
            "protection_summary": {
                "eligible": len(protect_eligible),
                "submitted": protect_submitted,
                "terminal": protect_terminal,
                "results_stored": protect_results,
                "complete": sum(
                    item.stage_status[JourneyStage.PROTECT] is StageStatus.COMPLETE
                    for item in documents
                ),
                "needs_review": sum(
                    item.stage_status[JourneyStage.PROTECT]
                    is StageStatus.NEEDS_REVIEW
                    for item in documents
                ),
                "failed": sum(
                    item.stage_status[JourneyStage.PROTECT] is StageStatus.FAILED
                    for item in documents
                ),
                "blocked": sum(
                    item.stage_status[JourneyStage.PROTECT] is StageStatus.BLOCKED
                    for item in documents
                ),
            },
            "stage_summary": status_counts,
            "handoff": {
                "protect": {
                    "available": protect_available,
                    "document_count": len(documents),
                    "eligible_count": len(protect_eligible),
                    "eligible_document_ids": [
                        item.document_id for item in protect_not_started
                    ],
                    "reason": protect_reason,
                }
            },
        }

    def protect_run(
        self,
        run_id: str,
        policy: PolicyProfile,
        service: DeidentificationService,
        *,
        document_ids: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Run the accepted privacy service independently for eligible reports."""

        if not isinstance(policy, PolicyProfile):
            raise TypeError("policy must be a PolicyProfile.")

        with self._lock:
            run = self._get_run_locked(run_id)
            ordered = sorted(run.documents, key=lambda value: value.order)
            if document_ids is not None:
                if not document_ids:
                    raise ValueError("document_ids cannot be empty when supplied.")
                if len(set(document_ids)) != len(document_ids):
                    raise ValueError("document_ids cannot contain duplicates.")
                known = {item.document_id: item for item in ordered}
                missing = [document_id for document_id in document_ids if document_id not in known]
                if missing:
                    raise LookupError("Journey document was not found in this run.")
                selected = [known[document_id] for document_id in document_ids]
            else:
                selected = ordered

            queued: list[str] = []
            run.current_stage = JourneyStage.PROTECT
            for item in selected:
                current = item.stage_status[JourneyStage.PROTECT]
                if current in TERMINAL_PROTECT_STATUSES:
                    continue
                eligible, reason = self._protect_eligibility(item)
                if not eligible:
                    if current is not StageStatus.BLOCKED:
                        item.transition(JourneyStage.PROTECT, StageStatus.BLOCKED)
                    item.stage_errors[JourneyStage.PROTECT] = reason
                    continue
                item.stage_errors.pop(JourneyStage.PROTECT, None)
                item.transition(JourneyStage.PROTECT, StageStatus.QUEUED)
                queued.append(item.document_id)
            self._touch_locked(run)

        raw_responses: dict[str, Any] = {}
        for document_id in queued:
            with self._lock:
                run = self._get_run_locked(run_id)
                item = self._find_document(run, document_id)
                if item.document is None:
                    item.transition(JourneyStage.PROTECT, StageStatus.BLOCKED)
                    item.stage_errors[JourneyStage.PROTECT] = (
                        "The retained source document is unavailable."
                    )
                    self._touch_locked(run)
                    continue
                item.transition(JourneyStage.PROTECT, StageStatus.PROCESSING)
                source_text = item.document.text
                source_type = item.source_type.lower()
                source_filename = item.original_filename
                self._touch_locked(run)

            try:
                response = service.process(source_text, policy=policy)
                if not response.success:
                    raise RuntimeError("The privacy service did not return a valid result.")
                generated_pdf = None
                artifact = None
                if source_type == "pdf":
                    generated_pdf = protected_document_builder.build_pdf(
                        source_filename=source_filename,
                        protected_text=response.data.deidentified_text,
                    )
                    artifact = ProtectedArtifact(
                        filename=generated_pdf.filename,
                        media_type=generated_pdf.media_type,
                        availability=True,
                        page_count=generated_pdf.page_count,
                        generated_at=generated_pdf.generated_at,
                        integrity_sha256=generated_pdf.integrity_sha256,
                        provenance=generated_pdf.provenance,
                    )
                output = build_protect_output(
                    report_id=document_id,
                    response=response,
                    policy=policy,
                    artifact=artifact,
                )
            except Exception:
                with self._lock:
                    run = self._get_run_locked(run_id)
                    item = self._find_document(run, document_id)
                    item.transition(JourneyStage.PROTECT, StageStatus.FAILED)
                    item.stage_errors[JourneyStage.PROTECT] = (
                        "Privacy Protection could not process this report."
                    )
                    item.error = item.stage_errors[JourneyStage.PROTECT]
                    item.review_status = "FAILED"
                    self._block_after(item, JourneyStage.PROTECT)
                    self._touch_locked(run)
                continue

            with self._lock:
                run = self._get_run_locked(run_id)
                item = self._find_document(run, document_id)
                serialized = output.to_dict()
                item.stage_results[JourneyStage.PROTECT] = serialized
                protection_blocked = output.protection_result.status == "BLOCKED"
                extract_input_safe = self._protected_input_safe(
                    output, item.source_type
                )
                item.protected_artifact = (
                    generated_pdf.content
                    if generated_pdf and not protection_blocked
                    else None
                )
                item.protected_artifact_filename = (
                    generated_pdf.filename
                    if generated_pdf and not protection_blocked
                    else None
                )
                item.protected_artifact_media_type = (
                    generated_pdf.media_type
                    if generated_pdf and not protection_blocked
                    else None
                )
                item.stage_errors.pop(JourneyStage.PROTECT, None)
                item.error = None
                if protection_blocked:
                    item.review_status = "BLOCKED"
                    item.stage_errors[JourneyStage.PROTECT] = (
                        "Protection is incomplete because a known high-risk "
                        "identity field remains unprotected."
                    )
                    item.transition(JourneyStage.PROTECT, StageStatus.BLOCKED)
                    self._block_after(item, JourneyStage.PROTECT)
                elif output.protection_result.review_required:
                    item.review_status = "NEEDS_REVIEW"
                    item.transition(JourneyStage.PROTECT, StageStatus.NEEDS_REVIEW)
                    if not extract_input_safe:
                        self._block_after(item, JourneyStage.PROTECT)
                else:
                    item.review_status = "CLEAR"
                    item.transition(JourneyStage.PROTECT, StageStatus.COMPLETE)
                    if not extract_input_safe:
                        self._block_after(item, JourneyStage.PROTECT)
                self._touch_locked(run)
            raw_responses[document_id] = response

        return raw_responses

    def protect(
        self,
        journey_id: str,
        policy: PolicyProfile,
        service: DeidentificationService,
    ):
        """Preserve the accepted standalone /privacy compatibility handoff."""

        return service.process(self.get(journey_id).document.text, policy=policy)

    def source_text_for_compare(self, run_id: str, document_id: str) -> str:
        """Return retained source text only for an explicit post-PROTECT review."""

        with self._lock:
            run = self._get_run_locked(run_id)
            item = self._find_document(run, document_id)
            if (
                item.stage_status[JourneyStage.PROTECT]
                not in {StageStatus.COMPLETE, StageStatus.NEEDS_REVIEW}
                or JourneyStage.PROTECT not in item.stage_results
            ):
                raise ValueError(
                    "Original comparison is available only after Privacy Protection completes."
                )
            if item.document is None:
                raise LookupError("The retained source document is unavailable.")
            self._touch_locked(run)
            return item.document.text

    def protected_artifact_for_view(
        self, run_id: str, document_id: str
    ) -> EphemeralDocumentArtifact:
        """Return a generated artifact without placing its bytes in run JSON."""

        with self._lock:
            run = self._get_run_locked(run_id)
            item = self._find_document(run, document_id)
            if (
                item.stage_status[JourneyStage.PROTECT]
                not in {StageStatus.COMPLETE, StageStatus.NEEDS_REVIEW}
                or JourneyStage.PROTECT not in item.stage_results
            ):
                raise ValueError(
                    "The protected document is available only after Privacy Protection completes."
                )
            if (
                item.protected_artifact is None
                or item.protected_artifact_filename is None
                or item.protected_artifact_media_type is None
            ):
                raise LookupError("No protected PDF artifact is available for this report.")
            self._touch_locked(run)
            return EphemeralDocumentArtifact(
                filename=item.protected_artifact_filename,
                media_type=item.protected_artifact_media_type,
                content=item.protected_artifact,
            )

    def source_artifact_for_compare(
        self, run_id: str, document_id: str
    ) -> EphemeralDocumentArtifact:
        """Return the original PDF only after an explicit post-PROTECT action."""

        with self._lock:
            run = self._get_run_locked(run_id)
            item = self._find_document(run, document_id)
            if (
                item.stage_status[JourneyStage.PROTECT]
                not in {StageStatus.COMPLETE, StageStatus.NEEDS_REVIEW}
                or JourneyStage.PROTECT not in item.stage_results
            ):
                raise ValueError(
                    "Original comparison is available only after Privacy Protection completes."
                )
            if item.source_type.lower() != "pdf" or item.source_artifact is None:
                raise LookupError("No original PDF artifact is available for this report.")
            self._touch_locked(run)
            return EphemeralDocumentArtifact(
                filename=item.original_filename,
                media_type="application/pdf",
                content=item.source_artifact,
            )

    def _complete_item(
        self,
        item: JourneyDocument,
        document: DocumentContent,
        context: MedNexusDocumentContext,
        result: dict[str, Any],
        *,
        source_artifact: bytes | None = None,
    ) -> None:
        item.document = document
        item.context = context
        item.source_artifact = (
            bytes(source_artifact)
            if source_artifact is not None and item.source_type.lower() == "pdf"
            else None
        )
        item.stage_results[JourneyStage.UNDERSTAND] = result
        item.warnings = tuple(result.get("warnings", ()))
        item.error = None
        item.stage_errors.pop(JourneyStage.UNDERSTAND, None)
        review_required = context.processing_context.document_review_required
        if review_required:
            item.review_status = "NEEDS_REVIEW"
            item.transition(JourneyStage.UNDERSTAND, StageStatus.NEEDS_REVIEW)
            self._block_downstream(
                item,
                allow_protect=context.processing_context.protect_ready,
            )
        else:
            item.review_status = "CLEAR"
            item.transition(JourneyStage.UNDERSTAND, StageStatus.COMPLETE)

    def _fail_item(self, item: JourneyDocument, error: str) -> None:
        item.error = error
        item.stage_errors[JourneyStage.UNDERSTAND] = error
        item.review_status = "FAILED"
        item.transition(JourneyStage.UNDERSTAND, StageStatus.FAILED)
        self._block_downstream(item)

    @staticmethod
    def _block_downstream(
        item: JourneyDocument,
        *,
        allow_protect: bool = False,
    ) -> None:
        for stage in PUBLIC_JOURNEY_STAGES[1:]:
            if stage is JourneyStage.PROTECT and allow_protect:
                continue
            if item.stage_status[stage] is StageStatus.NOT_STARTED:
                item.stage_status[stage] = StageStatus.BLOCKED
                item.stage_errors[stage] = (
                    "Blocked because UNDERSTAND did not produce a safe downstream handoff."
                )
                item.stage_history.append(
                    {"stage": stage.value, "status": StageStatus.BLOCKED.value, "at": _timestamp()}
                )

    @staticmethod
    def _block_after(item: JourneyDocument, completed_stage: JourneyStage) -> None:
        start = PUBLIC_JOURNEY_STAGES.index(completed_stage) + 1
        for stage in PUBLIC_JOURNEY_STAGES[start:]:
            if item.stage_status[stage] is StageStatus.NOT_STARTED:
                item.stage_status[stage] = StageStatus.BLOCKED
                item.stage_errors[stage] = (
                    f"Blocked because {completed_stage.value} requires review or failed."
                )
                item.stage_history.append(
                    {
                        "stage": stage.value,
                        "status": StageStatus.BLOCKED.value,
                        "at": _timestamp(),
                    }
                )

    @staticmethod
    def _protected_input_safe(output: Any, source_type: str) -> bool:
        """Assess only privacy-safe input availability, not EXTRACT profile readiness."""

        if output.protection_result.status not in {"COMPLETE", "NEEDS_REVIEW"}:
            return False
        if not output.protected_document.protected_text.strip():
            return False
        if source_type.lower() == "pdf":
            artifact = output.protected_document.artifact
            return bool(
                artifact
                and artifact.availability
                and artifact.media_type == "application/pdf"
                and artifact.integrity_sha256
            )
        return True

    @staticmethod
    def _protect_eligibility(item: JourneyDocument) -> tuple[bool, str]:
        if item.document is None or item.context is None:
            return False, "The retained source document or context is unavailable."
        if JourneyStage.UNDERSTAND not in item.stage_results:
            return False, "UNDERSTAND did not produce a valid document context."
        if not item.context.processing_context.protect_ready:
            return False, "The UNDERSTAND context does not permit Privacy Protection."
        if item.stage_status[JourneyStage.UNDERSTAND] not in {
            StageStatus.COMPLETE,
            StageStatus.NEEDS_REVIEW,
        }:
            return False, "UNDERSTAND has not produced an eligible terminal result."
        return True, ""

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
        run = self._get_run_locked(run_id)
        if run.mode is not JourneyMode.BATCH:
            raise ValueError("This operation requires a batch journey run.")
        return run

    def _get_run_locked(self, run_id: str) -> JourneyRun:
        self._cleanup_locked()
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise LookupError("Journey run was not found or has expired.") from exc

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
