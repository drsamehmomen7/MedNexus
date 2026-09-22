from __future__ import annotations

from backend.app.modules.medical_document_intelligence.contracts.document_content import (
    DocumentContent,
)
from backend.app.modules.medical_document_intelligence.understanding.models import (
    DocumentSubtype,
    RadiologySubdomain,
)
from backend.app.modules.medical_document_intelligence.understanding.service import (
    DocumentUnderstandingService,
)


def _analyze(filename: str, text: str):
    document = DocumentContent(
        text=text,
        source_name=filename,
        media_type="text/plain",
        extension=".txt",
        file_size=len(text.encode("utf-8")),
        encoding="utf-8",
    )
    return DocumentUnderstandingService().analyze_document(document)


def _report(title: str, technique: str) -> str:
    return f"""PATIENT ID: US-P-430817
{title}
CLINICAL HISTORY: Current symptoms prompted imaging.
TECHNIQUE: {technique}
FINDINGS: The current examination was reviewed in full.
IMPRESSION: No acute abnormality.
RADIOLOGIST: Electronically authenticated.
"""


def test_us_prefixed_source_and_us_patient_id_cannot_override_xray_video_content():
    result = _analyze(
        "US_dataset_origin_case.pdf",
        _report(
            "XRAY SWALLOWING FUNCTION VIDEO",
            "Dynamic images were obtained during barium swallowing.",
        ),
    )
    decision = result.radiology_decision

    assert decision is not None
    assert decision.subdomain is RadiologySubdomain.FLUOROSCOPY
    assert result.document_subtype is DocumentSubtype.UNKNOWN
    assert all(
        not (
            signal.matched_text.casefold() == "us"
            and signal.context == "PATIENT ID: US-P-430817"
        )
        for signal in decision.frame.modality_signals
    )


def test_us_source_name_cannot_override_explicit_mri_content():
    result = _analyze(
        "US_external_source_case.pdf",
        _report(
            "MRI BRAIN",
            "T1 and T2 weighted sequences were acquired.",
        ),
    )

    assert result.radiology_decision is not None
    assert result.radiology_decision.subdomain is RadiologySubdomain.MRI
    assert result.document_subtype is DocumentSubtype.MRI


def test_ct_source_name_cannot_override_explicit_ultrasound_content():
    result = _analyze(
        "CT_external_source_case.pdf",
        _report(
            "ULTRASOUND ABDOMEN",
            "Real-time sonographic images were obtained.",
        ),
    )

    assert result.radiology_decision is not None
    assert result.radiology_decision.subdomain is RadiologySubdomain.ULTRASOUND
    assert result.document_subtype is DocumentSubtype.ULTRASOUND


def test_source_name_and_body_agreement_preserves_normal_ct_behavior():
    result = _analyze(
        "CT_current_study.pdf",
        _report(
            "CT CHEST",
            "Current axial CT images were obtained.",
        ),
    )

    assert result.radiology_decision is not None
    assert result.radiology_decision.subdomain is RadiologySubdomain.CT
    assert result.document_subtype is DocumentSubtype.CT


def test_source_name_alone_is_not_authoritative_modality_evidence():
    result = _analyze(
        "CT_filename_only.pdf",
        """CLINICAL REPORT
CLINICAL HISTORY: Current symptoms are documented.
FINDINGS: The examination narrative contains no modality identity.
IMPRESSION: Manual review is recommended.
""",
    )

    assert result.document_subtype is not DocumentSubtype.CT
    if result.radiology_decision is not None:
        assert result.radiology_decision.subdomain is not RadiologySubdomain.CT
        assert all(
            signal.matched_text.casefold() != "ct"
            for signal in result.radiology_decision.frame.modality_signals
        )
