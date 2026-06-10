import re


_non_word = re.compile(r"[^\w\s]+", re.UNICODE)
_turkish_map = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "Ç": "c",
        "Ğ": "g",
        "İ": "i",
        "I": "i",
        "Ö": "o",
        "Ş": "s",
        "Ü": "u",
    }
)
_phrase_fixes = (
    ("you cup", "youtube"),
    ("you tube", "youtube"),
    ("whats app", "whatsapp"),
    ("what app", "whatsapp"),
    ("vat sap", "whatsapp"),
    ("vatsap", "whatsapp"),
    ("hava neler", "hava ne"),
    ("bilgisiyar", "bilgisayar"),
    ("bilgisyiar", "bilgisayar"),
    ("bilgisyer", "bilgisayar"),
)


def normalize_text(text: str) -> str:
    cleaned = text.lower().strip().translate(_turkish_map)
    for source, target in _phrase_fixes:
        cleaned = cleaned.replace(source, target)
    cleaned = _non_word.sub(" ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def strip_wake_word(text: str, wake_words: tuple[str, ...]) -> tuple[bool, str]:
    normalized = normalize_text(text)
    for wake_word in wake_words:
        if wake_word in normalized:
            remainder = normalized.replace(wake_word, " ", 1)
            return True, normalize_text(remainder)
    return False, normalized


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    haystack = normalize_text(text)
    return any(term in haystack for term in terms)


def remove_phrases(text: str, phrases: tuple[str, ...]) -> str:
    cleaned = normalize_text(text)
    for phrase in phrases:
        cleaned = cleaned.replace(normalize_text(phrase), " ")
    return normalize_text(cleaned)


def strip_tokens(text: str, tokens: tuple[str, ...]) -> str:
    cleaned = normalize_text(text)
    pieces = [piece for piece in cleaned.split() if piece not in set(tokens)]
    return normalize_text(" ".join(pieces))
