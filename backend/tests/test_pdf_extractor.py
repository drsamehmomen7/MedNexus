from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.pdf import (
    PdfDocumentExtractor,
)


def _escape_pdf_text(text: str) -> str:
    """
    Escape characters that have special meaning inside PDF text
    operators.
    """

    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _add_text_page(
    writer: PdfWriter,
    text: Optional[str],
) -> None:
    """
    Add a basic PDF page containing extractable Helvetica text.

    This helper creates a real text layer without introducing an
    additional test dependency such as ReportLab.
    """

    page = writer.add_blank_page(
        width=612,
        height=792,
    )

    if text is None:
        return

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )

    font_reference = writer._add_object(font)

    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): font_reference,
                }
            )
        }
    )

    content_stream = DecodedStreamObject()

    escaped_text = _escape_pdf_text(text)

    content_stream.set_data(
        (
            "BT\n"
            "/F1 12 Tf\n"
            "72 720 Td\n"
            f"({escaped_text}) Tj\n"
            "ET\n"
        ).encode("latin-1")
    )

    page[NameObject("/Contents")] = writer._add_object(
        content_stream
    )


def create_pdf(
    path: Path,
    *,
    pages: tuple[Optional[str], ...] = ("Clinical Report",),
    metadata: Optional[dict[str, str]] = None,
    password: Optional[str] = None,
) -> Path:
    """
    Create a PDF fixture for extractor tests.
    """

    writer = PdfWriter()

    for page_text in pages:
        _add_text_page(
            writer,
            page_text,
        )

    if metadata:
        writer.add_metadata(
            metadata
        )

    if password is not None:
        writer.encrypt(
            password
        )

    with path.open("wb") as file_handle:
        writer.write(
            file_handle
        )

    return path


def test_supported_extension():
    extractor = PdfDocumentExtractor()

    assert extractor.supported_extensions == (
        ".pdf",
    )


def test_media_type():
    extractor = PdfDocumentExtractor()

    assert extractor.media_type == "application/pdf"


def test_supports_pdf_extension():
    extractor = PdfDocumentExtractor()

    assert extractor.supports(
        "report.pdf"
    ) is True


def test_supports_uppercase_pdf_extension():
    extractor = PdfDocumentExtractor()

    assert extractor.supports(
        "REPORT.PDF"
    ) is True


def test_rejects_non_pdf_extension():
    extractor = PdfDocumentExtractor()

    assert extractor.supports(
        "report.docx"
    ) is False


