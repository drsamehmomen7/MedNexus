from backend.app.modules.medical_document_intelligence.policies.clinical_context import (
    ClinicalContextDetector,
)


def test_detect_pathology_sections():

    report = """
Patient:
John Smith

Gross Description

Irregular white firm tissue.

Microscopic Description

Invasive ductal carcinoma.

Final Diagnosis

Breast carcinoma.
"""

    sections = ClinicalContextDetector.detect(report)

    assert "patient_information" in sections
    assert "gross_description" in sections
    assert "microscopic_description" in sections
    assert "diagnosis" in sections