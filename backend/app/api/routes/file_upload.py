from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)
from backend.app.modules.medical_document_intelligence.services.file_processing_service import (
    FileProcessingService,
)


router = APIRouter(
    prefix="/api/v1/document",
    tags=["Medical Document Intelligence"],
)

service = FileProcessingService()


@router.post("/deidentify/file")
async def deidentify_file(
    file: UploadFile = File(...),
    policy: str = Form("mednexus_default"),
) -> dict[str, Any]:
    """
    Upload and de-identify a supported medical document.

    Supported formats:
        - TXT
        - DOCX
        - Text-based PDF

    Scanned and image-based PDF files are detected but are not processed
    through OCR in the current stage.
    """

    original_filename = (
        Path(file.filename).name
        if file.filename
        else ""
    )

    if not original_filename:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file must have a filename.",
        )

    suffix = Path(original_filename).suffix.lower()

    if not suffix:
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file must have a supported "
                "file extension."
            ),
        )

    try:
        selected_policy = PolicyProfile(policy)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported policy: {policy}",
        ) from exc

    if not service.supports(original_filename):
        supported_extensions = ", ".join(
            service.supported_extensions
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported document extension '{suffix}'. "
                f"Supported extensions: {supported_extensions}."
            ),
        )

    temporary_path: Path | None = None

    try:
        uploaded_content = await file.read()

        if not uploaded_content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=suffix,
        ) as temporary_file:
            temporary_file.write(uploaded_content)
            temporary_path = Path(
                temporary_file.name
            )

        response = service.process(
            path=temporary_path,
            policy=selected_policy,
        )

        document_metadata = dict(
            response.metadata.get(
                "document",
                {},
            )
        )

        # The extractor processes a temporary server file. Restore the
        # real client filename before returning public API metadata.
        document_metadata[
            "source_name"
        ] = original_filename

        response.metadata[
            "document"
        ] = document_metadata

        context_entities = [
            {
                "text": detected.value,
                "entity_type": detected.entity.value,
                "start": detected.start,
                "end": detected.end,
                "source": detected.source,
                "confidence": detected.confidence,
                "label": detected.label,
                "normalized_label": detected.normalized_label,
            }
            for detected in response.context_entities
        ]

        result = response.data

        return {
            "success": response.success,
            "message": response.message,
            "error": response.error,
            "module": response.module_name,
            "task": "File De-identification",
            "engine": {
                "name": response.engine_name,
                "version": response.engine_version,
            },
            "processing_time": response.processing_time,
            "warnings": response.warnings,
            "metadata": response.metadata,
            "context_entities": context_entities,
            "result": {
                "original_text": result.original_text,
                "deidentified_text": result.deidentified_text,
                "entities": result.pii_entities,
                "mapping": result.mapping,
            },
        }

    except HTTPException:
        raise

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except LookupError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred while processing "
                "the uploaded document."
            ),
        ) from exc

    finally:
        await file.close()

        if temporary_path is not None:
            try:
                temporary_path.unlink(
                    missing_ok=True,
                )
            except OSError:
                pass