import re
from typing import Dict, Tuple

from backend.app.modules.medical_document_intelligence.policies.context_taxonomy import (
    MedicalContextEntity,
)
from backend.app.modules.medical_document_intelligence.policies.policy_actions import (
    PolicyAction,
)
from backend.app.modules.medical_document_intelligence.policies.policy_engine import (
    PolicyEngine,
)
from backend.app.modules.medical_document_intelligence.policies.policy_profiles import (
    PolicyProfile,
)


class KeepEntityProtector:
    """
    Protects entities that the selected MedNexus policy marks as KEEP.

    This prevents the underlying AI engine from replacing clinical roles,
    physician names, hospitals, or departments that MedNexus explicitly
    decided to preserve.
    """

    ENTITY_PATTERNS = {
        MedicalContextEntity.PHYSICIAN_NAME: [
            re.compile(
                r"\bDr\.?\s+[A-Z][A-Za-z'-]+"
                r"(?:\s+[A-Z][A-Za-z'-]+){1,3}\b"
            ),
        ],

        MedicalContextEntity.HOSPITAL: [
            re.compile(
                r"\b[A-Z][A-Za-z&.' -]+\s+Hospital\b"
            ),
            re.compile(
                r"\b[A-Z][A-Za-z&.' -]+\s+Medical Center\b"
            ),
        ],

        MedicalContextEntity.DEPARTMENT: [
            re.compile(
                r"^(?:Pathology|Radiology|Laboratory|"
                r"Emergency|Cardiology|Surgery|Oncology)"
                r"\s+Department$",
                re.MULTILINE | re.IGNORECASE,
            ),
        ],
    }

    CLINICAL_ROLE_PATTERNS = [
        re.compile(
            r"^(?:Consultant Pathologist|"
            r"Consultant Radiologist|"
            r"Reporting Physician|"
            r"Attending Physician|"
            r"Referring Physician)$",
            re.MULTILINE | re.IGNORECASE,
        ),
    ]

    @classmethod
    def protect(
        cls,
        text: str,
        profile: PolicyProfile,
    ) -> Tuple[str, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        protected_text = text
        token_number = 1

        def protect_pattern(
            source_text: str,
            pattern: re.Pattern,
        ) -> str:
            nonlocal token_number

            def replace_match(match: re.Match) -> str:
                nonlocal token_number

                token = f"__MNX_KEEP_{token_number:04d}__"
                mapping[token] = match.group(0)
                token_number += 1

                return token

            return pattern.sub(replace_match, source_text)

        for entity, patterns in cls.ENTITY_PATTERNS.items():
            action = PolicyEngine.get_action(
                entity=entity,
                profile=profile,
            )

            if action != PolicyAction.KEEP:
                continue

            for pattern in patterns:
                protected_text = protect_pattern(
                    protected_text,
                    pattern,
                )

        physician_action = PolicyEngine.get_action(
            entity=MedicalContextEntity.PHYSICIAN_NAME,
            profile=profile,
        )

        if physician_action == PolicyAction.KEEP:
            for pattern in cls.CLINICAL_ROLE_PATTERNS:
                protected_text = protect_pattern(
                    protected_text,
                    pattern,
                )

        return protected_text, mapping

    @staticmethod
    def restore(
        text: str,
        mapping: Dict[str, str],
    ) -> str:
        restored_text = text

        for token, original_value in mapping.items():
            restored_text = restored_text.replace(
                token,
                original_value,
            )

        return restored_text