import re

from .models import DocumentLanguage


class LanguageDetector:
    """Offline Unicode-script language detection for clinical documents."""

    MIN_LETTERS = 4
    MIXED_MIN_RATIO = 0.18

    @classmethod
    def detect(cls, text: str) -> DocumentLanguage:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        arabic = len(re.findall(r"[\u0600-\u06ff]", text))
        english = len(re.findall(r"[A-Za-z]", text))
        total = arabic + english
        if total < cls.MIN_LETTERS:
            return DocumentLanguage.UNKNOWN
        if arabic / total >= cls.MIXED_MIN_RATIO and english / total >= cls.MIXED_MIN_RATIO:
            return DocumentLanguage.MIXED
        return DocumentLanguage.ARABIC if arabic > english else DocumentLanguage.ENGLISH
