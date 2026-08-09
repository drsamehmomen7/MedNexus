from dataclasses import FrozenInstanceError

import pytest

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)


def build_document_content(**overrides):
    values = {
        "text": "Patient Name: Ahmed Hassan\nMRN: 12345",
        "source_name": "report.txt",
        "media_type": "text/plain",
        "extension": ".txt",
        "file_size": 42,
        "encoding": "utf-8",
        "metadata": {
            "extractor": "txt",
        },
        "warnings": (),
    }

    values.update(overrides)

    return DocumentContent(**values)


def test_document_content_can_be_created():
    content = build_document_content()

    assert content.text == (
        "Patient Name: Ahmed Hassan\nMRN: 12345"
    )
    assert content.source_name == "report.txt"
    assert content.media_type == "text/plain"
    assert content.extension == ".txt"
    assert content.file_size == 42
    assert content.encoding == "utf-8"


def test_document_content_normalizes_extension():
    content = build_document_content(
        extension="TXT",
    )

    assert content.extension == ".txt"


def test_document_content_normalizes_media_type():
    content = build_document_content(
        media_type="  TEXT/PLAIN  ",
    )

    assert content.media_type == "text/plain"


def test_document_content_normalizes_encoding():
    content = build_document_content(
        encoding="  UTF-8  ",
    )

    assert content.encoding == "utf-8"


def test_document_content_converts_empty_encoding_to_none():
    content = build_document_content(
        encoding="   ",
    )

    assert content.encoding is None


def test_document_content_calculates_line_count():
    content = build_document_content(
        text="Line 1\nLine 2\nLine 3",
        line_count=None,
    )

    assert content.line_count == 3


def test_document_content_empty_text_has_zero_lines():
    content = build_document_content(
        text="",
        line_count=None,
    )

    assert content.line_count == 0


def test_document_content_uses_explicit_line_count():
    content = build_document_content(
        line_count=25,
    )

    assert content.line_count == 25


def test_document_content_reports_character_count():
    content = build_document_content(
        text="ABC123",
    )

    assert content.character_count == 6


def test_document_content_detects_empty_content():
    content = build_document_content(
        text="   \n\t",
    )

    assert content.is_empty is True


def test_document_content_detects_non_empty_content():
    content = build_document_content(
        text="Clinical report",
    )

    assert content.is_empty is False


def test_document_content_detects_warnings():
    content = build_document_content(
        warnings=(
            "Encoding fallback was used.",
        ),
    )

    assert content.has_warnings is True


def test_document_content_without_warnings():
    content = build_document_content(
        warnings=(),
    )

    assert content.has_warnings is False


def test_document_content_normalizes_warnings():
    content = build_document_content(
        warnings=(
            "  First warning  ",
            "",
            "   ",
            "Second warning",
        ),
    )

    assert content.warnings == (
        "First warning",
        "Second warning",
    )


def test_document_content_metadata_is_read_only():
    content = build_document_content()

    with pytest.raises(TypeError):
        content.metadata["new_key"] = "new_value"


def test_document_content_copies_source_metadata():
    source_metadata = {
        "extractor": "txt",
    }

    content = build_document_content(
        metadata=source_metadata,
    )

    source_metadata["extractor"] = "modified"

    assert content.metadata["extractor"] == "txt"


def test_document_content_is_immutable():
    content = build_document_content()

    with pytest.raises(FrozenInstanceError):
        content.text = "Modified text"


def test_document_content_rejects_non_string_text():
    with pytest.raises(
        TypeError,
        match="text must be a string",
    ):
        build_document_content(
            text=123,
        )


def test_document_content_rejects_empty_source_name():
    with pytest.raises(
        ValueError,
        match="source_name must not be empty",
    ):
        build_document_content(
            source_name="   ",
        )


def test_document_content_rejects_empty_media_type():
    with pytest.raises(
        ValueError,
        match="media_type must not be empty",
    ):
        build_document_content(
            media_type=" ",
        )


def test_document_content_rejects_empty_extension():
    with pytest.raises(
        ValueError,
        match="extension must not be empty",
    ):
        build_document_content(
            extension=" ",
        )


def test_document_content_rejects_negative_file_size():
    with pytest.raises(
        ValueError,
        match="file_size must not be negative",
    ):
        build_document_content(
            file_size=-1,
        )


def test_document_content_rejects_boolean_file_size():
    with pytest.raises(
        TypeError,
        match="file_size must be an integer",
    ):
        build_document_content(
            file_size=True,
        )


def test_document_content_rejects_zero_page_count():
    with pytest.raises(
        ValueError,
        match=(
            "page_count must be greater than "
            "or equal to 1"
        ),
    ):
        build_document_content(
            page_count=0,
        )


def test_document_content_accepts_valid_page_count():
    content = build_document_content(
        page_count=3,
    )

    assert content.page_count == 3


def test_document_content_rejects_negative_line_count():
    with pytest.raises(
        ValueError,
        match=(
            "line_count must be greater than "
            "or equal to 0"
        ),
    ):
        build_document_content(
            line_count=-1,
        )


def test_document_content_rejects_non_mapping_metadata():
    with pytest.raises(
        TypeError,
        match="metadata must be a mapping",
    ):
        build_document_content(
            metadata=["invalid"],
        )


def test_document_content_rejects_warning_string():
    with pytest.raises(
        TypeError,
        match="not a single string",
    ):
        build_document_content(
            warnings="One warning",
        )


def test_document_content_rejects_non_string_warning():
    with pytest.raises(
        TypeError,
        match="Every warning must be a string",
    ):
        build_document_content(
            warnings=(
                "Valid warning",
                123,
            ),
        )