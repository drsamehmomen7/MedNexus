from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
)


class PdfDocumentExtractor(BaseDocumentExtractor):
    """
    Extract text and metadata from text-based PDF documents.

    This extractor supports digital PDFs that already contain an
    extractable text layer.

    Supported capabilities:
        - Multi-page text extraction.
        - PDF metadata extraction.
        - Empty-page detection.
        - Detection of PDFs with no extractable text.
        - Basic handling of encrypted PDFs with an empty password.
        - Unified DocumentContent output.

    Current boundaries:
        - Scanned PDFs are not processed with OCR in this stage.
        - Images are not converted to text.
        - Handwritten content is not processed.
        - Tables are currently represented through their extracted text.
        - Page geometry and bounding boxes are not yet returned.
        - Password-protected PDFs requiring a password are rejected.

    Responsibilities not included:
        - De-identification.
        - Clinical NLP.
        - Document classification.
        - OCR.
        - Malware scanning.
        - Password management.
    """

    PDF_MEDIA_TYPE = "application/pdf"

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".pdf",)

    @property
    def media_type(self) -> str:
        return self.PDF_MEDIA_TYPE

    def extract(
        self,
        path: str | Path,
    ) -> DocumentContent:
        """
        Extract text and metadata from a PDF document.

        Args:
            path:
                Source PDF file path.

        Returns:
            DocumentContent containing extracted text, page count,
            source metadata, and non-fatal warnings.

        Raises:
            TypeError:
                If path is not a string or pathlib.Path.

            FileNotFoundError:
                If the source file does not exist.

            ValueError:
                If the path is empty, is not a file, has the wrong
                extension, is encrypted with a password, or contains
                an invalid/corrupted PDF package.

            PermissionError:
                If the operating system prevents reading the file.
        """

        file_path = self._validate_path(path)

        try:
            reader = PdfReader(
                str(file_path),
                strict=False,
            )
        except PdfReadError as exc:
            raise ValueError(
                f"The PDF document is invalid or corrupted: "
                f"{file_path.name}."
            ) from exc
        except (OSError, ValueError) as exc:
            raise ValueError(
                f"Unable to open PDF document: "
                f"{file_path.name}."
            ) from exc

        self._handle_encryption(
            reader=reader,
            file_name=file_path.name,
        )

        page_texts: List[str] = []
        empty_page_numbers: List[int] = []
        failed_page_numbers: List[int] = []

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):
            try:
                extracted_text = page.extract_text()
            except Exception:
                extracted_text = None
                failed_page_numbers.append(
                    page_number
                )

            normalized_text = self._normalize_text(
                extracted_text
            )

            if normalized_text:
                page_texts.append(
                    normalized_text
                )
            else:
                empty_page_numbers.append(
                    page_number
                )

        text = self._join_pages(
            page_texts
        )

        page_count = len(reader.pages)

        warnings = self._build_warnings(
            text=text,
            page_count=page_count,
            empty_page_numbers=empty_page_numbers,
            failed_page_numbers=failed_page_numbers,
        )

        pdf_metadata = self._extract_metadata(
            reader
        )

        metadata: Dict[str, Any] = {
            "extractor": "pdf",
            "pdf_metadata": pdf_metadata,
            "encrypted": bool(
                reader.is_encrypted
            ),
            "page_count": page_count,
            "extracted_page_count": len(
                page_texts
            ),
            "empty_page_count": len(
                empty_page_numbers
            ),
            "empty_page_numbers": tuple(
                empty_page_numbers
            ),
            "failed_page_count": len(
                failed_page_numbers
            ),
            "failed_page_numbers": tuple(
                failed_page_numbers
            ),
            "contains_extractable_text": bool(
                text.strip()
            ),
            "ocr_applied": False,
            "preserves_page_order": True,
        }

        return DocumentContent(
            text=text,
            source_name=file_path.name,
            media_type=self.media_type,
            extension=file_path.suffix,
            file_size=file_path.stat().st_size,
            encoding=None,
            page_count=page_count,
            metadata=metadata,
            warnings=tuple(warnings),
        )

    def _validate_path(
        self,
        path: str | Path,
    ) -> Path:
        """
        Validate and normalize the source PDF path.
        """

        if not isinstance(
            path,
            (str, Path),
        ):
            raise TypeError(
                "path must be a string or pathlib.Path."
            )

        if isinstance(path, str):
            normalized_path = path.strip()

            if not normalized_path:
                raise ValueError(
                    "path must not be empty."
                )

            file_path = Path(
                normalized_path
            )
        else:
            file_path = path

        if not file_path.exists():
            raise FileNotFoundError(
                file_path
            )

        if not file_path.is_file():
            raise ValueError(
                f"{file_path} is not a file."
            )

        if (
            file_path.suffix.lower()
            not in self.supported_extensions
        ):
            raise ValueError(
                "PdfDocumentExtractor supports only "
                "'.pdf' files."
            )

        return file_path

    @staticmethod
    def _handle_encryption(
        *,
        reader: PdfReader,
        file_name: str,
    ) -> None:
        """
        Attempt to open PDFs encrypted with an empty password.

        PDFs requiring an explicit password are rejected because
        password acquisition and secret management are outside the
        responsibilities of this extractor.
        """

        if not reader.is_encrypted:
            return

        try:
            decryption_result = reader.decrypt(
                ""
            )
        except Exception as exc:
            raise ValueError(
                f"The PDF document is encrypted and could not "
                f"be opened: {file_name}."
            ) from exc

        if not decryption_result:
            raise ValueError(
                f"The PDF document requires a password: "
                f"{file_name}."
            )

    @staticmethod
    def _extract_metadata(
        reader: PdfReader,
    ) -> Dict[str, Optional[str]]:
        """
        Convert PDF metadata into a serializable dictionary.

        Leading slash characters used by the PDF format are removed
        from metadata field names.
        """

        raw_metadata = reader.metadata

        if not raw_metadata:
            return {}

        normalized_metadata: Dict[
            str,
            Optional[str],
        ] = {}

        for key, value in raw_metadata.items():
            normalized_key = str(
                key
            ).lstrip("/").strip()

            if not normalized_key:
                continue

            if value is None:
                normalized_value = None
            else:
                normalized_value = str(
                    value
                ).strip()

                if not normalized_value:
                    normalized_value = None

            normalized_metadata[
                normalized_key
            ] = normalized_value

        return normalized_metadata

    @staticmethod
    def _normalize_text(
        text: Optional[str],
    ) -> str:
        """
        Normalize extracted page text while preserving line order.
        """

        if not isinstance(
            text,
            str,
        ):
            return ""

        normalized = text.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )

        lines = [
            line.rstrip()
            for line in normalized.split(
                "\n"
            )
        ]

        while (
            lines
            and not lines[0].strip()
        ):
            lines.pop(0)

        while (
            lines
            and not lines[-1].strip()
        ):
            lines.pop()

        return "\n".join(
            lines
        ).strip()

    @staticmethod
    def _join_pages(
        page_texts: List[str],
    ) -> str:
        """
        Join extracted pages in their original order.

        A blank line separates pages without inserting artificial
        content into the medical document.
        """

        normalized_pages = [
            page_text.strip()
            for page_text in page_texts
            if page_text.strip()
        ]

        return "\n\n".join(
            normalized_pages
        )

    @staticmethod
    def _build_warnings(
        *,
        text: str,
        page_count: int,
        empty_page_numbers: List[int],
        failed_page_numbers: List[int],
    ) -> List[str]:
        """
        Create non-fatal PDF extraction warnings.
        """

        warnings: List[str] = []

        if page_count == 0:
            warnings.append(
                "The PDF document contains no pages."
            )

        if not text.strip():
            warnings.append(
                "The PDF document contains no extractable text. "
                "It may be scanned or image-based and may require OCR."
            )

        if empty_page_numbers:
            page_list = ", ".join(
                str(page_number)
                for page_number
                in empty_page_numbers
            )

            warnings.append(
                "No extractable text was found on PDF page(s): "
                f"{page_list}."
            )

        if failed_page_numbers:
            page_list = ", ".join(
                str(page_number)
                for page_number
                in failed_page_numbers
            )

            warnings.append(
                "Text extraction failed on PDF page(s): "
                f"{page_list}."
            )

        return warnings