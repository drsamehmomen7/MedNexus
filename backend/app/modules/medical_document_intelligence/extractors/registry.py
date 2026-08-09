from __future__ import annotations

from typing import Dict, Iterable, Tuple

from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
)


class ExtractorRegistry:
    """
    Registry for MedNexus document extractors.

    The registry maps file extensions to extractor instances.

    Responsibilities:
        - Register document extractors.
        - Normalize supported extensions.
        - Resolve an extractor by file extension.
        - Report all supported extensions.

    Responsibilities not included:
        - Reading files.
        - Inspecting file contents.
        - Applying de-identification.
        - Selecting extractors by MIME sniffing.
        - Creating API responses.

    Each registry instance owns its own state to avoid hidden global
    configuration and to support isolated tests and future tenant-specific
    extractor configurations.
    """

    def __init__(
        self,
        extractors: Iterable[BaseDocumentExtractor] | None = None,
    ) -> None:
        self._extractors: Dict[str, BaseDocumentExtractor] = {}

        if extractors is not None:
            for extractor in extractors:
                self.register(extractor)

    def register(
        self,
        extractor: BaseDocumentExtractor,
        *,
        replace: bool = False,
    ) -> None:
        """
        Register an extractor for all its supported extensions.

        Args:
            extractor:
                A concrete BaseDocumentExtractor instance.

            replace:
                When False, registering an extension that already belongs
                to another extractor raises ValueError.

                When True, the existing registration is replaced.

        Raises:
            TypeError:
                If extractor is not a BaseDocumentExtractor instance.

            ValueError:
                If the extractor exposes no supported extensions, exposes
                an invalid extension, or attempts to register a duplicate
                extension without replace=True.
        """

        if not isinstance(extractor, BaseDocumentExtractor):
            raise TypeError(
                "extractor must be an instance of "
                "BaseDocumentExtractor."
            )

        extensions = tuple(extractor.supported_extensions)

        if not extensions:
            raise ValueError(
                "extractor must declare at least one "
                "supported extension."
            )

        normalized_extensions = tuple(
            self._normalize_extension(extension)
            for extension in extensions
        )

        if len(set(normalized_extensions)) != len(
            normalized_extensions
        ):
            raise ValueError(
                "extractor contains duplicate supported extensions."
            )

        if not replace:
            duplicate_extensions = [
                extension
                for extension in normalized_extensions
                if extension in self._extractors
            ]

            if duplicate_extensions:
                duplicates = ", ".join(
                    sorted(duplicate_extensions)
                )

                raise ValueError(
                    "An extractor is already registered for: "
                    f"{duplicates}."
                )

        for extension in normalized_extensions:
            self._extractors[extension] = extractor

    def unregister(
        self,
        extension: str,
    ) -> BaseDocumentExtractor:
        """
        Remove and return the extractor registered for an extension.

        Only the requested extension mapping is removed. Other extensions
        belonging to the same extractor remain registered.

        Raises:
            KeyError:
                If no extractor is registered for the extension.
        """

        normalized_extension = self._normalize_extension(
            extension
        )

        try:
            return self._extractors.pop(normalized_extension)
        except KeyError as exc:
            raise KeyError(
                "No extractor is registered for extension "
                f"'{normalized_extension}'."
            ) from exc

    def get(
        self,
        extension: str,
    ) -> BaseDocumentExtractor:
        """
        Return the extractor registered for an extension.

        The extension may be supplied with or without a leading dot and
        in any letter case.

        Examples:
            ".txt"
            "txt"
            "TXT"

        Raises:
            KeyError:
                If the extension is not registered.
        """

        normalized_extension = self._normalize_extension(
            extension
        )

        try:
            return self._extractors[normalized_extension]
        except KeyError as exc:
            raise KeyError(
                "No extractor is registered for extension "
                f"'{normalized_extension}'."
            ) from exc

    def contains(
        self,
        extension: str,
    ) -> bool:
        """
        Return True when an extractor is registered for the extension.
        """

        normalized_extension = self._normalize_extension(
            extension
        )

        return normalized_extension in self._extractors

    @property
    def supported_extensions(self) -> Tuple[str, ...]:
        """
        Return all registered extensions in deterministic order.
        """

        return tuple(sorted(self._extractors))

    @property
    def extractor_count(self) -> int:
        """
        Return the number of unique registered extractor instances.

        An extractor supporting multiple extensions is counted once.
        """

        return len(
            {
                id(extractor)
                for extractor in self._extractors.values()
            }
        )

    @property
    def extension_count(self) -> int:
        """
        Return the number of registered extension mappings.
        """

        return len(self._extractors)

    def clear(self) -> None:
        """
        Remove all extractor registrations.
        """

        self._extractors.clear()

    @staticmethod
    def _normalize_extension(
        extension: str,
    ) -> str:
        """
        Normalize a file extension.

        Examples:
            "TXT" -> ".txt"
            " .PDF " -> ".pdf"
        """

        if not isinstance(extension, str):
            raise TypeError(
                "extension must be a string."
            )

        normalized = extension.strip().lower()

        if not normalized:
            raise ValueError(
                "extension must not be empty."
            )

        if "/" in normalized or "\\" in normalized:
            raise ValueError(
                "extension must not contain path separators."
            )

        if normalized == ".":
            raise ValueError(
                "extension must contain characters after the dot."
            )

        if not normalized.startswith("."):
            normalized = f".{normalized}"

        if normalized.count(".") != 1:
            raise ValueError(
                "extension must contain exactly one leading dot."
            )

        if any(character.isspace() for character in normalized):
            raise ValueError(
                "extension must not contain whitespace."
            )

        return normalized