import hashlib

from backend.app.modules.medical_document_intelligence.intelligence.candidate_entity import (
    CandidateEntityType,
)
from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)

from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
    get_policy_definition,
    resolve_policy_profile,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)


class PolicyEngine:
    """
    Resolves and applies MedNexus de-identification policy actions.
    """

    IMPLEMENTED_ACTIONS = frozenset(
        {
            PolicyAction.KEEP,
            PolicyAction.REPLACE,
            PolicyAction.HASH,
            PolicyAction.MASK,
            PolicyAction.REMOVE,
        }
    )

    @staticmethod
    def get_rule(
        entity,
        profile: PolicyProfile | str = PolicyProfile.MEDNEXUS_CLINICAL,
        *,
        require_mapping: bool = False,
    ):
        target = PolicyEngine._normalize_policy_target(entity)
        definition = get_policy_definition(profile)
        rule = definition.rules.get(target) if target is not None else None
        if rule is not None:
            return rule
        if require_mapping:
            raise ValueError(
                f"No policy action is configured for target: {entity}."
            )
        return None

    @staticmethod
    def get_action(
        entity,
        profile: PolicyProfile | str = PolicyProfile.MEDNEXUS_CLINICAL,
        *,
        require_mapping: bool = False,
    ) -> PolicyAction:
        rule = PolicyEngine.get_rule(
            entity,
            profile,
            require_mapping=require_mapping,
        )
        return rule.action if rule is not None else PolicyAction.KEEP

    @staticmethod
    def stable_hash(value: str, length: int = 10) -> str:
        """
        Generate a stable short hash for repeatable pseudonymization.
        """
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
        return digest[:length]

    @classmethod
    def transform_value(
        cls,
        value: str,
        entity,
        profile: PolicyProfile | str,
        *,
        require_mapping: bool = False,
        hash_length: int = 10,
    ) -> str:
        """
        Apply the configured policy action to a detected value.
        """
        target = cls._normalize_policy_target(entity)
        profile = resolve_policy_profile(profile)
        action = cls.get_action(
            target,
            profile,
            require_mapping=require_mapping,
        )

        if action not in cls.IMPLEMENTED_ACTIONS:
            raise NotImplementedError(
                f"Policy action '{action.value}' is planned but not implemented."
            )

        if action == PolicyAction.KEEP:
            return value

        if action == PolicyAction.REPLACE:
            return f"[{target.upper()}]"

        if action == PolicyAction.HASH:
            return (
                f"[{target.upper()}:"
                f"{cls.stable_hash(value, hash_length)}]"
            )

        if action == PolicyAction.MASK:
            if len(value) <= 4:
                return "*" * len(value)

            return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"

        if action == PolicyAction.REMOVE:
            return "[REMOVED]"

        return value

    @staticmethod
    def _normalize_policy_target(entity) -> str | None:
        if isinstance(entity, CandidateEntityType):
            return entity.value
        if isinstance(entity, MedicalContextEntity):
            try:
                return CandidateEntityType(entity.value).value
            except ValueError:
                if entity == MedicalContextEntity.HOSPITAL:
                    return CandidateEntityType.ORGANIZATION.value
                if entity == MedicalContextEntity.UNKNOWN_PII:
                    return CandidateEntityType.UNKNOWN.value
                return None
        if isinstance(entity, str):
            normalized = entity.strip().lower()
            return normalized or None
        return None
