import re
from typing import Dict, Tuple


class PlaceholderProtector:
    """
    Protects MedNexus-generated placeholders before AI processing.

    Example:
        [MRN:6f82d913ab]
        becomes temporarily:
        __MNX_PLACEHOLDER_0001__

    The original MedNexus placeholder is restored after AI processing.
    """

    PLACEHOLDER_PATTERN = re.compile(
        r"\[[A-Z][A-Z0-9_]*(?::[^\[\]\r\n]+)?\]"
    )

    @classmethod
    def protect(
        cls,
        text: str,
    ) -> Tuple[str, Dict[str, str]]:
        mapping: Dict[str, str] = {}
        token_number = 1

        def replace_match(match: re.Match) -> str:
            nonlocal token_number

            token = f"__MNX_PLACEHOLDER_{token_number:04d}__"

            mapping[token] = match.group(0)
            token_number += 1

            return token

        protected_text = cls.PLACEHOLDER_PATTERN.sub(
            replace_match,
            text,
        )

        return protected_text, mapping

    @staticmethod
    def restore(
        text: str,
        mapping: Dict[str, str],
    ) -> str:
        restored_text = text

        for token, original_placeholder in mapping.items():
            restored_text = restored_text.replace(
                token,
                original_placeholder,
            )

        return restored_text