from backend.app.modules.medical_document_intelligence.policies.protected_terms import (
    PROTECTED_TERMS,
)


def test_pathology_terms_exist():

    assert "gross_description" in PROTECTED_TERMS

    assert "white" in PROTECTED_TERMS["gross_description"]

    assert "firm" in PROTECTED_TERMS["gross_description"]

    assert "microscopic_description" in PROTECTED_TERMS

    assert "carcinoma" in PROTECTED_TERMS["diagnosis"]