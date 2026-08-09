from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def create_temp_txt(tmp_path: Path) -> Path:
    file_path = tmp_path / "sample.txt"

    file_path.write_text(
        """Patient:
John Smith

MRN:
123456

Diagnosis:
Hypertension
""",
        encoding="utf-8",
    )

    return file_path


def test_upload_txt_file(tmp_path):

    file_path = create_temp_txt(tmp_path)

    with open(file_path, "rb") as f:

        response = client.post(
            "/api/v1/document/deidentify/file",
            files={
                "file": (
                    file_path.name,
                    f,
                    "text/plain",
                )
            },
            data={
                "policy": "mednexus_default",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert data["error"] is None

    assert data["module"] == "medical_document_intelligence"

    assert data["task"] == "File De-identification"

    assert "engine" in data

    assert "metadata" in data

    assert "context_entities" in data

    assert "result" in data

    result = data["result"]

    assert "original_text" in result

    assert "deidentified_text" in result

    assert "entities" in result

    assert "mapping" in result

    document = data["metadata"]["document"]

    assert document["source_name"] == "sample.txt"

    assert document["extension"] == ".txt"

    assert document["media_type"] == "text/plain"


def test_invalid_policy(tmp_path):

    file_path = create_temp_txt(tmp_path)

    with open(file_path, "rb") as f:

        response = client.post(
            "/api/v1/document/deidentify/file",
            files={
                "file": (
                    file_path.name,
                    f,
                    "text/plain",
                )
            },
            data={
                "policy": "unknown_policy",
            },
        )

    assert response.status_code == 400


def test_missing_file():

    response = client.post(
        "/api/v1/document/deidentify/file",
        data={
            "policy": "mednexus_default",
        },
    )

    assert response.status_code == 422