def test_extract_returns_document_content(tmp_path):
    file_path = create_pdf(
        tmp_path / "report.pdf",
        pages=(
            "Pathology Department",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert isinstance(
        result,
        DocumentContent,
    )


def test_extracts_text_from_pdf(tmp_path):
    file_path = create_pdf(
        tmp_path / "report.pdf",
        pages=(
            "Patient Name: Ahmed Hassan",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert "Patient Name: Ahmed Hassan" in result.text


def test_extracts_multiple_pages_in_order(tmp_path):
    file_path = create_pdf(
        tmp_path / "multi-page.pdf",
        pages=(
            "First Page Content",
            "Second Page Content",
            "Third Page Content",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    first_position = result.text.index(
        "First Page Content"
    )
    second_position = result.text.index(
        "Second Page Content"
    )
    third_position = result.text.index(
        "Third Page Content"
    )

    assert first_position < second_position
    assert second_position < third_position


def test_pages_are_separated_by_blank_line(tmp_path):
    file_path = create_pdf(
        tmp_path / "multi-page.pdf",
        pages=(
            "Page One",
            "Page Two",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert "Page One\n\nPage Two" in result.text


def test_extracts_page_count(tmp_path):
    file_path = create_pdf(
        tmp_path / "three-pages.pdf",
        pages=(
            "Page One",
            "Page Two",
            "Page Three",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert result.page_count == 3
    assert result.metadata["page_count"] == 3


def test_extracts_source_metadata(tmp_path):
    file_path = create_pdf(
        tmp_path / "clinical-report.pdf",
        pages=(
            "Clinical Report",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert result.source_name == "clinical-report.pdf"
    assert result.extension == ".pdf"
    assert result.media_type == "application/pdf"
    assert result.file_size > 0
    assert result.encoding is None


def test_extracts_pdf_metadata(tmp_path):
    file_path = create_pdf(
        tmp_path / "metadata.pdf",
        pages=(
            "Laboratory Report",
        ),
        metadata={
            "/Title": "Laboratory Report",
            "/Author": "MedNexus",
            "/Subject": "Clinical Validation",
        },
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    pdf_metadata = result.metadata[
        "pdf_metadata"
    ]

    assert pdf_metadata["Title"] == "Laboratory Report"
    assert pdf_metadata["Author"] == "MedNexus"
    assert pdf_metadata["Subject"] == "Clinical Validation"


def test_pdf_metadata_keys_have_no_leading_slash(tmp_path):
    file_path = create_pdf(
        tmp_path / "metadata.pdf",
        metadata={
            "/Title": "Medical Report",
        },
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    metadata_keys = result.metadata[
        "pdf_metadata"
    ].keys()

    assert "Title" in metadata_keys
    assert "/Title" not in metadata_keys


def test_reports_extractor_metadata(tmp_path):
    file_path = create_pdf(
        tmp_path / "report.pdf",
        pages=(
            "Clinical content",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert result.metadata["extractor"] == "pdf"
    assert result.metadata["ocr_applied"] is False
    assert result.metadata["preserves_page_order"] is True
    assert result.metadata["contains_extractable_text"] is True
    assert result.metadata["encrypted"] is False


def test_reports_extracted_page_count(tmp_path):
    file_path = create_pdf(
        tmp_path / "report.pdf",
        pages=(
            "Page One",
            None,
            "Page Three",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert result.metadata["page_count"] == 3
    assert result.metadata["extracted_page_count"] == 2
    assert result.metadata["empty_page_count"] == 1
    assert result.metadata["empty_page_numbers"] == (
        2,
    )


def test_blank_page_generates_warning(tmp_path):
    file_path = create_pdf(
        tmp_path / "blank-page.pdf",
        pages=(
            "Page One",
            None,
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert result.has_warnings is True

    assert (
        "No extractable text was found on PDF page(s): 2."
        in result.warnings
    )


def test_image_style_pdf_without_text_generates_ocr_warning(
    tmp_path,
):
    file_path = create_pdf(
        tmp_path / "scanned-style.pdf",
        pages=(
            None,
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert result.is_empty is True
    assert result.metadata[
        "contains_extractable_text"
    ] is False

    assert any(
        "may require OCR" in warning
        for warning in result.warnings
    )


def test_pdf_with_text_has_no_ocr_warning(tmp_path):
    file_path = create_pdf(
        tmp_path / "digital.pdf",
        pages=(
            "Digital PDF content",
        ),
    )

    extractor = PdfDocumentExtractor()

    result = extractor.extract(
        file_path
    )

    assert not any(
        "may require OCR" in warning
        for warning in result.warnings
    )


def test_missing_file_raises_file_not_found():
    extractor = PdfDocumentExtractor()

    with pytest.raises(
        FileNotFoundError,
    ):
        extractor.extract(
            "missing-report.pdf"
        )


def test_directory_path_is_rejected(tmp_path):
    extractor = PdfDocumentExtractor()

    with pytest.raises(
        ValueError,
        match="is not a file",
    ):
        extractor.extract(
            tmp_path
        )


def test_empty_string_path_is_rejected():
    extractor = PdfDocumentExtractor()

    with pytest.raises(
        ValueError,
        match="path must not be empty",
    ):
        extractor.extract(
            "   "
        )


def test_non_path_value_is_rejected():
    extractor = PdfDocumentExtractor()

    with pytest.raises(
        TypeError,
        match="path must be a string or pathlib.Path",
    ):
        extractor.extract(
            123
        )


def test_wrong_extension_is_rejected(tmp_path):
    file_path = tmp_path / "report.txt"

    file_path.write_text(
        "Not a PDF document",
        encoding="utf-8",
    )

    extractor = PdfDocumentExtractor()

    with pytest.raises(
        ValueError,
        match="supports only '.pdf' files",
    ):
        extractor.extract(
            file_path
        )


def test_invalid_pdf_file_is_rejected(tmp_path):
    file_path = tmp_path / "invalid.pdf"

    file_path.write_text(
        "This is not a valid PDF document.",
        encoding="utf-8",
    )

    extractor = PdfDocumentExtractor()

    with pytest.raises(
        ValueError,
        match=(
            "invalid or corrupted"
            "|Unable to open PDF document"
        ),
    ):
        extractor.extract(
            file_path
        )


def test_password_protected_pdf_is_rejected(tmp_path):
    file_path = create_pdf(
        tmp_path / "protected.pdf",
        pages=(
            "Protected clinical content",
        ),
        password="secret-password",
    )

    extractor = PdfDocumentExtractor()

    with pytest.raises(
        ValueError,
        match=(
            "requires a password"
            "|encrypted and could not be opened"
        ),
    ):
        extractor.extract(
            file_path
        )


def test_normalize_text_handles_none():
    result = PdfDocumentExtractor._normalize_text(
        None
    )

    assert result == ""


def test_normalize_text_removes_outer_blank_lines():
    result = PdfDocumentExtractor._normalize_text(
        "\n\nClinical Report\n\n"
    )

    assert result == "Clinical Report"


def test_normalize_text_normalizes_windows_line_breaks():
    result = PdfDocumentExtractor._normalize_text(
        "Line One\r\nLine Two\rLine Three"
    )

    assert result == (
        "Line One\n"
        "Line Two\n"
        "Line Three"
    )


def test_join_pages_preserves_page_order():
    result = PdfDocumentExtractor._join_pages(
        [
            "First page",
            "Second page",
            "Third page",
        ]
    )

    assert result == (
        "First page\n\n"
        "Second page\n\n"
        "Third page"
    )


def test_join_pages_ignores_empty_page_text():
    result = PdfDocumentExtractor._join_pages(
        [
            "First page",
            "",
            "   ",
            "Last page",
        ]
    )

    assert result == (
        "First page\n\n"
        "Last page"
    )