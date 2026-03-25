"""Mixed-format numeric parsers for vessel fleet data.

Handles real-world data formats found in XLS, HTML, and PDF sources:
- Comma-separated numbers: "8,000 ft."
- Dimension pairs: "89.2 ft. x 36.7 ft."
- Boolean variants: "Y", "Yes", "1", "True"
- Label-embedded numbers: "DP2", "Class 3"
"""

from __future__ import annotations

import re
from typing import Optional, Union

_UNIT_SUFFIXES: tuple[str, ...] = (
    " ft.", " ft", " feet",
    " m.", " m", " metres", " meters",
    " tonnes", " tons", " t",
    " kips", " klbs",
    " hp", " HP",
    " psi", " PSI",
    " in.", " in", " inches",
    " st", " ST",
    " knots", " kn",
    " MW", " mw",
)

_NON_NUMERIC_VALUES: frozenset[str] = frozenset({
    "n/a", "na", "nil", "none", "-", "--", "---",
    "tbd", "tba", "unknown", "varies",
})

_BOOL_TRUE: frozenset[str] = frozenset({"y", "yes", "true", "1"})
_BOOL_FALSE: frozenset[str] = frozenset({"n", "no", "false", "0"})

_LEADING_SYMBOLS_RE = re.compile(r"^[~><≈≥≤+]+")
_TRAILING_PLUS_RE = re.compile(r"\+$")
_DIMENSION_SPLIT_RE = re.compile(r"\s*[xX×]\s*")
_DIGITS_RE = re.compile(r"\d+")


def strip_unit(value: Optional[str]) -> str:
    """Remove known unit suffixes from a string value."""
    if value is None:
        return ""
    s = value.strip()
    for suffix in _UNIT_SUFFIXES:
        if s.lower().endswith(suffix.lower()):
            s = s[: -len(suffix)]
            break
    return s.strip()


def parse_numeric(value: Optional[Union[str, int, float]]) -> Optional[float]:
    """Parse a numeric value from a messy string.

    Handles commas, unit suffixes, leading symbols (~, >, <), trailing +.
    Returns None for non-numeric or empty inputs.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = value.strip()
    if not s or s.lower() in _NON_NUMERIC_VALUES:
        return None

    s = strip_unit(s)
    s = _LEADING_SYMBOLS_RE.sub("", s)
    s = _TRAILING_PLUS_RE.sub("", s)
    s = s.replace(",", "")
    s = s.strip()

    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_dimension_pair(
    value: Optional[str],
) -> Optional[tuple[float, float]]:
    """Parse a dimension pair from strings like '20 x 40' or '89.2 ft. x 36.7 ft.'.

    Returns (first, second) as floats, or None if not parseable.
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None

    parts = _DIMENSION_SPLIT_RE.split(s)
    if len(parts) < 2:
        return None

    first = parse_numeric(parts[0])
    second = parse_numeric(parts[1])
    if first is None or second is None:
        return None
    return (first, second)


def parse_bool(
    value: Optional[Union[str, bool, int, float]],
) -> Optional[bool]:
    """Parse a boolean from various representations.

    Handles Y/Yes/True/1 -> True, N/No/False/0 -> False.
    Returns None for unrecognised values.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
        return None
    s = value.strip()
    if not s:
        return None
    lower = s.lower()
    if lower in _BOOL_TRUE:
        return True
    if lower in _BOOL_FALSE:
        return False
    return None


def parse_int_from_label(value: Optional[str]) -> Optional[int]:
    """Extract an integer from a label string.

    Handles 'DP2', 'DP 3', 'Class 2', or plain '3'.
    Returns None if no digits found.
    """
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    match = _DIGITS_RE.search(s)
    if match:
        return int(match.group())
    return None
