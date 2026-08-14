from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.app.modules.medical_document_intelligence.understanding.service import (
    DocumentUnderstandingService,
)
from backend.app.modules.medical_document_intelligence.understanding.journey import journey_store
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import resolve_policy_profile
from backend.app.modules.medical_document_intelligence.services.deidentification import DeidentificationService


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


def _journey_payload(document, result) -> dict[str, Any]:
    context = service.build_context(document, result)
    journey_id = journey_store.retain(document, context)
    payload = result.to_dict()
    payload["document_context"] = context.to_dict()
    payload["journey"] = {"journey_id": journey_id, "continue_to_protect": f"/privacy?journey_id={journey_id}#workspace"}
    return payload


@router.post("/analyze-text")
def analyze_text(request: UnderstandingTextRequest) -> dict[str, Any]:
    document = service.text_document(request.text)
    return _journey_payload(document, service.analyze_document(document))


@router.post("/analyze-file")
async def analyze_file(file: UploadFile = File(...)) -> dict[str, Any]:
    original_filename = Path(file.filename).name if file.filename else ""
    if not original_filename:
        raise HTTPException(status_code=400, detail="The uploaded file must have a filename.")
    suffix = Path(original_filename).suffix.lower()
    if not suffix:
        raise HTTPException(status_code=400, detail="The uploaded file must have a supported file extension.")
    if not service.supports(original_filename):
        supported = ", ".join(service.supported_extensions)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document extension '{suffix}'. Supported extensions: {supported}.",
        )

    temporary_path: Path | None = None
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        document = replace(service.extract_file(temporary_path), source_name=original_filename)
        payload = _journey_payload(document, service.analyze_document(document))
        payload["metadata"]["source_name"] = original_filename
        return payload
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
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


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
