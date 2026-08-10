from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
)
from backend.app.modules.medical_document_intelligence.extractors.bootstrap import (
    build_default_registry,
)
from backend.app.modules.medical_document_intelligence.extractors.factory import (
    ExtractorFactory,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)
from backend.app.modules.medical_document_intelligence.services.deidentification import (
    DeidentificationService,
)


class FileProcessingService:
    """
    Orchestrate end-to-end medical document file processing.

    The service connects the MedNexus document extraction layer with
    the existing text de-identification pipeline.

    Processing flow:

        Source File
            |
            v
        ExtractorFactory
            |
            v
        Concrete Document Extractor
            |
            v
        DocumentContent
            |
            v
        DeidentificationService
            |
            v
        ProcessingResponse

    Responsibilities:
        - Resolve the appropriate extractor for the source file.
        - Extract document text and source metadata.
        - Pass extracted text to DeidentificationService.
        - Preserve extraction metadata inside the processing response.
        - Expose supported file extensions.

    Responsibilities not included:
        - FastAPI request handling.
        - Temporary upload-file management.
        - File persistence.
        - Malware scanning.
        - OCR.
        - Document classification.
        - Clinical information extraction.
        - Terminology normalization.
        - Output file generation.
    """

    def __init__(
        self,
        *,
        factory: ExtractorFactory | None = None,
        deidentification_service: DeidentificationService | None = None,
    ) -> None:
        """
        Initialize the file-processing service.

        Args:
            factory:
                Optional ExtractorFactory dependency.

                When omitted, MedNexus creates a default factory backed
                by the production extractor registry containing TXT,
                DOCX, and PDF extractors.

            deidentification_service:
                Optional DeidentificationService dependency.

                Dependency injection allows isolated testing without
                loading the real AI engine.
        """

        if factory is not None and not isinstance(
            factory,
            ExtractorFactory,
        ):
            raise TypeError(
                "factory must be an instance of ExtractorFactory "
                "or None."
            )

        if (
            deidentification_service is not None
            and not isinstance(
                deidentification_service,
                DeidentificationService,
            )
        ):
            raise TypeError(
                "deidentification_service must be an instance of "
                "DeidentificationService or None."
            )

        if factory is None:
            registry = build_default_registry()
            factory = ExtractorFactory(
                registry
            )

        if deidentification_service is None:
            deidentification_service = DeidentificationService()

        self._factory = factory
        self._deidentification_service = (
            deidentification_service
        )

    @property
    def factory(self) -> ExtractorFactory:
        """
        Return the ExtractorFactory used by this service.
        """

        return self._factory

    @property
    def deidentification_service(
        self,
    ) -> DeidentificationService:
        """
        Return the DeidentificationService used by this service.
        """

        return self._deidentification_service

    @property
    def supported_extensions(
        self,
    ) -> tuple[str, ...]:
        """
        Return all file extensions supported by the active registry.
        """

        return self._factory.registry.supported_extensions

    def supports(
        self,
        path: str | Path,
    ) -> bool:
        """
        Return True when the supplied file path is supported.

        The physical file does not need to exist for this check.
        """

        return self._factory.supports(
            path
        )

    def extract(
        self,
        path: str | Path,
    ) -> DocumentContent:
        """
        Extract a file into the unified DocumentContent contract.

        This method performs extraction only. It does not invoke the
        de-identification pipeline.

        Args:
            path:
                Path to a supported source document.

        Returns:
            Extracted DocumentContent.

        Raises:
            TypeError:
                If path is not a string or pathlib.Path.

            ValueError:
                If path is empty, has no extension, or the concrete
                extractor rejects the file.

            LookupError:
                If the document extension is unsupported.

            FileNotFoundError:
                If the source file does not exist.
        """

        extractor = self._factory.resolve(
            path
        )

        self._validate_extractor(
            extractor
        )

        document_content = extractor.extract(
            path
        )

        self._validate_document_content(
            document_content
        )

        return document_content

    def process(
        self,
        path: str | Path,
        policy: PolicyProfile = PolicyProfile.MEDNEXUS_CLINICAL,
    ):
        """
        Extract and de-identify a medical document.

        Args:
            path:
                Path to a TXT, DOCX, or text-based PDF document.

            policy:
                MedNexus privacy policy applied to the extracted text.

        Returns:
            The ProcessingResponse created by DeidentificationService,
            enriched with document-extraction metadata.

        Raises:
            TypeError:
                If policy is not a PolicyProfile.

            LookupError:
                If the document extension is unsupported.

            FileNotFoundError:
                If the source file does not exist.

            ValueError:
                If the file cannot be extracted or contains no
                meaningful extractable text.
        """

        if not isinstance(
            policy,
            PolicyProfile,
        ):
            raise TypeError(
                "policy must be an instance of PolicyProfile."
            )

        document_content = self.extract(
            path
        )

        if document_content.is_empty:
            raise ValueError(
                "The document contains no meaningful extractable "
                "text and cannot be sent to the de-identification "
                "pipeline."
            )

        response = self._deidentification_service.process(
            text=document_content.text,
            policy=policy,
        )

        self._attach_document_metadata(
            response=response,
            document_content=document_content,
        )

        return response

    @staticmethod
    def _validate_extractor(
        extractor: BaseDocumentExtractor,
    ) -> None:
        """
        Validate the extractor returned by the factory.
        """

        if not isinstance(
            extractor,
            BaseDocumentExtractor,
        ):
            raise TypeError(
                "ExtractorFactory returned an invalid extractor."
            )

    @staticmethod
    def _validate_document_content(
        document_content: DocumentContent,
    ) -> None:
        """
        Validate the output contract returned by an extractor.
        """

        if not isinstance(
            document_content,
            DocumentContent,
        ):
            raise TypeError(
                "Document extractor must return DocumentContent."
            )

    @staticmethod
    def _attach_document_metadata(
        *,
        response: Any,
        document_content: DocumentContent,
    ) -> None:
        """
        Attach source-document and extraction metadata to the response.

        The existing DeidentificationService response remains the
        canonical processing response. This method enriches its metadata
        without exposing extractor-specific logic to the API layer.
        """

        if not hasattr(
            response,
            "metadata",
        ):
            raise TypeError(
                "DeidentificationService returned a response without "
                "metadata."
            )

        if response.metadata is None:
            response.metadata = {}

        if not isinstance(
            response.metadata,
            dict,
        ):
            raise TypeError(
                "Processing response metadata must be a dictionary."
            )

        document_metadata: Dict[str, Any] = {
            "source_name": document_content.source_name,
            "media_type": document_content.media_type,
            "extension": document_content.extension,
            "file_size": document_content.file_size,
            "encoding": document_content.encoding,
            "page_count": document_content.page_count,
            "line_count": document_content.line_count,
            "character_count": document_content.character_count,
            "is_empty": document_content.is_empty,
            "has_warnings": document_content.has_warnings,
            "warnings": document_content.warnings,
            "extraction_metadata": dict(
                document_content.metadata
            ),
        }

        response.metadata[
            "document"
        ] = document_metadata
