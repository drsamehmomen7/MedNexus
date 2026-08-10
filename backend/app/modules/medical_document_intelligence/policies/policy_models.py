from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)


@dataclass(frozen=True)
class PolicyRule:
    """One purpose-based privacy rule resolved by a canonical target key."""

    action: PolicyAction
    rationale: str = ""
    parameters: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.action, PolicyAction):
            raise TypeError("action must be a PolicyAction.")
        object.__setattr__(
            self,
            "parameters",
            MappingProxyType(dict(self.parameters)),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "rationale": self.rationale,
            "parameters": dict(self.parameters),
        }


@dataclass(frozen=True)
class PolicyDefinition:
    """Executable rules plus purpose-of-use metadata for one profile."""

    profile_id: str
    display_name: str
    intended_use: str
    privacy_level: str
    analytical_utility: str
    selection_guidance: str
    rules: Mapping[str, PolicyRule]
    implemented_capabilities: tuple[str, ...] = (
        "keep",
        "replace",
        "hash",
        "mask",
        "remove",
    )
    planned_capabilities: tuple[str, ...] = (
        "generalize",
        "shift_date",
        "age_band",
        "geographic_reduction",
        "pseudonymize",
    )

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id cannot be empty.")
        if not self.display_name.strip():
            raise ValueError("display_name cannot be empty.")
        normalized_rules = dict(self.rules)
        if not all(
            isinstance(key, str) and key.strip()
            for key in normalized_rules
        ):
            raise TypeError("Policy rule keys must be non-empty strings.")
        if not all(
            isinstance(rule, PolicyRule)
            for rule in normalized_rules.values()
        ):
            raise TypeError("Policy rules must contain PolicyRule values.")
        object.__setattr__(
            self,
            "rules",
            MappingProxyType(normalized_rules),
        )

    def to_dict(self) -> dict[str, object]:
        action_summary: dict[str, list[str]] = {}
        for target, rule in self.rules.items():
            action_summary.setdefault(rule.action.value, []).append(target)

        return {
            "id": self.profile_id,
            "display_name": self.display_name,
            "intended_use": self.intended_use,
            "privacy_level": self.privacy_level,
            "analytical_utility": self.analytical_utility,
            "selection_guidance": self.selection_guidance,
            "action_summary": action_summary,
            "capabilities": {
                "implemented": list(self.implemented_capabilities),
                "planned": list(self.planned_capabilities),
            },
        }
