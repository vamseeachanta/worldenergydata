"""Deterministic reference-marker labels and calendar positions."""

from __future__ import annotations

import re
from calendar import isleap
from datetime import date


def reference_marker(reference_date: str | None, *, fallback_year: float) -> dict:
    """Use elapsed calendar days for exact dates; never consult the clock.

    The fallback is a decimal year, not a claim about a particular day.
    Historical gate parsing deliberately remains the builder's responsibility.
    """
    if reference_date is None:
        return {
            "year": fallback_year,
            "lab": "Reference year",
            "dt": str(fallback_year),
        }
    message = "reference date must be a valid YYYY-MM-DD calendar date"
    if not isinstance(reference_date, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", reference_date
    ):
        raise ValueError(message)
    try:
        parsed = date.fromisoformat(reference_date)
    except ValueError as error:
        raise ValueError(message) from error
    elapsed = (parsed - date(parsed.year, 1, 1)).days
    days_in_year = 366 if isleap(parsed.year) else 365
    return {
        "year": parsed.year + elapsed / days_in_year,
        "lab": "As of",
        "dt": reference_date,
    }
