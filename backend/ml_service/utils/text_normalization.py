"""Shared text preprocessing for the Python ML service.

This mirrors the JavaScript normalization layer closely so the JS fallback and
Python microservice see near-identical text before vectorization.
"""

from __future__ import annotations

import re
import unicodedata

SLANG_REPLACEMENTS = [
    (r"\bim\b", "i am"),
    (r"\bive\b", "i have"),
    (r"\bdont\b", "do not"),
    (r"\bcant\b", "cannot"),
    (r"\bwont\b", "will not"),
    (r"\bdoesnt\b", "does not"),
    (r"\bdidnt\b", "did not"),
    (r"\bshouldnt\b", "should not"),
    (r"\bwouldnt\b", "would not"),
    (r"\bthere's\b", "there is"),
    (r"\btheres\b", "there is"),
    (r"\bpls\b", "please"),
    (r"\bplz\b", "please"),
    (r"\bu\b", "you"),
    (r"\bur\b", "your"),
    (r"\bgonna\b", "going to"),
    (r"\bwanna\b", "want to"),
    (r"\bkinda\b", "kind of"),
    (r"\bsorta\b", "sort of"),
    (r"\byaar\b", "friend"),
    (r"\bghabrahat\b", "anxiety"),
    (r"\bbechain\b", "restless"),
    (r"\budas\b", "sad"),
    (r"\budasi\b", "sadness"),
    (r"\bumeed\b", "hope"),
    (r"\bmehfooz\b", "safe"),
    (r"\bbohat\b", "very"),
    (r"\bbhot\b", "very"),
    (r"\bthora\b", "a little"),
    (r"\baaj\b", "today"),
    (r"\bkal\b", "tomorrow"),
]

COMMON_TYPOS = [
    (r"\bdefinately\b", "definitely"),
    (r"\brecieve\b", "receive"),
    (r"\bseperate\b", "separate"),
    (r"\boccurence\b", "occurrence"),
]


def _normalize_repeated_characters(text: str) -> str:
    return re.sub(r"([a-z])\1{2,}", r"\1\1", text)


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    normalized = unicodedata.normalize("NFKC", text).lower().strip()
    normalized = normalized.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    normalized = re.sub(r"[^\w\s'/-]+", " ", normalized, flags=re.UNICODE)

    for pattern, replacement in COMMON_TYPOS + SLANG_REPLACEMENTS:
        normalized = re.sub(pattern, replacement, normalized)

    normalized = _normalize_repeated_characters(normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def strip_punctuation(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\/'-]", " ", normalize_text(text))).strip()


def make_casual_variant(text: str) -> str:
    return (
        normalize_text(text)
        .replace("you are", "youre")
        .replace("do not", "dont")
        .replace("cannot", "cant")
        .replace("i am", "i'm")
        .replace("i have", "i've")
    )


def make_roman_urdu_variant(text: str) -> str:
    return (
        normalize_text(text)
        .replace("anxiety", "ghabrahat")
        .replace("sadness", "udas")
        .replace("sad", "udas")
        .replace("hope", "umeed")
        .replace("safe", "mehfooz")
        .replace("restless", "bechain")
        .replace("very", "bohat")
    )


def make_noisy_variant(text: str) -> str:
    return (
        strip_punctuation(text)
        .replace("very", "vry")
        .replace("please", "pls")
        .replace("friend", "yaar")
        .replace("today", "aaj")
    )
