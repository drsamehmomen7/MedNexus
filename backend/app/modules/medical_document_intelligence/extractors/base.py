from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)


class BaseDocumentExtractor(ABC):
    """
    Base class for every MedNexus document extractor.

    Each extractor is responsible only for reading its own file type
    and converting it into the common immutable DocumentContent
    contract.

    No de-identification, NLP, policy application, or document
    understanding should occur inside extractors.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> tuple[str, ...]:
        """
        Supported file extensions.

        Example:
            (".txt",)

            (".docx",)

            (".pdf",)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def media_type(self) -> str:
        """
        MIME media type produced by this extractor.

        Example:
            text/plain
            application/pdf
        """
        raise NotImplementedError

    def supports(self, path: str | Path) -> bool:
        """
        Return True if this extractor supports the given file.
        """

        suffix = Path(path).suffix.lower()

        return suffix in {
            ext.lower()
            for ext in self.supported_extensions
        }

    @abstractmethod
    def extract(
        self,
        path: str | Path,
    ) -> DocumentContent:
        """
        Read a document and return a DocumentContent contract.
        """
        raise NotImplementedError