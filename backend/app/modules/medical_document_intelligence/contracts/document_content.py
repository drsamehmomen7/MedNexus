from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Optional, Tuple


@dataclass(frozen=True, slots=True)
class DocumentContent:
    """
    Immutable contract representing content extracted from a document.

    All MedNexus document extractors must return this contract,
    regardless of the original file format.

    Examples of supported and planned sources:

    - TXT
    - DOCX
    - PDF
    - Scanned PDF through OCR
    - RTF
    - HTML
    - HL7 CDA
    - FHIR DocumentReference
    - DICOM Structured Report

    The contract stores the extracted plain text together with
    source metadata, extraction details, and non-fatal warnings.
    """

    text: str
    source_name: str
    media_type: str
    extension: str
    file_size: int

    encoding: Optional[str] = None
    page_count: Optional[int] = None
    line_count: Optional[int] = None

    metadata: Mapping[str, Any] = field(default_factory=dict)
    warnings: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """
        Validate and normalize the document content contract.

        The dataclass is frozen, therefore normalization is performed
        with object.__setattr__ only during initialization.
        """

        if not isinstance(self.text, str):
            raise TypeError("text must be a string.")

        if not isinstance(self.source_name, str):
            raise TypeError("source_name must be a string.")

        normalized_source_name = self.source_name.strip()

        if not normalized_source_name:
            raise ValueError("source_name must not be empty.")

        if not isinstance(self.media_type, str):
            raise TypeError("media_type must be a string.")

        normalized_media_type = self.media_type.strip().lower()

        if not normalized_media_type:
            raise ValueError("media_type must not be empty.")

        if not isinstance(self.extension, str):
            raise TypeError("extension must be a string.")

        normalized_extension = self.extension.strip().lower()

        if not normalized_extension:
            raise ValueError("extension must not be empty.")

        if not normalized_extension.startswith("."):
            normalized_extension = f".{normalized_extension}"

        if isinstance(self.file_size, bool) or not isinstance(
            self.file_size,
            int,
        ):
            raise TypeError("file_size must be an integer.")

        if self.file_size < 0:
            raise ValueError("file_size must not be negative.")

        if self.encoding is not None:
            if not isinstance(self.encoding, str):
                raise TypeError(
                    "encoding must be a string or None."
                )

            normalized_encoding = self.encoding.strip().lower()

            if not normalized_encoding:
                normalized_encoding = None
        else:
            normalized_encoding = None

        normalized_page_count = self._validate_optional_count(
            name="page_count",
            value=self.page_count,
            minimum=1,
        )

        calculated_line_count = self._calculate_line_count(
            self.text
        )

        if self.line_count is None:
            normalized_line_count = calculated_line_count
        else:
            normalized_line_count = self._validate_optional_count(
                name="line_count",
                value=self.line_count,
                minimum=0,
            )

        if not isinstance(self.metadata, Mapping):
            raise TypeError("metadata must be a mapping.")

        normalized_metadata = MappingProxyType(
            dict(self.metadata)
        )

        if isinstance(self.warnings, str):
            raise TypeError(
                "warnings must be an iterable of strings, "
                "not a single string."
            )

        try:
            normalized_warnings = tuple(self.warnings)
        except TypeError as exc:
            raise TypeError(
                "warnings must be an iterable of strings."
            ) from exc

        for warning in normalized_warnings:
            if not isinstance(warning, str):
                raise TypeError(
                    "Every warning must be a string."
                )

        normalized_warnings = tuple(
            warning.strip()
            for warning in normalized_warnings
            if warning.strip()
        )

        object.__setattr__(
            self,
            "source_name",
            normalized_source_name,
        )
        object.__setattr__(
            self,
            "media_type",
            normalized_media_type,
        )
        object.__setattr__(
            self,
            "extension",
            normalized_extension,
        )
        object.__setattr__(
            self,
            "encoding",
            normalized_encoding,
        )
        object.__setattr__(
            self,
            "page_count",
            normalized_page_count,
        )
        object.__setattr__(
            self,
            "line_count",
            normalized_line_count,
        )
        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )
        object.__setattr__(
            self,
            "warnings",
            normalized_warnings,
        )

    @property
    def is_empty(self) -> bool:
        """
        Return True when the extracted text contains no meaningful
        non-whitespace content.
        """

        return not self.text.strip()

    @property
    def has_warnings(self) -> bool:
        """
        Return True when one or more non-fatal extraction warnings
        were recorded.
        """

        return bool(self.warnings)

    @property
    def character_count(self) -> int:
        """
        Return the number of characters in the extracted text.
        """

        return len(self.text)

    @staticmethod
    def _calculate_line_count(text: str) -> int:
        """
        Calculate the number of logical lines in extracted text.

        Empty text has zero lines.
        A non-empty string without newline characters has one line.
        """

        if text == "":
            return 0

        return len(text.splitlines())

    @staticmethod
    def _validate_optional_count(
        *,
        name: str,
        value: Optional[int],
        minimum: int,
    ) -> Optional[int]:
        """
        Validate optional integer count fields.
        """

        if value is None:
            return None

        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(
                f"{name} must be an integer or None."
            )

        if value < minimum:
            raise ValueError(
                f"{name} must be greater than or equal "
                f"to {minimum}."
            )

        return value