from backend.app.modules.medical_document_intelligence.policies.keep_entity_protector import (
    KeepEntityProtector,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)


def test_research_policy_protects_physician_and_role():
    text = """
Pathology Department

Consultant Pathologist

Dr. Huda Al-Awadhi
"""

    protected_text, mapping = KeepEntityProtector.protect(
        text=text,
        profile=PolicyProfile.RESEARCH,
    )

    assert "Consultant Pathologist" not in protected_text
    assert "Dr. Huda Al-Awadhi" not in protected_text

    assert "__MNX_KEEP_0001__" in protected_text
    assert "__MNX_KEEP_0002__" in protected_text

    assert "Consultant Pathologist" in mapping.values()
    assert "Dr. Huda Al-Awadhi" in mapping.values()


def test_research_policy_restores_physician_and_role():
    original_text = """
Consultant Pathologist

Dr. Huda Al-Awadhi
"""

    protected_text, mapping = KeepEntityProtector.protect(
        text=original_text,
        profile=PolicyProfile.RESEARCH,
    )

    restored_text = KeepEntityProtector.restore(
        protected_text,
        mapping,
    )

    assert restored_text == original_text


def test_strict_privacy_does_not_protect_physician():
    text = """
Consultant Pathologist

Dr. Huda Al-Awadhi
"""

    protected_text, mapping = KeepEntityProtector.protect(
        text=text,
        profile=PolicyProfile.STRICT_PRIVACY,
    )

    assert protected_text == text
    assert mapping == {}