from backend.app.modules.medical_document_intelligence.policies.placeholder_protector import (
    PlaceholderProtector,
)


def test_protect_mednexus_placeholders():
    text = """
Patient:
[PATIENT_NAME]

Civil ID:
[CIVIL_ID:21ac847bf2]

MRN:
[MRN:94d3f12a08]

Specimen Number:
[SPECIMEN_NUMBER:70ac0f13e4]
"""

    protected_text, mapping = PlaceholderProtector.protect(text)

    assert "[PATIENT_NAME]" not in protected_text
    assert "[CIVIL_ID:21ac847bf2]" not in protected_text
    assert "[MRN:94d3f12a08]" not in protected_text
    assert "[SPECIMEN_NUMBER:70ac0f13e4]" not in protected_text

    assert "__MNX_PLACEHOLDER_0001__" in protected_text
    assert "__MNX_PLACEHOLDER_0002__" in protected_text

    assert len(mapping) == 4


def test_restore_mednexus_placeholders():
    original_text = """
Patient:
[PATIENT_NAME]

MRN:
[MRN:94d3f12a08]
"""

    protected_text, mapping = PlaceholderProtector.protect(
        original_text
    )

    restored_text = PlaceholderProtector.restore(
        protected_text,
        mapping,
    )

    assert restored_text == original_text