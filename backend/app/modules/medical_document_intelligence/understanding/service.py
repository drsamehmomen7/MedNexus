from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from backend.app.modules.medical_document_intelligence.contracts.document_content import DocumentContent
from backend.app.modules.medical_document_intelligence.extractors.bootstrap import build_default_registry
from backend.app.modules.medical_document_intelligence.extractors.factory import ExtractorFactory

from .document_classifier import DocumentClassifier
from .context_builder import DocumentContextBuilder
from .context_models import MedNexusDocumentContext
from .language_detector import LanguageDetector
from .knowledge.radiology import RadiologyReasoner
from .models import DocumentUnderstandingResult, RadiologySubdomain
from .routing import UnderstandingRouter
from .section_detector import SectionDetector


class DocumentUnderstandingService:
    """Standalone MedNexus-owned UNDERSTAND orchestrator."""

    def __init__(self, factory: ExtractorFactory | None = None) -> None:
        if factory is not None and not isinstance(factory, ExtractorFactory):
            raise TypeError("factory must be an ExtractorFactory or None.")
        self._factory = factory or ExtractorFactory(build_default_registry())

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return self._factory.registry.supported_extensions

    def supports(self, path: str | Path) -> bool:
        return self._factory.supports(path)

    def analyze_text(self, text: str, *, metadata: dict[str, Any] | None = None, warnings=()) -> DocumentUnderstandingResult:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        if metadata is not None and not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary or None.")
        sections = SectionDetector.detect(text)
        radiology_decision = RadiologyReasoner.assess(text, sections)
        classification = DocumentClassifier.classify(
            text, sections, radiology_decision=radiology_decision
        )
        result_warnings = list(warnings)
        if not text.strip():
            result_warnings.append("Document contains no meaningful text for understanding.")
        routing = UnderstandingRouter.route(
            classification.document_type, classification.confidence_band
        )
        if (
            classification.radiology_decision is not None
            and classification.radiology_decision.subdomain is RadiologySubdomain.OTHER
        ):
            routing = replace(routing, manual_review_required=True)
        return DocumentUnderstandingResult(
            classification.domain,
            classification.document_type,
            classification.document_subtype,
            LanguageDetector.detect(text),
            sections,
            classification.confidence,
            classification.confidence_band,
            classification.evidence,
            routing,
            dict(metadata or {}),
            tuple(result_warnings),
            classification.document_nature,
            classification.explanations,
            classification.radiology_decision,
        )

    def analyze_document(self, document: DocumentContent) -> DocumentUnderstandingResult:
        if not isinstance(document, DocumentContent):
            raise TypeError("document must be a DocumentContent instance.")
        metadata = {
            "source_name": document.source_name, "media_type": document.media_type,
            "extension": document.extension, "file_size": document.file_size,
            "page_count": document.page_count, "line_count": document.line_count,
            "extraction_metadata": dict(document.metadata),
        }
        return self.analyze_text(document.text, metadata=metadata, warnings=document.warnings)

    def build_context(
        self, document: DocumentContent, result: DocumentUnderstandingResult | None = None
    ) -> MedNexusDocumentContext:
        if not isinstance(document, DocumentContent):
            raise TypeError("document must be a DocumentContent instance.")
        return DocumentContextBuilder.build(result or self.analyze_document(document), document)

    @staticmethod
    def text_document(text: str) -> DocumentContent:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        return DocumentContent(text, "pasted-text.txt", "text/plain", ".txt", len(text.encode("utf-8")), encoding="utf-8")

    def extract_file(self, path: str | Path) -> DocumentContent:
        return self._factory.resolve(path).extract(path)

    def analyze_file(self, path: str | Path) -> DocumentUnderstandingResult:
        return self.analyze_document(self.extract_file(path))
