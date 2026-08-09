import time

from backend.app.modules.medical_document_intelligence.schemas.processing_response import (
    ProcessingResponse,
)


class BaseService:
    """
    Base class for all MedNexus services.
    """

    def start_timer(self):
        return time.perf_counter()

    def stop_timer(self, start_time: float) -> float:
        return time.perf_counter() - start_time

    def create_response(self, **kwargs) -> ProcessingResponse:
        return ProcessingResponse(**kwargs)