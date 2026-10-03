"""Explicit alias matching shared by mapping and reasoning (no NLP models, no extraction tools)."""
from __future__ import annotations
import re


def alias_regex(alias: str) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def find_alias(text: str, aliases: list[str]):
    """Return (alias, start, end) for the earliest match of any alias, else None."""
    best = None
    for a in aliases:
        m = alias_regex(a).search(text)
        if m and (best is None or m.start() < best[1]):
            best = (a, m.start(), m.end())
    return best


def snippet(text: str, start: int, end: int, width: int = 90) -> str:
    return text[max(0, start - width): end + width].strip()
