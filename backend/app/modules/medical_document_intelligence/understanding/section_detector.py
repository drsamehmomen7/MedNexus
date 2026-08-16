import re

from .models import DetectedSection
from .profiles import SECTION_ALIASES


class SectionDetector:
    """Detect line, inline, and conservatively flattened clinical headings."""

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
        # Extracted templates often flatten several ``Heading: value`` fields onto
        # one line. A colon is required here so prose mentions are not boundaries.
        for canonical, aliases in SECTION_ALIASES.items():
            for alias in sorted(aliases, key=len, reverse=True):
                for match in re.finditer(
                    rf"(?<![\w\u0600-\u06ff])(?P<head>{re.escape(alias)})[ \t]*:",
                    text, re.IGNORECASE,
                ):
                    headings.append((canonical, match.group("head"), match.start("head")))
        headings.extend(cls._flattened_heading_cluster(text))
        ordered = sorted(set(headings), key=lambda item: (item[2], -len(item[1])))
        headings = []
        for candidate in ordered:
            if headings and candidate[2] < headings[-1][2] + len(headings[-1][1]):
                continue
            headings.append(candidate)
        return tuple(
            DetectedSection(
                canonical_name=canonical,
                original_heading=heading,
                start=start,
                end=headings[index + 1][2] if index + 1 < len(headings) else len(text),
            )
            for index, (canonical, heading, start) in enumerate(headings)
        )

    @classmethod
    def _flattened_heading_cluster(cls, text: str):
        """Recover title-cased heading sequences from layout-flattened text.

        A single terminology occurrence is never structural. The fallback activates
        only when at least three distinct registered headings form a document-level
        cluster beginning near the front of the text. It reuses the existing section
        registry and adds no report-specific vocabulary.
        """
        candidates = []
        for canonical, aliases in SECTION_ALIASES.items():
            for alias in sorted(aliases, key=len, reverse=True):
                for match in re.finditer(
                    rf"(?<![\w\u0600-\u06ff])(?P<head>{re.escape(alias)})(?![\w\u0600-\u06ff])",
                    text, re.IGNORECASE,
                ):
                    heading = match.group("head")
                    cased = [char for char in heading if char.isalpha() and char.lower() != char.upper()]
                    if not cased or not cased[0].isupper():
                        continue
                    candidates.append((canonical, heading, match.start("head")))
        ordered = sorted(set(candidates), key=lambda item: (item[2], -len(item[1])))
        non_overlapping = []
        for candidate in ordered:
            if non_overlapping and candidate[2] < non_overlapping[-1][2] + len(non_overlapping[-1][1]):
                continue
            non_overlapping.append(candidate)
        if len({item[0] for item in non_overlapping}) < 3:
            return ()
        if non_overlapping[0][2] > max(120, len(text) // 5):
            return ()
        return tuple(non_overlapping)

    @staticmethod
    def normalize_heading(value: str) -> str:
        return re.sub(r"[^\w\u0600-\u06ff]+", " ", value.casefold()).strip()
