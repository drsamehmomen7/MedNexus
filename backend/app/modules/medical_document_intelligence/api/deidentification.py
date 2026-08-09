from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.modules.medical_document_intelligence.services.deidentification import (
    DeidentificationService,
)


router = APIRouter(
    prefix="/api/v1/document",
    tags=["Medical Document Intelligence"],
)

service = DeidentificationService()


class DeidentificationRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        description="Medical text to be de-identified.",
    )


@router.post("/deidentify")
def deidentify_document(request: DeidentificationRequest):
    """
    De-identify medical text using the MedNexus processing pipeline.

    The API returns:

    - Processing status
    - Engine information
    - Detected healthcare context entities
    - Original and de-identified text
    - AI engine entities and mappings
    - Processing metadata
    """

    response = service.process(request.text)

    openmed_result = response.data

    context_entities = [
        {
            "text": detected_entity.value,
            "entity_type": detected_entity.entity.value,
            "start": detected_entity.start,
            "end": detected_entity.end,
            "source": detected_entity.source,
            "confidence": detected_entity.confidence,
            "label": detected_entity.label,
            "normalized_label": detected_entity.normalized_label,
        }
        for detected_entity in response.context_entities
    ]

    return {
        "success": response.success,
        "message": response.message,
        "error": response.error,
        "module": response.module_name,
        "task": "De-identification",
        "engine": {
            "name": response.engine_name,
            "version": response.engine_version,
        },
        "processing_time": response.processing_time,
        "warnings": response.warnings,
        "metadata": response.metadata,
        "context_entities": context_entities,
        "result": {
            "original_text": openmed_result.original_text,
            "deidentified_text": openmed_result.deidentified_text,
            "entities": openmed_result.pii_entities,
            "mapping": openmed_result.mapping,
        },
    }