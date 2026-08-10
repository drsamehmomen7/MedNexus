from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)

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


def _fake_text_processing_response(text):
    return SimpleNamespace(
        success=True,
        message="ok",
        error=None,
        module_name="medical_document_intelligence",
        engine_name="OpenMed",
        engine_version="test",
        processing_time=0.0,
        warnings=[],
        metadata={},
        context_entities=[],
        data=SimpleNamespace(
            original_text=text,
            deidentified_text=text,
            pii_entities=[],
            mapping={},
        ),
    )


def test_text_only_request_defaults_to_clinical(monkeypatch):
    selected = []

    def process(text, policy):
        selected.append(policy)
        return _fake_text_processing_response(text)

    monkeypatch.setattr(
        "backend.app.modules.medical_document_intelligence.api.deidentification.service.process",
        process,
    )

    response = client.post(
        "/api/v1/document/deidentify",
        json={"text": "Diagnosis: Pneumonia"},
    )

    assert response.status_code == 200
    assert selected == [PolicyProfile.MEDNEXUS_CLINICAL]


@pytest.mark.parametrize(
    ("policy_id", "expected"),
    [
        ("mednexus_research", PolicyProfile.MEDNEXUS_RESEARCH),
        (
            "mednexus_analytics_public_health",
            PolicyProfile.MEDNEXUS_ANALYTICS_PUBLIC_HEALTH,
        ),
        (
            "mednexus_strict_privacy",
            PolicyProfile.MEDNEXUS_STRICT_PRIVACY,
        ),
        ("research", PolicyProfile.MEDNEXUS_RESEARCH),
    ],
)
def test_text_api_resolves_supported_policy_ids(
    monkeypatch,
    policy_id,
    expected,
):
    selected = []

    def process(text, policy):
        selected.append(policy)
        return _fake_text_processing_response(text)

    monkeypatch.setattr(
        "backend.app.modules.medical_document_intelligence.api.deidentification.service.process",
        process,
    )

    response = client.post(
        "/api/v1/document/deidentify",
        json={
            "text": "Diagnosis: Pneumonia",
            "policy": policy_id,
        },
    )

    assert response.status_code == 200
    assert selected == [expected]


def test_text_api_rejects_invalid_policy(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("service must not run for an invalid policy")

    monkeypatch.setattr(
        "backend.app.modules.medical_document_intelligence.api.deidentification.service.process",
        fail_if_called,
    )

    response = client.post(
        "/api/v1/document/deidentify",
        json={
            "text": "Diagnosis: Pneumonia",
            "policy": "unknown_policy",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported policy: unknown_policy"
