from __future__ import annotations

import hashlib
from io import BytesIO
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.app.main import app
from backend.app.modules.medical_document_intelligence.contracts.protection import (
    build_protect_output,
)
from backend.app.modules.medical_document_intelligence.api import (
    understanding as understanding_api,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)
from backend.app.modules.medical_document_intelligence.services.protected_document_builder import (
    ProtectedDocumentBuilder,
)


client = TestClient(app)


def _source_pdf(*lines: str) -> bytes:
    output = BytesIO()
    document = canvas.Canvas(output, pagesize=letter)
    y = 740
    for line in lines:
        if y < 60:
            document.showPage()
            y = 740
        document.drawString(54, y, line)
        y -= 16
    document.save()
    return output.getvalue()


def _create_batch() -> str:
    response = client.post(
        "/api/v1/understanding/journey-runs", json={"mode": "batch"}
    )
    assert response.status_code == 200
    return response.json()["run_id"]


def _add_pdf(run_id: str, order: int, filename: str, content: bytes):
    return client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/documents",
        data={"order": str(order)},
        files={"file": (filename, content, "application/pdf")},
    )


class ControlledPrivacyService:
    def process(self, text, policy):
        if "CONTROLLED FAILURE" in text:
            raise RuntimeError("controlled artifact isolation failure")
        protected = text.replace("Nadia Hassan", "[PATIENT_NAME]").replace(
            "99887766", "[MRN]"
        )
        return SimpleNamespace(
            success=True,
            data=SimpleNamespace(deidentified_text=protected),
            metadata={
                "requires_review": False,
                "candidate_counts": {
                    "total": 2,
                    "accepted": 2,
                    "rejected": 0,
                    "review_required": 0,
                    "pending": 0,
                },
                "intelligence_result": {"accepted": []},
                "output_owner": "MedNexus",
                "external_engine_role": "candidate_detector",
                "privacy_decision_path": "unified",
            },
            engine_name="controlled",
            engine_version="1.0",
            processing_time=0.001,
        )


class IncompletePrivacyService:
    def process(self, text, policy):
        return SimpleNamespace(
            success=True,
            data=SimpleNamespace(deidentified_text=text),
            metadata={
                "requires_review": True,
                "protection_complete": False,
                "protection_blockers": [
                    {
                        "semantic_role": "patient_name",
                        "canonical_type": "patient_name",
                        "start": 31,
                        "end": 43,
                        "required_action": "replace",
                    }
                ],
                "candidate_counts": {
                    "total": 1,
                    "accepted": 0,
                    "rejected": 0,
                    "review_required": 1,
                    "pending": 0,
                },
                "intelligence_result": {"accepted": []},
                "output_owner": "MedNexus",
                "external_engine_role": "candidate_detector",
                "privacy_decision_path": "unified",
            },
            engine_name="controlled",
            engine_version="1.0",
            processing_time=0.001,
        )


class ReviewablePrivacyService(ControlledPrivacyService):
    def process(self, text, policy):
        response = super().process(text, policy)
        response.metadata["requires_review"] = True
        response.metadata["protection_complete"] = True
        response.metadata["candidate_counts"]["review_required"] = 1
        return response


def test_review_signal_summary_is_typed_human_readable_and_phi_safe():
    response = SimpleNamespace(
        success=True,
        data=SimpleNamespace(deidentified_text="Protected clinical report."),
        metadata={
            "requires_review": True,
            "candidate_counts": {"review_required": 3, "pending": 1},
            "intelligence_result": {
                "accepted": [],
                "review_required": [
                    {
                        "text": "Sensitive Person",
                        "canonical_type": "patient_name",
                        "source": "openmed",
                        "confidence": 0.51,
                    },
                    {
                        "text": "04/05/2026",
                        "canonical_type": "general_date",
                        "source": "openmed",
                    },
                    {
                        "text": "Unresolved value",
                        "canonical_type": "unknown",
                        "source": "openmed",
                    },
                ],
                "pending": [
                    {
                        "text": "Possible Name",
                        "canonical_type": "person_name",
                        "source": "openmed",
                    }
                ],
            },
            "output_owner": "MedNexus",
            "external_engine_role": "candidate_detector",
            "privacy_decision_path": "unified",
        },
        engine_name="controlled",
        engine_version="1.0",
        processing_time=0.001,
    )

    output = build_protect_output(
        report_id="review-contract",
        response=response,
        policy=PolicyProfile.MEDNEXUS_CLINICAL,
    ).to_dict()
    summaries = output["protection_result"]["review_signal_summary"]

    assert {
        (item["category"], item["human_label"], item["count"])
        for item in summaries
    } == {
        ("ambiguous_date_time", "Ambiguous date/time signal", 1),
        ("clinical_person_ambiguity", "Clinical-term/person ambiguity", 1),
        ("possible_person_name", "Possible person-name signal", 1),
        (
            "unclassified_identity_like",
            "Unclassified identity-like signal",
            1,
        ),
    }
    serialized = json.dumps(summaries).lower()
    assert "sensitive person" not in serialized
    assert "possible name" not in serialized
    assert "04/05/2026" not in serialized
    assert "openmed" not in serialized
    assert "confidence" not in serialized


