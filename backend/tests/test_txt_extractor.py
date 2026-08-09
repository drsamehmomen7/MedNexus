from pathlib import Path

import pytest

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.txt import (
    TxtDocumentExtractor,
)


def test_supported_extension():
    extractor = TxtDocumentExtractor()

    assert extractor.supported_extensions == (
        ".txt",
    )


def test_media_type():
    extractor = TxtDocumentExtractor()

    assert extractor.media_type == "text/plain"


def test_extract_txt(tmp_path):

    file = tmp_path / "report.txt"

    file.write_text(
        "Patient Name\nAhmed",
        encoding="utf-8",
    )

    extractor = TxtDocumentExtractor()

    result = extractor.extract(file)

    assert isinstance(
        result,
        DocumentContent,
    )

    assert result.text == "Patient Name\nAhmed"

    assert result.source_name == "report.txt"

    assert result.extension == ".txt"

    assert result.media_type == "text/plain"

    assert result.encoding == "utf-8"

    assert result.page_count == 1

    assert result.metadata["extractor"] == "txt"


def test_missing_file():

    extractor = TxtDocumentExtractor()

    with pytest.raises(
        FileNotFoundError,
    ):
        extractor.extract(
            "missing.txt",
        )


def test_directory_is_not_file(tmp_path):

    extractor = TxtDocumentExtractor()

    with pytest.raises(
        ValueError,
    ):
        extractor.extract(
            tmp_path,
        )


def test_supports():

    extractor = TxtDocumentExtractor()

    assert extractor.supports(
        "abc.txt",
    )

    assert extractor.supports(
        Path("abc.txt"),
    )

    assert not extractor.supports(
        "abc.pdf",
    )