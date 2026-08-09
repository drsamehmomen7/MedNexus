from backend.app.modules.medical_document_intelligence.extractors.bootstrap import (
    build_default_registry,
)
from backend.app.modules.medical_document_intelligence.extractors.docx import (
    DocxDocumentExtractor,
)
from backend.app.modules.medical_document_intelligence.extractors.pdf import (
    PdfDocumentExtractor,
)
from backend.app.modules.medical_document_intelligence.extractors.registry import (
    ExtractorRegistry,
)
from backend.app.modules.medical_document_intelligence.extractors.txt import (
    TxtDocumentExtractor,
)


def test_build_default_registry_returns_registry():
    registry = build_default_registry()

    assert isinstance(
        registry,
        ExtractorRegistry,
    )


def test_txt_is_registered():
    registry = build_default_registry()

    extractor = registry.get(
        ".txt"
    )

    assert isinstance(
        extractor,
        TxtDocumentExtractor,
    )


def test_docx_is_registered():
    registry = build_default_registry()

    extractor = registry.get(
        ".docx"
    )

    assert isinstance(
        extractor,
        DocxDocumentExtractor,
    )


def test_pdf_is_registered():
    registry = build_default_registry()

    extractor = registry.get(
        ".pdf"
    )

    assert isinstance(
        extractor,
        PdfDocumentExtractor,
    )


def test_supported_extensions():
    registry = build_default_registry()

    assert registry.supported_extensions == (
        ".docx",
        ".pdf",
        ".txt",
    )


def test_extension_count():
    registry = build_default_registry()

    assert registry.extension_count == 3


def test_extractor_count():
    registry = build_default_registry()

    assert registry.extractor_count == 3


def test_contains_registered_extensions():
    registry = build_default_registry()

    assert registry.contains(
        ".txt"
    )
    assert registry.contains(
        ".docx"
    )
    assert registry.contains(
        ".pdf"
    )


def test_contains_is_case_insensitive():
    registry = build_default_registry()

    assert registry.contains(
        "TXT"
    )
    assert registry.contains(
        "DOCX"
    )
    assert registry.contains(
        "PDF"
    )


def test_each_registry_is_independent():
    first_registry = build_default_registry()
    second_registry = build_default_registry()

    first_registry.unregister(
        ".txt"
    )

    assert first_registry.contains(
        ".txt"
    ) is False

    assert second_registry.contains(
        ".txt"
    ) is True