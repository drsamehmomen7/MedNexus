from __future__ import annotations

from pathlib import Path

from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
)
from backend.app.modules.medical_document_intelligence.extractors.registry import (
    ExtractorRegistry,
)


class ExtractorFactory:
    """
    Resolve the appropriate MedNexus document extractor for a file.

    The factory delegates extractor registration and extension mapping
    to ExtractorRegistry.

    Responsibilities:
        - Accept a source file path.
        - Validate that the path contains a usable file extension.
        - Resolve the matching extractor from the registry.
        - Provide clear errors for unsupported document formats.

    Responsibilities not included:
        - Reading or parsing the document.
        - Detecting MIME types from file content.
        - Applying de-identification.
        - Applying policies or clinical NLP.
        - Modifying the registry automatically.

    The factory remains independent of concrete extractors such as TXT,
    DOCX, or PDF. New extractors become available by registering them
    with the supplied ExtractorRegistry.
    """

    def __init__(
        self,
        registry: ExtractorRegistry,
    ) -> None:
        if not isinstance(registry, ExtractorRegistry):
            raise TypeError(
                "registry must be an instance of ExtractorRegistry."
            )

        self._registry = registry

    @property
    def registry(self) -> ExtractorRegistry:
        """
        Return the registry used by this factory.
        """

        return self._registry

    def resolve(
        self,
        path: str | Path,
    ) -> BaseDocumentExtractor:
        """
        Resolve the extractor registered for the source file extension.

        Args:
            path:
                A string or pathlib.Path representing a source document.

        Returns:
            The registered BaseDocumentExtractor instance.

        Raises:
            TypeError:
                If path is not a string or pathlib.Path.

            ValueError:
                If path is empty or has no usable extension.

            LookupError:
                If no extractor is registered for the extension.
        """

        file_path = self._normalize_path(path)
        extension = file_path.suffix

        if not extension:
            raise ValueError(
                "The source document must have a file extension."
            )

        try:
            return self._registry.get(extension)
        except KeyError as exc:
            supported = self._format_supported_extensions()

            raise LookupError(
                "Unsupported document extension "
                f"'{extension.lower()}'. "
                f"Supported extensions: {supported}."
            ) from exc

    def supports(
        self,
        path: str | Path,
    ) -> bool:
        """
        Return True if a registered extractor supports the source file.

        A path without an extension returns False.

        Invalid path types still raise TypeError because they represent
        programming errors rather than unsupported document formats.
        """

        file_path = self._normalize_path(path)
        extension = file_path.suffix

        if not extension:
            return False

        return self._registry.contains(extension)

    def create_for(
        self,
        path: str | Path,
    ) -> BaseDocumentExtractor:
        """
        Alias for resolve().

        This method provides factory-style terminology while preserving
        resolve() as the explicit registry resolution operation.
        """

        return self.resolve(path)

    @staticmethod
    def _normalize_path(
        path: str | Path,
    ) -> Path:
        """
        Validate and normalize a source path.

        The source file does not need to exist at factory resolution time.
        Existence validation remains the responsibility of the concrete
        extractor during extraction.
        """

        if not isinstance(path, (str, Path)):
            raise TypeError(
                "path must be a string or pathlib.Path."
            )

        if isinstance(path, str):
            normalized = path.strip()

            if not normalized:
                raise ValueError(
                    "path must not be empty."
                )

            return Path(normalized)

        if not str(path).strip():
            raise ValueError(
                "path must not be empty."
            )

        return path

    def _format_supported_extensions(self) -> str:
        """
        Return registered extensions as a user-readable string.
        """

        supported_extensions = self._registry.supported_extensions

        if not supported_extensions:
            return "none"

        return ", ".join(supported_extensions)