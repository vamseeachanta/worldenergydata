"""Conservative, descriptive Phase 1B intervention HSE assessments.

Basis: the 2026-05-18 issue-416 plan, Metric Contract and Operator Aggregation
Contract, and issue 419 (p5-p8). This is an adapter boundary, not a raw DB loader:
callers must validate source identity, calendar dates, incident deduplication and
activity classification before supplying records. The mixed-source Phase 0 DB
cannot be treated as a qualified BSEE incident cohort.

All patterns remain NOT_EVALUATED: descriptive counts do not establish exposure,
statistical significance, causation or a recommendation. Audit row indices are
internal only. Use public_summary() for review; even that projection requires the
separate operator-policy review before publication. No names, leases or arbitrary
input labels are returned in its fixed output schema.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Literal

from worldenergydata.bsee.analysis.intervention.hse_join import (
    match_intervention_windows,
    normalize_join_key,
)

# Issue-416 plan (2026-05-18), Operator Aggregation Contract rule 2;
# issue 419 strengthens this to every operator-aggregate cross-tab cell.
MIN_CELL_SIZE = 5
ACTIVITIES = ("PERS", "PSAFE", "CRANE")
# Controlled service types from the same plan, Metric Contract,
# service_type_incident_rate row. These are types, never vendor names.
VENDOR_TYPES = frozenset(
    (
        "wireline",
        "coil_tubing",
        "lift_boat",
        "snubbing",
        "workover_rig",
        "support_vessel",
        "pumping",
    )
)
SEASONS = ("hurricane", "non_hurricane")


def atlantic_season(day: date) -> str:
    """Calendar stratum only; no assertion of actual cyclone exposure.

    NHC, Tropical Cyclone Climatology, Atlantic Hurricane Season (accessed
    2026-10-22), https://www.nhc.noaa.gov/climo/: June 1 through November 30.
    """
    if type(day) is not date:
        raise ValueError("season requires an explicit calendar date")
    return "hurricane" if 6 <= day.month <= 11 else "non_hurricane"


@dataclass(frozen=True)
class PatternAssessment:
    """A fixed-label descriptive table plus unfulfilled inference requirements."""

    pattern: str
    cells: tuple[tuple[str, int], ...]
    reasons: tuple[str, ...]
    status: Literal["NOT_EVALUATED"] = "NOT_EVALUATED"
    statistic: None = None
    p_value: None = None
    effect_size: None = None


@dataclass(frozen=True)
class PatternDiagnostics:
    """Internal trace for supplied row order; do not publish audit fields.

    Counts are cohort diagnostics, not disclosure-controlled outputs. In
    particular, serializing this dataclass directly is not a public report.
    """

    patterns: tuple[PatternAssessment, ...]
    matched_pairs: tuple[tuple[int, int], ...]
    excluded_rows: tuple[int, ...]
    join_counts: dict[str, int]
    invalid_window_indices: tuple[int, ...]

    def public_summary(self) -> dict[str, object]:
        """Return review-only aggregate candidates without identities or margins.

        If any table is sparse, withhold every table in this release. Releasing
        other cuts could disclose a total usable to reconstruct a suppressed
        cell. No partially suppressed table or raw audit count is emitted.
        This does not replace the separate deny-list scanner or release review.
        """
        sparse = any("small_cell_table_withheld" in p.reasons for p in self.patterns)
        return {
            "publication_status": "REVIEW_REQUIRED",
            "patterns": [
                {
                    "pattern": p.pattern,
                    "status": p.status,
                    "cells": [] if sparse else [[k, n] for k, n in p.cells],
                    "reasons": list(p.reasons),
                    "statistic": p.statistic,
                    "p_value": p.p_value,
                    "effect_size": p.effect_size,
                }
                for p in self.patterns
            ],
        }


def _assessment(
    pattern: str,
    counts: Counter[str],
    labels: Iterable[str],
    missing: str | None = None,
    requirements: tuple[str, ...] = (),
) -> PatternAssessment:
    reasons = [
        "coverage_and_source_validation_required",
        "statistical_sanity_not_evaluated",
        "publication_policy_review_required",
        *requirements,
    ]
    cells = tuple((label, counts[label]) for label in labels)
    if missing:
        reasons.append(missing)
        cells = ()
    elif not cells or any(n < MIN_CELL_SIZE for _, n in cells):
        reasons.append("small_cell_table_withheld")
        cells = ()
    return PatternAssessment(pattern, cells, tuple(reasons))


def assess_patterns(
    incidents: Iterable[Mapping[str, object]],
    windows: Iterable[Mapping[str, object]],
) -> PatternDiagnostics:
    """Assess p5-p8 using uniquely matched, qualified BSEE incident rows only.

    Incident fields extend hse_join's operator/lease_number/incident_date with
    incident_id (unique nonempty source-qualified text), source='BSEE',
    record_kind='incident', and activity_code in ACTIVITIES. These are normalized
    adapter fields, not assumptions about raw DB columns. INC notices and all
    other sources are excluded. IDs must be unique across the supplied batch;
    duplicate IDs reject it instead of arbitrarily retaining one copy.

    Window fields follow hse_join plus vendor_type in VENDOR_TYPES. All supplied
    windows must already be classified as intervention activity. Matching reuses
    its inclusive-day, case/spacing-only normalization and ambiguity handling.
    Invalid, ambiguous and unmatched rows never become incident counts or a
    non-intervention control cohort. p5 requires complete PERS/PSAFE/CRANE
    classification of the matched cohort; p8 requires a controlled vendor type
    for every matched window. Missing labels withhold the entire affected table.

    p6 counts incidents by calendar season, not rates. p7 is NOT_EVALUATED until
    rig age at incident time and rig-specific exposure denominators are qualified.
    No rate scaling, statistical cutoffs or assumed rig-age bins are introduced.
    """
    rows, periods = list(incidents), list(windows)
    seen: set[str] = set()
    selected, original_indices, excluded = [], [], []
    for index, row in enumerate(rows):
        identifier = row.get("incident_id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("incident_id must be nonempty text")
        identifier = identifier.strip()
        if identifier in seen:
            raise ValueError("duplicate incident_id")
        seen.add(identifier)
        if row.get("source") != "BSEE" or row.get("record_kind") != "incident":
            excluded.append(index)
            continue
        selected.append(row)
        original_indices.append(index)

    join = match_intervention_windows(selected, periods)
    pairs = []
    activity_counts: Counter[str] = Counter()
    season_counts: Counter[str] = Counter()
    vendor_counts: Counter[str] = Counter()
    activity_missing = vendor_missing = False
    for index, match in enumerate(join.matches):
        if match.status != "matched":
            continue
        window_index = match.window_indices[0]
        pairs.append((original_indices[index], window_index))
        row = selected[index]
        key = normalize_join_key(
            row.get("operator"), row.get("lease_number"), row.get("incident_date")
        )
        # A uniquely matched row necessarily has a valid normalized date.
        season_counts[atlantic_season(key[2])] += 1
        activity = row.get("activity_code")
        if isinstance(activity, str) and activity in ACTIVITIES:
            activity_counts[activity] += 1
        else:
            activity_missing = True
        vendor = periods[window_index].get("vendor_type")
        if isinstance(vendor, str) and vendor in VENDOR_TYPES:
            vendor_counts[vendor] += 1
        else:
            vendor_missing = True

    patterns = (
        _assessment(
            "p5",
            activity_counts,
            ACTIVITIES,
            "activity_classification_required" if activity_missing else None,
        ),
        _assessment(
            "p6",
            season_counts,
            SEASONS,
            requirements=("exposure_denominator_required",),
        ),
        _assessment("p7", Counter(), (), "rig_age_and_rig_exposure_required"),
        _assessment(
            "p8",
            vendor_counts,
            sorted(vendor_counts),
            "vendor_type_required" if vendor_missing else None,
            requirements=("exposure_denominator_required",),
        ),
    )
    return PatternDiagnostics(
        patterns,
        tuple(pairs),
        tuple(excluded),
        join.counts,
        join.invalid_window_indices,
    )
