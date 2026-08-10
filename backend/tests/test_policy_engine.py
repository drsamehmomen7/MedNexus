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


def test_candidate_type_is_directly_policy_resolvable():
    assert (
        PolicyEngine.transform_value(
            value="Dr. Ahmed Hassan",
            entity=CandidateEntityType.PHYSICIAN_NAME,
            profile=PolicyProfile.STRICT_PRIVACY,
            require_mapping=True,
        )
        == "[REMOVED]"
    )


def test_required_policy_mapping_cannot_silently_keep_unknown_input():
    with pytest.raises(ValueError, match="No policy action"):
        PolicyEngine.get_action(
            object(),
            PolicyProfile.MEDNEXUS_DEFAULT,
            require_mapping=True,
        )


def test_legacy_unknown_pii_retains_compatibility_policy():
    assert (
        PolicyEngine.get_action(
            MedicalContextEntity.UNKNOWN_PII,
            PolicyProfile.RESEARCH,
        ).value
        == "remove"
    )
import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
)
