from pathlib import Path

import pytest

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
)
from backend.app.modules.medical_document_intelligence.extractors.factory import (
    ExtractorFactory,
)
from backend.app.modules.medical_document_intelligence.extractors.registry import (
    ExtractorRegistry,
)


class TxtExtractor(BaseDocumentExtractor):

    @property
    def supported_extensions(self):
        return (".txt",)

    @property
    def media_type(self):
        return "text/plain"

    def extract(self, path):
        return DocumentContent(
            text="TXT content",
            source_name="report.txt",
            media_type=self.media_type,
            extension=".txt",
            file_size=11,
        )


class DocxExtractor(BaseDocumentExtractor):

    @property
    def supported_extensions(self):
        return (".docx",)

    @property
    def media_type(self):
        return (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        )

    def extract(self, path):
        return DocumentContent(
            text="DOCX content",
            source_name="report.docx",
            media_type=self.media_type,
            extension=".docx",
            file_size=12,
        )


def build_factory():
    txt_extractor = TxtExtractor()
    docx_extractor = DocxExtractor()

    registry = ExtractorRegistry(
        extractors=(
            txt_extractor,
            docx_extractor,
        )
    )

    factory = ExtractorFactory(registry)

    return (
        factory,
        registry,
        txt_extractor,
        docx_extractor,
    )


def test_factory_requires_registry():
    with pytest.raises(
        TypeError,
        match="ExtractorRegistry",
    ):
        ExtractorFactory(
            object()
        )


def test_factory_exposes_registry():
    factory, registry, _, _ = build_factory()

    assert factory.registry is registry


def test_resolve_txt_extractor():
    factory, _, txt_extractor, _ = build_factory()

    resolved = factory.resolve(
        "report.txt"
    )

    assert resolved is txt_extractor


def test_resolve_docx_extractor():
    factory, _, _, docx_extractor = build_factory()

    resolved = factory.resolve(
        "report.docx"
    )

    assert resolved is docx_extractor


def test_resolve_uppercase_extension():
    factory, _, txt_extractor, _ = build_factory()

    resolved = factory.resolve(
        "REPORT.TXT"
    )

    assert resolved is txt_extractor


def test_resolve_pathlib_path():
    factory, _, txt_extractor, _ = build_factory()

    resolved = factory.resolve(
        Path("report.txt")
    )

    assert resolved is txt_extractor


def test_resolve_nested_path():
    factory, _, txt_extractor, _ = build_factory()

    resolved = factory.resolve(
        Path("documents") / "reports" / "report.txt"
    )

    assert resolved is txt_extractor


def test_create_for_is_alias_of_resolve():
    factory, _, txt_extractor, _ = build_factory()

    resolved = factory.create_for(
        "report.txt"
    )

    assert resolved is txt_extractor


def test_supports_registered_extension():
    factory, _, _, _ = build_factory()

    assert factory.supports(
        "report.txt"
    ) is True

    assert factory.supports(
        "report.docx"
    ) is True


def test_supports_uppercase_extension():
    factory, _, _, _ = build_factory()

    assert factory.supports(
        "REPORT.DOCX"
    ) is True


def test_supports_unregistered_extension():
    factory, _, _, _ = build_factory()

    assert factory.supports(
        "report.pdf"
    ) is False


def test_supports_path_without_extension_returns_false():
    factory, _, _, _ = build_factory()

    assert factory.supports(
        "report"
    ) is False


def test_resolve_path_without_extension_raises_value_error():
    factory, _, _, _ = build_factory()

    with pytest.raises(
        ValueError,
        match="must have a file extension",
    ):
        factory.resolve(
            "report"
        )


def test_resolve_empty_path_raises_value_error():
    factory, _, _, _ = build_factory()

    with pytest.raises(
        ValueError,
        match="path must not be empty",
    ):
        factory.resolve(
            "   "
        )


def test_supports_empty_path_raises_value_error():
    factory, _, _, _ = build_factory()

    with pytest.raises(
        ValueError,
        match="path must not be empty",
    ):
        factory.supports(
            ""
        )


def test_resolve_non_path_type_raises_type_error():
    factory, _, _, _ = build_factory()

    with pytest.raises(
        TypeError,
        match="path must be a string or pathlib.Path",
    ):
        factory.resolve(
            123
        )


def test_supports_non_path_type_raises_type_error():
    factory, _, _, _ = build_factory()

    with pytest.raises(
        TypeError,
        match="path must be a string or pathlib.Path",
    ):
        factory.supports(
            object()
        )


def test_unsupported_extension_raises_lookup_error():
    factory, _, _, _ = build_factory()

    with pytest.raises(
        LookupError,
        match="Unsupported document extension '.pdf'",
    ):
        factory.resolve(
            "report.pdf"
        )


def test_unsupported_extension_error_lists_supported_extensions():
    factory, _, _, _ = build_factory()

    with pytest.raises(
        LookupError,
        match=r"\.docx, \.txt",
    ):
        factory.resolve(
            "report.pdf"
        )


def test_empty_registry_error_reports_none_supported():
    registry = ExtractorRegistry()
    factory = ExtractorFactory(registry)

    with pytest.raises(
        LookupError,
        match="Supported extensions: none",
    ):
        factory.resolve(
            "report.txt"
        )


def test_factory_uses_registry_updates():
    registry = ExtractorRegistry()
    factory = ExtractorFactory(registry)
    txt_extractor = TxtExtractor()

    assert factory.supports(
        "report.txt"
    ) is False

    registry.register(
        txt_extractor
    )

    assert factory.supports(
        "report.txt"
    ) is True

    assert factory.resolve(
        "report.txt"
    ) is txt_extractor


def test_factory_stops_supporting_unregistered_extension():
    factory, registry, txt_extractor, _ = build_factory()

    assert factory.resolve(
        "report.txt"
    ) is txt_extractor

    registry.unregister(
        ".txt"
    )

    assert factory.supports(
        "report.txt"
    ) is False


def test_factory_only_resolves_and_does_not_extract():
    factory, _, txt_extractor, _ = build_factory()

    resolved = factory.resolve(
        "missing-file.txt"
    )

    assert resolved is txt_extractor