def test_protected_pdf_builder_preserves_long_content_across_pages():
    protected_text = "\n".join(
        [
            "RADIOLOGY REPORT",
            "FINDINGS:",
            *(
                f"Clinical observation line {index:03d} remains available for care."
                for index in range(320)
            ),
            "IMPRESSION:",
            "No acute cardiopulmonary abnormality.",
        ]
    )

    artifact = ProtectedDocumentBuilder().build_pdf(
        source_filename='Unsafe:Report?.pdf',
        protected_text=protected_text,
    )
    reader = PdfReader(BytesIO(artifact.content))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert artifact.filename == "Unsafe_Report_PROTECTED.pdf"
    assert artifact.media_type == "application/pdf"
    assert artifact.page_count == len(reader.pages)
    assert artifact.page_count > 1
    assert "Clinical observation line 000 remains available for care." in extracted
    assert "Clinical observation line 319 remains available for care." in extracted
    assert "No acute cardiopulmonary abnormality." in extracted
    assert artifact.integrity_sha256 == hashlib.sha256(artifact.content).hexdigest()
    assert artifact.provenance["strategy"] == "deterministic_text_rebuild"
    assert artifact.provenance["content_authority"] == "protected_text"


def test_pdf_journey_builds_non_cacheable_protected_artifact_without_mutating_source(
    monkeypatch, caplog
):
    monkeypatch.setattr(
        understanding_api,
        "privacy_service",
        ControlledPrivacyService(),
    )
    source = _source_pdf(
        "RADIOLOGY REPORT",
        "Patient Name: Nadia Hassan",
        "MRN: 99887766",
        "EXAMINATION: CT chest",
        "TECHNIQUE: Axial images were obtained.",
        "FINDINGS: The lungs are clear.",
        "IMPRESSION: No acute finding.",
    )
    source_digest = hashlib.sha256(source).hexdigest()
    run_id = _create_batch()
    added = _add_pdf(run_id, 0, "clinical-report.pdf", source)
    assert added.status_code == 200
    document_id = added.json()["documents"][0]["document_id"]

    unavailable = client.get(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/protected-artifact"
    )
    assert unavailable.status_code == 409

    protected = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert protected.status_code == 200
    result = protected.json()["documents"][0]["stage_results"]["PROTECT"]
    artifact = result["protected_document"]["artifact"]
    assert artifact["availability"] is True
    assert artifact["media_type"] == "application/pdf"
    assert artifact["filename"] == "clinical-report_PROTECTED.pdf"
    assert artifact["page_count"] >= 1
    assert artifact["provenance"]["content_authority"] == "protected_text"
    assert "%PDF" not in json.dumps(result)

    artifact_response = client.get(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/protected-artifact"
    )
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"] == "application/pdf"
    assert artifact_response.headers["cache-control"] == "no-store, private"
    assert artifact_response.headers["pragma"] == "no-cache"
    assert artifact_response.headers["expires"] == "0"
    assert artifact_response.headers["x-content-type-options"] == "nosniff"
    assert "clinical-report_PROTECTED.pdf" in artifact_response.headers["content-disposition"]

    reader = PdfReader(BytesIO(artifact_response.content))
    protected_pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Nadia Hassan" not in protected_pdf_text
    assert "99887766" not in protected_pdf_text
    assert "The lungs are clear." in protected_pdf_text
    assert "No acute finding." in protected_pdf_text

    original_response = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/compare-artifact"
    )
    assert original_response.status_code == 200
    assert original_response.content == source
    assert hashlib.sha256(original_response.content).hexdigest() == source_digest
    assert original_response.headers["cache-control"] == "no-store, private"
    assert "Nadia Hassan" not in caplog.text
    assert "99887766" not in caplog.text
    assert "%PDF" not in caplog.text


