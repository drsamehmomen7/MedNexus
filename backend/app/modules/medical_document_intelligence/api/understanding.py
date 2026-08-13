from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from backend.app.modules.medical_document_intelligence.understanding.service import (
    DocumentUnderstandingService,
)


router = APIRouter(
    prefix="/api/v1/understanding",
    tags=["Medical Document Understanding"],
)
service = DocumentUnderstandingService()


class UnderstandingTextRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Extracted healthcare document text.")


@router.post("/analyze-text")
def analyze_text(request: UnderstandingTextRequest) -> dict[str, Any]:
    return service.analyze_text(request.text).to_dict()


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
        payload = service.analyze_file(temporary_path).to_dict()
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
