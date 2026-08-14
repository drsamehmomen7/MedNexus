import re

from .models import DocumentLanguage


class LanguageDetector:
    """Offline Unicode-script language detection for clinical documents."""

    MIN_LETTERS = 4
    # MIXED represents substantial bilingual content, not incidental labels,
    # identifiers, or system-generated footer text in a second script.
    MIXED_MIN_RATIO = 0.30

    @classmethod
    def detect(cls, text: str) -> DocumentLanguage:
        if not isinstance(text, str):
            raise TypeError("text must be a string.")
        arabic = len(re.findall(r"[\u0600-\u06ff]", text))
        english = len(re.findall(r"[A-Za-z]", text))
        total = arabic + english
        if total < cls.MIN_LETTERS:
            return DocumentLanguage.UNKNOWN
        if arabic / total < cls.MIXED_MIN_RATIO:
            return DocumentLanguage.ENGLISH
        if english / total < cls.MIXED_MIN_RATIO:
            return DocumentLanguage.ARABIC

        arabic_lines = 0
        english_lines = 0
        for line in text.splitlines():
            line_arabic = len(re.findall(r"[\u0600-\u06ff]", line))
            line_english = len(re.findall(r"[A-Za-z]", line))
            line_total = line_arabic + line_english
            if line_total < cls.MIN_LETTERS:
                continue
            if line_arabic / line_total >= cls.MIXED_MIN_RATIO:
                arabic_lines += 1
            if line_english / line_total >= cls.MIXED_MIN_RATIO:
                english_lines += 1

        line_total = arabic_lines + english_lines
        if line_total and min(arabic_lines, english_lines) / line_total >= cls.MIXED_MIN_RATIO:
            return DocumentLanguage.MIXED
        return DocumentLanguage.ARABIC if arabic_lines > english_lines else DocumentLanguage.ENGLISH
