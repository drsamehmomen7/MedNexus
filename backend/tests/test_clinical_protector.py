from backend.app.modules.medical_document_intelligence.policies.clinical_context import (
    ClinicalContextProtector,
)


def test_protect_terms_only_inside_gross_description():
    text = """
Patient:
White male

Gross Description

Irregular white firm tissue.
"""

    protected_text, mapping = ClinicalContextProtector.protect(text)

    assert "White male" in protected_text

    assert "__CTX_0001__" in protected_text
    assert "__CTX_0002__" in protected_text
    assert "__CTX_0003__" in protected_text

    assert "white firm tissue" not in protected_text.lower()

    assert set(mapping.values()) == {
        "white",
        "firm",
        "tissue",
    }


def test_restore_protected_clinical_terms():
    original_text = """
Gross Description

Irregular white firm tissue.
"""

    protected_text, mapping = ClinicalContextProtector.protect(
        original_text
    )

    restored_text = ClinicalContextProtector.restore(
        protected_text,
        mapping,
    )

    assert restored_text == original_text