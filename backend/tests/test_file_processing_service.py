from pathlib import Path

import pytest

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)
from backend.app.modules.medical_document_intelligence.services.file_processing_service import (
    FileProcessingService,
)


def create_txt(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "report.txt"
    path.write_text(
        text,
        encoding="utf-8",
    )
    return path


def test_supported_extensions():

    service = FileProcessingService()

    assert service.supported_extensions == (
        ".docx",
        ".pdf",
        ".txt",
    )


def test_supports_txt():

    service = FileProcessingService()

    assert service.supports("report.txt")


def test_supports_docx():

    service = FileProcessingService()

    assert service.supports("report.docx")


def test_supports_pdf():

    service = FileProcessingService()

    assert service.supports("report.pdf")


def test_rejects_unknown_extension():

    service = FileProcessingService()

    assert not service.supports("report.exe")


def test_extract_returns_document_content(tmp_path):

    service = FileProcessingService()

    path = create_txt(
        tmp_path,
        "Hello MedNexus",
    )

    document = service.extract(path)

    assert isinstance(
        document,
        DocumentContent,
    )

    assert document.text == "Hello MedNexus"


def test_process_returns_processing_response(tmp_path):

    service = FileProcessingService()

    path = create_txt(
        tmp_path,
        """
Patient:
Ahmed Hassan

Civil ID:
123456789012
""",
    )

    response = service.process(
        path,
        policy=PolicyProfile.RESEARCH,
    )

    assert response.success

    assert response.data is not None


def test_document_metadata_added(tmp_path):

    service = FileProcessingService()

    path = create_txt(
        tmp_path,
        "Example",
    )

    response = service.process(path)

    assert "document" in response.metadata

    metadata = response.metadata["document"]

    assert metadata["source_name"] == "report.txt"

    assert metadata["extension"] == ".txt"

    assert metadata["media_type"] == "text/plain"


def test_empty_document_rejected(tmp_path):

    service = FileProcessingService()

    path = create_txt(
        tmp_path,
        "",
    )

    with pytest.raises(
        ValueError,
    ):
        service.process(path)


def test_missing_file_raises():

    service = FileProcessingService()

    with pytest.raises(
        FileNotFoundError,
    ):
        service.process(
            "missing.txt",
        )


def test_invalid_policy_type(tmp_path):

    service = FileProcessingService()

    path = create_txt(
        tmp_path,
        "hello",
    )

    with pytest.raises(
        TypeError,
    ):
        service.process(
            path,
            policy="research",
        )