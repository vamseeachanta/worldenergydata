"""Vessel name normalization for deduplication."""

from __future__ import annotations

import re
from typing import Optional

_PREFIXES: tuple[str, ...] = (
    "M/V ", "MV ", "S/V ", "SV ", "T.O. ", "SS ",
    "MT ", "FPSO ", "FSO ", "AHTS ",
)

_SUFFIXES: tuple[str, ...] = (
    " I", " II", " III", " IV", " V",
)

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^A-Z0-9 ]")


def normalize_vessel_name(name: Optional[str]) -> str:
    """Normalize a vessel name for dedup matching.

    Steps:
    1. Uppercase
    2. Strip common prefixes (M/V, MV, SS, etc.)
    3. Remove non-alphanumeric chars except spaces
    4. Collapse multiple spaces
    5. Strip leading/trailing whitespace

    Returns empty string for None/empty input.
    """
    if not name:
        return ""
    s = name.strip().upper()

    for prefix in _PREFIXES:
        if s.startswith(prefix):
            s = s[len(prefix):]
            break

    s = _NON_ALNUM_RE.sub(" ", s)
    s = _WHITESPACE_RE.sub(" ", s).strip()
    return s


def names_match(name_a: Optional[str], name_b: Optional[str]) -> bool:
    """Check if two vessel names match after normalization."""
    norm_a = normalize_vessel_name(name_a)
    norm_b = normalize_vessel_name(name_b)
    if not norm_a or not norm_b:
        return False
    return norm_a == norm_b
