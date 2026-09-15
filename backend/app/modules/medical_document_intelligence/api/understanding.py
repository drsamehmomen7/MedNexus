from __future__ import annotations

import hashlib
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.app.modules.medical_document_intelligence.policies.policy_profiles import resolve_policy_profile
from backend.app.modules.medical_document_intelligence.services.deidentification import DeidentificationService
from backend.app.modules.medical_document_intelligence.understanding.journey import (
    JourneyMode,
    JourneyStage,
    StageStatus,
    journey_store,
)
from backend.app.modules.medical_document_intelligence.understanding.service import (
    DocumentUnderstandingService,
)


router = APIRouter(
    prefix="/api/v1/understanding",
    tags=["Medical Document Understanding"],
)
service = DocumentUnderstandingService()
privacy_service = DeidentificationService()


class UnderstandingTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Extracted healthcare document text.")


class JourneyProtectRequest(BaseModel):
    policy: str = "mednexus_clinical"


class JourneyRunRequest(BaseModel):
    mode: str = Field("batch", description="Journey operating mode: single or batch.")


def _result_payload(document, result, context, journey: dict[str, Any]) -> dict[str, Any]:
    payload = result.to_dict()
    payload["document_context"] = context.to_dict()
    payload["journey"] = journey
    payload["metadata"]["source_name"] = document.source_name
    return payload


def _journey_payload(document, result) -> dict[str, Any]:
    context = service.build_context(document, result)
    journey_id = context.document.document_id
    payload = _result_payload(
        document,
        result,
        context,
        {
            "journey_id": journey_id,
            "run_id": journey_id,
            "mode": "single",
            "continue_to_protect": f"/privacy?journey_id={journey_id}#workspace",
        },
    )
    journey_store.retain(document, context, payload)
    return payload


def _batch_result_payload(document, result, run_id: str, document_id: str) -> tuple[dict[str, Any], Any]:
    context = service.build_context(document, result, document_id=document_id)
    payload = _result_payload(
        document,
        result,
        context,
        {
            "journey_id": None,
            "run_id": run_id,
            "document_id": document_id,
            "mode": "batch",
            "continue_to_protect": None,
        },
    )
    return payload, context


def _upload_identity(file: UploadFile) -> tuple[str, str]:
    original_filename = Path(file.filename).name if file.filename else ""
    if not original_filename:
        raise HTTPException(status_code=400, detail="The uploaded file must have a filename.")
    suffix = Path(original_filename).suffix.lower()
    if not suffix:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must have a supported file extension.",
        )
    return original_filename, suffix


def _validate_supported(original_filename: str, suffix: str) -> None:
    if service.supports(original_filename):
        return
    supported = ", ".join(service.supported_extensions)
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported document extension '{suffix}'. Supported extensions: {supported}.",
    )


def _extract_uploaded_content(original_filename: str, suffix: str, content: bytes):
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        return replace(service.extract_file(temporary_path), source_name=original_filename)
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _known_upload_error(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return str(exc.detail)
    if isinstance(exc, (FileNotFoundError, LookupError, ValueError)):
        return str(exc)
    return "MRJ could not understand this report because document processing failed."


@router.post("/analyze-text")
def analyze_text(request: UnderstandingTextRequest) -> dict[str, Any]:
    document = service.text_document(request.text)
    return _journey_payload(document, service.analyze_document(document))


@router.post("/analyze-file")
async def analyze_file(file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        original_filename, suffix = _upload_identity(file)
        _validate_supported(original_filename, suffix)
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        document = _extract_uploaded_content(original_filename, suffix, content)
        return _journey_payload(document, service.analyze_document(document))
    except HTTPException:
        raise
    except (FileNotFoundError, LookupError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while understanding the uploaded document.",
        ) from exc
    finally:
        await file.close()


@router.post("/journey-runs")
def create_journey_run(request: JourneyRunRequest) -> dict[str, Any]:
    try:
        mode = JourneyMode(request.mode.upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Journey mode must be 'single' or 'batch'."
        ) from exc
    run = journey_store.create_run(mode)
    return journey_store.run_payload(run.run_id)


async def _process_batch_upload(
    run_id: str,
    file: UploadFile,
    order: int,
    *,
    retry_document_id: str | None = None,
) -> dict[str, Any]:
    content = b""
    item = None
    try:
        original_filename, suffix = _upload_identity(file)
        content = await file.read()
        digest = hashlib.sha256(content).hexdigest() if content else None
        if retry_document_id is None:
            item = journey_store.begin_document(
                run_id,
                original_filename=original_filename,
                order=order,
                source_type=suffix.lstrip("."),
                content_digest=digest,
            )
        else:
            item = journey_store.retry_document(
                run_id,
                retry_document_id,
                original_filename=original_filename,
                source_type=suffix.lstrip("."),
                content_digest=digest,
            )
        if item.stage_status[JourneyStage.UNDERSTAND] is StageStatus.FAILED:
            return journey_store.run_payload(run_id)
        _validate_supported(original_filename, suffix)
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        document = _extract_uploaded_content(original_filename, suffix, content)
        result = service.analyze_document(document)
        payload, context = _batch_result_payload(document, result, run_id, item.document_id)
        journey_store.complete_document(
            run_id,
            item.document_id,
            document=document,
            context=context,
            result=payload,
        )
    except (LookupError, ValueError) as exc:
        if item is None:
            raise
        journey_store.fail_document(run_id, item.document_id, _known_upload_error(exc))
    except Exception as exc:
        if item is None:
            raise
        journey_store.fail_document(run_id, item.document_id, _known_upload_error(exc))
    finally:
        content = b""
        await file.close()
    return journey_store.run_payload(run_id)


@router.post("/journey-runs/{run_id}/documents")
async def analyze_batch_document(
    run_id: str,
    order: int = Form(..., ge=0),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    try:
        return await _process_batch_upload(run_id, file, order)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/journey-runs/{run_id}/documents/{document_id}/retry")
async def retry_batch_document(
    run_id: str,
    document_id: str,
    file: UploadFile = File(...),
) -> dict[str, Any]:
    try:
        run = journey_store.get_run(run_id)
        existing = next(
            (item for item in run.documents if item.document_id == document_id), None
        )
        if existing is None:
            raise LookupError("Journey document was not found in this run.")
        return await _process_batch_upload(
            run_id,
            file,
            existing.order,
            retry_document_id=document_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/journey-runs/{run_id}")
def get_journey_run(run_id: str) -> dict[str, Any]:
    try:
        return journey_store.run_payload(run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/journeys/{journey_id}")
def get_journey(journey_id: str) -> dict[str, Any]:
    try:
        record = journey_store.get(journey_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"journey_id": journey_id, "document_context": record.context.to_dict()}


@router.post("/journeys/{journey_id}/protect")
def protect_journey(journey_id: str, request: JourneyProtectRequest):
    try:
        policy = resolve_policy_profile(request.policy)
        response = journey_store.protect(journey_id, policy, privacy_service)
        response.metadata["document_context"] = journey_store.get(journey_id).context.to_dict()
        response.metadata["journey_id"] = journey_id
        return response
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
