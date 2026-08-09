import hashlib

from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    POLICY_RULES,
    PolicyProfile,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)


class PolicyEngine:
    """
    Resolves and applies MedNexus de-identification policy actions.
    """

    @staticmethod
    def get_action(
        entity,
        profile: PolicyProfile = PolicyProfile.MEDNEXUS_DEFAULT,
    ) -> PolicyAction:
        rules = POLICY_RULES.get(profile, {})
        return rules.get(entity, PolicyAction.KEEP)

    @staticmethod
    def stable_hash(value: str) -> str:
        """
        Generate a stable short hash for repeatable pseudonymization.
        """
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[:10]

    @classmethod
    def transform_value(
        cls,
        value: str,
        entity,
        profile: PolicyProfile,
    ) -> str:
        """
        Apply the configured policy action to a detected value.
        """
        action = cls.get_action(entity, profile)

        if action == PolicyAction.KEEP:
            return value

        if action == PolicyAction.REPLACE:
            return f"[{entity.value.upper()}]"

        if action == PolicyAction.HASH:
            return f"[{entity.value.upper()}:{cls.stable_hash(value)}]"

        if action == PolicyAction.MASK:
            if len(value) <= 4:
                return "*" * len(value)

            return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"

        if action == PolicyAction.GENERALIZE:
            return f"[GENERALIZED_{entity.value.upper()}]"

        if action == PolicyAction.SHIFT_DATE:
            # Date shifting will be implemented consistently
            # in a dedicated temporal transformer.
            return f"[SHIFTED_{entity.value.upper()}]"

        if action == PolicyAction.REMOVE:
            return "[REMOVED]"

        return value