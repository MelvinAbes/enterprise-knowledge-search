import re
import unicodedata

TRAILING_WHITESPACE = re.compile(r"[ \t]+$", re.MULTILINE)
EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_document_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\u00a0", " ")
    normalized = TRAILING_WHITESPACE.sub("", normalized)
    normalized = EXCESS_BLANK_LINES.sub("\n\n", normalized)
    return normalized.strip()
