import pytest

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.extractors.base import (
    BaseDocumentExtractor,
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
            text="TXT",
            source_name="report.txt",
            media_type=self.media_type,
            extension=".txt",
            file_size=3,
        )


class MultiExtensionExtractor(BaseDocumentExtractor):

    @property
    def supported_extensions(self):
        return (
            ".text",
            ".log",
        )

    @property
    def media_type(self):
        return "text/plain"

    def extract(self, path):
        return DocumentContent(
            text="Multi",
            source_name="report.text",
            media_type=self.media_type,
            extension=".text",
            file_size=5,
        )


class DuplicateExtensionExtractor(BaseDocumentExtractor):

    @property
    def supported_extensions(self):
        return (
            ".txt",
            ".TXT",
        )

    @property
    def media_type(self):
        return "text/plain"

    def extract(self, path):
        return DocumentContent(
            text="Duplicate",
            source_name="report.txt",
            media_type=self.media_type,
            extension=".txt",
            file_size=9,
        )


class EmptyExtensionExtractor(BaseDocumentExtractor):

    @property
    def supported_extensions(self):
        return ()

    @property
    def media_type(self):
        return "application/octet-stream"

    def extract(self, path):
        return DocumentContent(
            text="",
            source_name="empty.bin",
            media_type=self.media_type,
            extension=".bin",
            file_size=0,
        )


def test_registry_starts_empty():
    registry = ExtractorRegistry()

    assert registry.supported_extensions == ()
    assert registry.extractor_count == 0
    assert registry.extension_count == 0


def test_registry_accepts_initial_extractors():
    txt_extractor = TxtExtractor()

    registry = ExtractorRegistry(
        extractors=(
            txt_extractor,
        )
    )

    assert registry.get(".txt") is txt_extractor


def test_register_extractor():
    registry = ExtractorRegistry()
    extractor = TxtExtractor()

    registry.register(extractor)

    assert registry.get(".txt") is extractor


def test_registers_all_supported_extensions():
    registry = ExtractorRegistry()
    extractor = MultiExtensionExtractor()

    registry.register(extractor)

    assert registry.get(".text") is extractor
    assert registry.get(".log") is extractor


def test_get_normalizes_extension_without_dot():
    registry = ExtractorRegistry()
    extractor = TxtExtractor()

    registry.register(extractor)

    assert registry.get("txt") is extractor


def test_get_normalizes_uppercase_extension():
    registry = ExtractorRegistry()
    extractor = TxtExtractor()

    registry.register(extractor)

    assert registry.get("TXT") is extractor


def test_contains_registered_extension():
    registry = ExtractorRegistry()
    registry.register(TxtExtractor())

    assert registry.contains(".txt") is True
    assert registry.contains("TXT") is True


def test_contains_unregistered_extension():
    registry = ExtractorRegistry()

    assert registry.contains(".pdf") is False


def test_supported_extensions_are_sorted():
    registry = ExtractorRegistry()

    registry.register(
        MultiExtensionExtractor()
    )
    registry.register(
        TxtExtractor()
    )

    assert registry.supported_extensions == (
        ".log",
        ".text",
        ".txt",
    )


def test_extractor_count_counts_unique_instances():
    registry = ExtractorRegistry()

    registry.register(
        MultiExtensionExtractor()
    )

    assert registry.extractor_count == 1
    assert registry.extension_count == 2


def test_duplicate_registration_is_rejected():
    registry = ExtractorRegistry()

    registry.register(
        TxtExtractor()
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        registry.register(
            TxtExtractor()
        )


def test_duplicate_registration_can_be_replaced():
    registry = ExtractorRegistry()

    first = TxtExtractor()
    second = TxtExtractor()

    registry.register(first)
    registry.register(
        second,
        replace=True,
    )

    assert registry.get(".txt") is second


def test_duplicate_extensions_inside_extractor_are_rejected():
    registry = ExtractorRegistry()

    with pytest.raises(
        ValueError,
        match="duplicate supported extensions",
    ):
        registry.register(
            DuplicateExtensionExtractor()
        )


def test_extractor_without_extensions_is_rejected():
    registry = ExtractorRegistry()

    with pytest.raises(
        ValueError,
        match="at least one supported extension",
    ):
        registry.register(
            EmptyExtensionExtractor()
        )


def test_non_extractor_object_is_rejected():
    registry = ExtractorRegistry()

    with pytest.raises(
        TypeError,
        match="BaseDocumentExtractor",
    ):
        registry.register(
            object()
        )


def test_get_unknown_extension_raises_key_error():
    registry = ExtractorRegistry()

    with pytest.raises(
        KeyError,
        match="No extractor is registered",
    ):
        registry.get(".pdf")


def test_unregister_extension():
    registry = ExtractorRegistry()
    extractor = TxtExtractor()

    registry.register(extractor)

    removed = registry.unregister(".txt")

    assert removed is extractor
    assert registry.contains(".txt") is False


def test_unregister_unknown_extension_raises_key_error():
    registry = ExtractorRegistry()

    with pytest.raises(
        KeyError,
        match="No extractor is registered",
    ):
        registry.unregister(".pdf")


def test_clear_removes_all_registrations():
    registry = ExtractorRegistry()

    registry.register(
        TxtExtractor()
    )
    registry.register(
        MultiExtensionExtractor()
    )

    registry.clear()

    assert registry.supported_extensions == ()
    assert registry.extractor_count == 0
    assert registry.extension_count == 0


@pytest.mark.parametrize(
    "extension",
    [
        "",
        " ",
        ".",
        "report.txt",
        "folder/txt",
        r"folder\txt",
        "t xt",
    ],
)
def test_invalid_extensions_are_rejected(extension):
    registry = ExtractorRegistry()

    with pytest.raises(
        ValueError,
    ):
        registry.contains(extension)


def test_non_string_extension_is_rejected():
    registry = ExtractorRegistry()

    with pytest.raises(
        TypeError,
        match="extension must be a string",
    ):
        registry.contains(123)