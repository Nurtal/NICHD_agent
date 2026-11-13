"""Text normalization and lenient French matching shared by the engine and the filter."""

from __future__ import annotations

import re
import unicodedata


def normalize(text: str) -> str:
    """Lowercase, strip accents, unify apostrophes; keep word boundaries."""
    text = unicodedata.normalize("NFKD", text.replace("’", "'").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def contains(haystack_norm: str, needle: str) -> bool:
    """Whole-word match of a normalized phrase; `needle*` matches as a word prefix."""
    prefix = needle.endswith("*")
    n = normalize(needle.rstrip("*"))
    if not n:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(n) + (r"" if prefix else r"(?![a-z0-9])")
    return re.search(pattern, haystack_norm) is not None


def mentions(haystack_norm: str, anchor: str) -> bool:
    """Lenient match: single words match on a stem, to absorb French inflections."""
    n = normalize(anchor)
    if " " in n or len(n) <= 4:
        return contains(haystack_norm, anchor)
    stem = n[: max(4, len(n) - 3)]
    return re.search(r"(?<![a-z0-9])" + re.escape(stem), haystack_norm) is not None
