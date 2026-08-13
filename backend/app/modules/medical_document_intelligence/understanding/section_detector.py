import re

from .models import DetectedSection
from .profiles import SECTION_ALIASES


class SectionDetector:
    """Detect line-oriented major clinical headings with exact offsets."""

    @classmethod
    def detect(cls, text: str) -> tuple[DetectedSection, ...]:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        headings = []
        for match in re.finditer(
            r"(?m)^[ \t]*(?P<head>[^\r\n:]{2,60}?)[ \t]*(?::[^\r\n]*)?[ \t]*\r?$",
            text,
        ):
            heading = match.group("head").strip()
            normalized = cls.normalize_heading(heading)
            for canonical, aliases in SECTION_ALIASES.items():
                if normalized in {cls.normalize_heading(alias) for alias in aliases}:
                    headings.append((canonical, heading, match.start("head")))
                    break
        return tuple(
            DetectedSection(
                canonical_name=canonical,
                original_heading=heading,
                start=start,
                end=headings[index + 1][2] if index + 1 < len(headings) else len(text),
            )
            for index, (canonical, heading, start) in enumerate(headings)
        )

    @staticmethod
    def normalize_heading(value: str) -> str:
        return re.sub(r"[^\w\u0600-\u06ff]+", " ", value.casefold()).strip()
