import pytest

from backend.app.modules.medical_document_intelligence.policies.clinical_context import (
    ClinicalContextDetector,
    ClinicalContextProtector,
)


def test_detector_detects_authorized_by_as_consultant_section():
    text = (
        "Laboratory Report\n"
        "Authorized By\n"
        "Dr. Rania Al-Haddad\n"
        "Consultant Clinical Pathologist\n"
    )

    detected_sections = ClinicalContextDetector.detect(text)

    assert "consultant" in detected_sections


def test_protector_rejects_non_string_text():
    with pytest.raises(
        TypeError,
        match="Text must be a string.",
    ):
        ClinicalContextProtector.protect(None)


def test_protects_clinical_pathologist_in_laboratory_report():
    text = (
        "Authorized By\n"
        "Dr. Rania Al-Haddad\n"
        "Consultant Clinical Pathologist\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(
        text,
        document_type="laboratory_report",
    )

    assert "Consultant Clinical Pathologist" not in protected_text
    assert "__CTX_0001__" in protected_text

    assert "Consultant Clinical Pathologist" in mapping.values()


def test_protects_pathologist_without_explicit_document_type():
    text = (
        "Authorized By\n"
        "Dr. Rania Al-Haddad\n"
        "Consultant Clinical Pathologist\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(text)

    assert "Consultant Clinical Pathologist" not in protected_text
    assert "__CTX_" in protected_text

    assert "Consultant Clinical Pathologist" in mapping.values()


def test_protects_pathology_diagnosis_term():
    text = (
        "Final Diagnosis\n"
        "Invasive Carcinoma is identified.\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(
        text,
        document_type="pathology_report",
    )

    assert "Invasive Carcinoma" not in protected_text
    assert "__CTX_0001__" in protected_text

    assert mapping["__CTX_0001__"] == "Invasive Carcinoma"


def test_protects_pathology_term_using_section_fallback():
    text = (
        "Final Diagnosis\n"
        "Invasive Carcinoma is identified.\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(text)

    assert "Invasive Carcinoma" not in protected_text
    assert "Invasive Carcinoma" in mapping.values()


def test_protects_common_clinical_occupations():
    text = (
        "Consultant\n"
        "Consultant Physician\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(text)

    assert "Consultant Physician" not in protected_text
    assert "Consultant" in mapping.values()
    assert "Physician" in mapping.values()


def test_preserves_section_heading():
    text = (
        "Authorized By\n"
        "Consultant Clinical Pathologist\n"
    )

    protected_text, _ = ClinicalContextProtector.protect(
        text,
        document_type="laboratory_report",
    )

    assert protected_text.startswith("Authorized By\n")


def test_preserves_line_breaks():
    text = (
        "Final Diagnosis\r\n"
        "Invasive Carcinoma.\r\n"
    )

    protected_text, _ = ClinicalContextProtector.protect(
        text,
        document_type="pathology_report",
    )

    assert protected_text.count("\r\n") == 2


def test_restores_protected_laboratory_vocabulary():
    text = (
        "Authorized By\n"
        "Consultant Clinical Pathologist\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(
        text,
        document_type="laboratory_report",
    )

    restored_text = ClinicalContextProtector.restore(
        protected_text,
        mapping,
    )

    assert restored_text == text


def test_restores_multiple_protected_terms():
    text = (
        "Consultant\n"
        "Consultant Physician\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(text)

    restored_text = ClinicalContextProtector.restore(
        protected_text,
        mapping,
    )

    assert restored_text == text


def test_does_not_apply_pathology_vocabulary_to_patient_information():
    text = (
        "Patient Information\n"
        "Occupation: Pathologist\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(
        text,
        document_type="pathology_report",
    )

    assert "Pathologist" in protected_text
    assert "Pathologist" not in mapping.values()


def test_explicit_wrong_document_type_does_not_use_laboratory_profile():
    text = (
        "Authorized By\n"
        "Clinical Microbiologist\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(
        text,
        document_type="radiology_report",
    )

    assert "Clinical Microbiologist" in protected_text
    assert "Clinical Microbiologist" not in mapping.values()


def test_token_numbers_are_sequential():
    text = (
        "Consultant\n"
        "Consultant Physician\n"
    )

    protected_text, mapping = ClinicalContextProtector.protect(text)

    assert "__CTX_0001__" in protected_text
    assert "__CTX_0002__" in protected_text

    assert list(mapping.keys()) == [
        "__CTX_0001__",
        "__CTX_0002__",
    ]