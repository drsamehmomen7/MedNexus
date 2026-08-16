import re
import unicodedata


def normalize_reference_term(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("value must be a string.")
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w\u0600-\u06ff]+", " ", normalized).strip()
