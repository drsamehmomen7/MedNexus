from pathlib import Path

import pytest

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
)


class DummyExtractor(BaseDocumentExtractor):

    @property
    def supported_extensions(self):
        return (".txt", ".text")

    @property
    def media_type(self):
        return "text/plain"

    def extract(self, path):
        return DocumentContent(
            text="Example",
            source_name="example.txt",
            media_type=self.media_type,
            extension=".txt",
            file_size=7,
        )


def test_supports_txt():
    extractor = DummyExtractor()

    assert extractor.supports("report.txt")


def test_supports_uppercase_extension():
    extractor = DummyExtractor()

    assert extractor.supports("REPORT.TXT")


def test_supports_pathlib():
    extractor = DummyExtractor()

    assert extractor.supports(Path("report.txt"))


def test_rejects_pdf():
    extractor = DummyExtractor()

    assert extractor.supports("report.pdf") is False


def test_media_type():
    extractor = DummyExtractor()

    assert extractor.media_type == "text/plain"


def test_supported_extensions():
    extractor = DummyExtractor()

    assert extractor.supported_extensions == (
        ".txt",
        ".text",
    )


def test_extract_returns_document_content():
    extractor = DummyExtractor()

    result = extractor.extract("anything.txt")

    assert isinstance(result, DocumentContent)


def test_cannot_instantiate_base_extractor():
    with pytest.raises(TypeError):
        BaseDocumentExtractor()