"""Descriptive taxonomy counts; no exposure rates or causal claims."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from .classifier_bridge import ClassifiedIncident

# Source: docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md (2026),
# Operator Aggregation Contract, rule 2. Apply to every cell conservatively.
MIN_CELL_SIZE = 5


@dataclass(frozen=True)
class ActivityCount:
    """A released taxonomy-code cell, excluding source text and identifiers."""

    activity: str
    count: int


def count_activity_patterns(
    incidents: Iterable[ClassifiedIncident],
) -> tuple[ActivityCount, ...]:
    """Count each unique record once and omit cells below the disclosure minimum.

    Only registry activity codes are emitted. Suppressed labels, counts and
    population totals are omitted to avoid direct subtraction of a small cell.
    These are descriptive counts, not intervention incident rates. Cohort
    membership and source coverage require separate evidence; publishing
    overlapping cuts requires a separate disclosure assessment.
    """
    from worldenergydata.safety_analysis.taxonomy.activity_registry import (
        ActivityTaxonomy,
    )

    rows = tuple(incidents)
    if len({row.record_id for row in rows}) != len(rows):
        raise ValueError("HSE record IDs must be unique")
    codes = {activity.code for activity in ActivityTaxonomy().activities}
    if any(row.activity not in codes for row in rows):
        raise ValueError("Unknown activity code; free-text labels are not permitted")
    # Count = sum of one indicator per record in the category (no coefficients).
    # Method basis: Phase 1A hse_incidents_profile, SQL GROUP BY / COUNT(*), 2026.
    counts = Counter(row.activity for row in rows)
    return tuple(
        ActivityCount(code, count)
        for code, count in sorted(counts.items())
        if count >= MIN_CELL_SIZE
    )
