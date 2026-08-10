import pytest

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)
from backend.app.modules.medical_document_intelligence.policies.policy_engine import (
    PolicyEngine,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    POLICY_DEFINITIONS,
    PolicyProfile,
    get_policy_definition,
    resolve_policy_profile,
)


def test_all_four_canonical_profiles_have_purpose_metadata():
    assert set(POLICY_DEFINITIONS) == {
        PolicyProfile.MEDNEXUS_CLINICAL,
        PolicyProfile.MEDNEXUS_RESEARCH,
        PolicyProfile.MEDNEXUS_ANALYTICS_PUBLIC_HEALTH,
        PolicyProfile.MEDNEXUS_STRICT_PRIVACY,
    }
    for definition in POLICY_DEFINITIONS.values():
        assert definition.intended_use
        assert definition.privacy_level
        assert definition.analytical_utility
        assert definition.selection_guidance
        assert "pseudonymize" in definition.planned_capabilities


@pytest.mark.parametrize(
    ("legacy_id", "expected"),
    [
        ("mednexus_default", PolicyProfile.MEDNEXUS_CLINICAL),
        ("research", PolicyProfile.MEDNEXUS_RESEARCH),
        ("strict_privacy", PolicyProfile.MEDNEXUS_STRICT_PRIVACY),
    ],
)
def test_legacy_policy_identifiers_resolve(legacy_id, expected):
    assert resolve_policy_profile(legacy_id) is expected


@pytest.mark.parametrize(
    ("profile", "patient_action", "clinician_action"),
    [
        (
            PolicyProfile.MEDNEXUS_CLINICAL,
            PolicyAction.REPLACE,
            PolicyAction.KEEP,
        ),
        (
            PolicyProfile.MEDNEXUS_RESEARCH,
            PolicyAction.REPLACE,
            PolicyAction.REMOVE,
        ),
        (
            PolicyProfile.MEDNEXUS_ANALYTICS_PUBLIC_HEALTH,
            PolicyAction.REPLACE,
            PolicyAction.REMOVE,
        ),
        (
            PolicyProfile.MEDNEXUS_STRICT_PRIVACY,
            PolicyAction.REMOVE,
            PolicyAction.REMOVE,
        ),
    ],
)
def test_patient_and_clinician_identity_rules(
    profile,
    patient_action,
    clinician_action,
):
    assert PolicyEngine.get_action(
        CandidateEntityType.PATIENT_NAME,
        profile,
        require_mapping=True,
    ) is patient_action
    assert PolicyEngine.get_action(
        CandidateEntityType.PHYSICIAN_NAME,
        profile,
        require_mapping=True,
    ) is clinician_action


def test_phone_and_mrn_are_explicitly_policy_controlled():
    for profile in POLICY_DEFINITIONS:
        assert PolicyEngine.get_rule(
            CandidateEntityType.PHONE_NUMBER,
            profile,
            require_mapping=True,
        )
        assert PolicyEngine.get_rule(
            CandidateEntityType.MRN,
            profile,
            require_mapping=True,
        )


def test_policy_metadata_is_serializable_for_future_frontend_use():
    metadata = get_policy_definition(
        PolicyProfile.MEDNEXUS_CLINICAL
    ).to_dict()
    assert metadata["id"] == "mednexus_clinical"
    assert metadata["action_summary"]["keep"]
    assert metadata["capabilities"]["planned"]
