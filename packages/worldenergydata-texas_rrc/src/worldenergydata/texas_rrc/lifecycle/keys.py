"""API key normalization for Texas RRC lifecycle joins."""

from __future__ import annotations

import re


def normalize_api14(value: object) -> str | None:
    """Normalize common Texas RRC API shapes to a 14-digit API key."""
    if value is None:
        return None

    digits = re.sub(r"\D", "", str(value).strip())
    if not digits.startswith("42"):
        return None

    if len(digits) == 10:
        return f"{digits}0000"
    if len(digits) == 12:
        return f"{digits}00"
    if len(digits) == 14:
        return digits
    return None


def derive_api10(api14: str | None) -> str | None:
    """Return the API10 base well key from a normalized API14 value."""
    normalized = normalize_api14(api14)
    if normalized is None:
        return None
    return normalized[:10]


def split_api14(api14: str) -> dict[str, str]:
    """Split API14 into the lifecycle join fields used downstream."""
    normalized = normalize_api14(api14)
    if normalized is None:
        raise ValueError(f"Invalid Texas API14: {api14}")

    return {
        "api10": normalized[:10],
        "county_code": normalized[2:5],
        "well_unique_number": normalized[5:10],
        "sidetrack_code": normalized[10:12],
        "completion_code": normalized[12:14],
    }