def test_failed_batch_report_does_not_prevent_independent_protected_pdfs(monkeypatch):
    monkeypatch.setattr(
        understanding_api,
        "privacy_service",
        ControlledPrivacyService(),
    )
    run_id = _create_batch()
    sources = (
        _source_pdf(
            "RADIOLOGY REPORT", "EXAMINATION: CT chest", "TECHNIQUE: Axial images.",
            "FINDINGS: Clear lungs.", "IMPRESSION: No acute finding.", "REPORT: ONE",
        ),
        _source_pdf(
            "RADIOLOGY REPORT", "EXAMINATION: CT chest", "TECHNIQUE: Axial images.",
            "FINDINGS: Clear lungs.", "IMPRESSION: No acute finding.", "CONTROLLED FAILURE",
        ),
        _source_pdf(
            "RADIOLOGY REPORT", "EXAMINATION: CT chest", "TECHNIQUE: Axial images.",
            "FINDINGS: Clear lungs.", "IMPRESSION: No acute finding.", "REPORT: THREE",
        ),
    )
    for index, source in enumerate(sources):
        assert _add_pdf(run_id, index, f"report-{index + 1}.pdf", source).status_code == 200

    protected = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert protected.status_code == 200
    payload = protected.json()
    assert [
        item["stage_status"]["PROTECT"]["status"] for item in payload["documents"]
    ] == ["COMPLETE", "FAILED", "COMPLETE"]
    assert payload["protection_summary"]["complete"] == 2
    assert payload["protection_summary"]["failed"] == 1

    for index in (0, 2):
        document_id = payload["documents"][index]["document_id"]
        response = client.get(
            f"/api/v1/understanding/journey-runs/{run_id}/documents/{document_id}/protected-artifact"
        )
        assert response.status_code == 200
        assert response.content.startswith(b"%PDF")
    failed_id = payload["documents"][1]["document_id"]
    assert client.get(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/{failed_id}/protected-artifact"
    ).status_code == 409


def test_incomplete_protection_blocks_pdf_artifact_and_downstream_use(monkeypatch):
    monkeypatch.setattr(
        understanding_api,
        "privacy_service",
        IncompletePrivacyService(),
    )
    source = _source_pdf(
        "RADIOLOGY REPORT",
        "Patient Name: Nadia Hassan",
        "EXAMINATION: CT chest",
        "FINDINGS: The lungs are clear.",
        "IMPRESSION: No acute finding.",
    )
    run_id = _create_batch()
    added = _add_pdf(run_id, 0, "incomplete-protection.pdf", source)
    assert added.status_code == 200
    document_id = added.json()["documents"][0]["document_id"]

    protected = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert protected.status_code == 200
    document = protected.json()["documents"][0]
    output = document["stage_results"]["PROTECT"]

    assert document["stage_status"]["PROTECT"]["status"] == "BLOCKED"
    assert document["stage_status"]["EXTRACT"]["status"] == "BLOCKED"
    assert document["review_status"] == "BLOCKED"
    assert output["protection_result"]["status"] == "BLOCKED"
    assert output["protection_result"]["review_required"] is True
    assert output["protected_document"]["artifact"] is None
    assert client.get(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/"
        f"{document_id}/protected-artifact"
    ).status_code == 409


def test_reviewable_safe_protected_pdf_does_not_block_extract_input(monkeypatch):
    monkeypatch.setattr(
        understanding_api,
        "privacy_service",
        ReviewablePrivacyService(),
    )
    source = _source_pdf(
        "RADIOLOGY REPORT",
        "Patient Name: Nadia Hassan",
        "MRN: 99887766",
        "EXAMINATION: CT chest",
        "TECHNIQUE: Axial images were obtained.",
        "FINDINGS: The lungs are clear.",
        "IMPRESSION: No acute finding.",
    )
    run_id = _create_batch()
    added = _add_pdf(run_id, 0, "reviewable-report.pdf", source)
    assert added.status_code == 200
    document_id = added.json()["documents"][0]["document_id"]

    protected = client.post(
        f"/api/v1/understanding/journey-runs/{run_id}/protect",
        json={"policy": "mednexus_clinical"},
    )
    assert protected.status_code == 200
    document = protected.json()["documents"][0]
    artifact = document["stage_results"]["PROTECT"]["protected_document"]["artifact"]

    assert document["stage_status"]["UNDERSTAND"]["status"] == "COMPLETE"
    assert document["stage_status"]["PROTECT"]["status"] == "NEEDS_REVIEW"
    assert document["stage_status"]["EXTRACT"]["status"] == "NOT_STARTED"
    assert "EXTRACT" not in document["stage_results"]
    assert artifact["availability"] is True
    assert artifact["integrity_sha256"]
    assert client.get(
        f"/api/v1/understanding/journey-runs/{run_id}/documents/"
        f"{document_id}/protected-artifact"
    ).status_code == 200
