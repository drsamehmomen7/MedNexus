from backend.app.modules.medical_document_intelligence.policies.policy_engine import (
    PolicyEngine,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)
from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)


def test_hash_policy():
    result = PolicyEngine.transform_value(
        value="MRN-998122",
        entity=MedicalContextEntity.MRN,
        profile=PolicyProfile.RESEARCH,
    )

    assert result.startswith("[MRN:")
    assert result.endswith("]")


def test_replace_policy():
    result = PolicyEngine.transform_value(
        value="Mariam Saleh",
        entity=MedicalContextEntity.PATIENT_NAME,
        profile=PolicyProfile.MEDNEXUS_DEFAULT,
    )

    assert result == "[PATIENT_NAME]"


def test_strict_privacy_removes_specimen_number():
    result = PolicyEngine.transform_value(
        value="SP-2026-77881",
        entity=MedicalContextEntity.SPECIMEN_NUMBER,
        profile=PolicyProfile.STRICT_PRIVACY,
    )

    assert result == "[REMOVED]"