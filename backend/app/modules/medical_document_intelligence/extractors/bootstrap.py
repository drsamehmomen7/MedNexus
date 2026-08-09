from __future__ import annotations

from backend.app.modules.medical_document_intelligence.extractors.docx import (
    DocxDocumentExtractor,
)
from backend.app.modules.medical_document_intelligence.extractors.pdf import (
    PdfDocumentExtractor,
)
from backend.app.modules.medical_document_intelligence.extractors.registry import (
    ExtractorRegistry,
)
from backend.app.modules.medical_document_intelligence.extractors.txt import (
    TxtDocumentExtractor,
)


def build_default_registry() -> ExtractorRegistry:
    """
    Build the default MedNexus document extractor registry.

    The returned registry is pre-populated with all production-ready
    document extractors currently shipped with MedNexus.

    Current default extractors:
        - TXT
        - DOCX
        - PDF

    Future extractors may include:
        - CSV
        - XLSX
        - OCR image formats
        - HL7 CDA
        - FHIR documents
        - DICOM Structured Reports

    Returns:
        A new ExtractorRegistry instance containing the default
        production extractors.

    Each call creates a new independent registry to avoid hidden global
    mutable state and to keep tests and future tenant configurations
    isolated.
    """

    return ExtractorRegistry(
        extractors=(
            TxtDocumentExtractor(),
            DocxDocumentExtractor(),
            PdfDocumentExtractor(),
        )
    )