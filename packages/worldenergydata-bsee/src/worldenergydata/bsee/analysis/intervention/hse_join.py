"""Internal operator/lease/day linkage for intervention HSE analysis.

Basis: docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md,
Pseudocode step 3 and Operator Aggregation Contract; issue 419 requires a
committed normalization function before operator-level pattern mining.

Only case and whitespace are normalized. Lease prefixes, leading zeros and
operator punctuation remain significant: alias equivalence requires upstream
source evidence. Dates must be explicit calendar days or YYYY-MM-DD strings.
Raw WAR locale-formatted dates must be parsed explicitly by the caller using
the source's documented format; timestamps require a source timezone decision.

This module performs no classification, source filtering or publication. Callers
must supply already classified intervention windows and source-filtered incident
rows. A match is temporal co-occurrence, not causation or an incident rate.
Unmatched means no valid supplied window matched, not no intervention occurred.
No operator names or per-operator counts are included in the returned diagnostics.
Patterns p5-p8 remain NOT_EVALUATED until coverage, exposure denominators and
publication controls are established. No statistical thresholds are assumed.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Literal

JoinKey = tuple[str, str, date]
MatchStatus = Literal["matched", "unmatched", "invalid_key", "ambiguous"]


def _calendar_day(value: object) -> date | None:
    """Reject timestamps and locale-dependent strings instead of guessing."""
    if type(value) is date:
        return value
    # YYYY-MM-DD is an input representation, not an engineering coefficient.
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return None


def normalize_join_key(operator: object, lease: object, day: object) -> JoinKey | None:
    """Return an equality key, or None when any component is unusable.

    Numeric IDs are rejected: string conversion cannot recover lost leading
    zeros. No padding, prefix deletion, fuzzy names or date imputation is used.
    """
    if not isinstance(operator, str) or not isinstance(lease, str):
        return None
    operator_key = " ".join(operator.split()).casefold()
    lease_key = " ".join(lease.split()).upper()
    parsed_day = _calendar_day(day)
    if not operator_key or not lease_key or parsed_day is None:
        return None
    return operator_key, lease_key, parsed_day


@dataclass(frozen=True)
class IncidentMatch:
    """One result per input incident; indices refer to supplied window order."""

    status: MatchStatus
    window_indices: tuple[int, ...]


@dataclass(frozen=True)
class JoinResult:
    """Internal diagnostics; counts are coverage totals, not publishable patterns."""

    matches: tuple[IncidentMatch, ...]
    invalid_window_indices: tuple[int, ...]
    pattern_status: Literal["NOT_EVALUATED"] = "NOT_EVALUATED"

    @property
    def counts(self) -> dict[str, int]:
        """Partition incident rows without dropping invalid or ambiguous keys."""
        counts = dict.fromkeys(("matched", "unmatched", "invalid_key", "ambiguous"), 0)
        for match in self.matches:
            counts[match.status] += 1
        return counts


def match_intervention_windows(
    incidents: Iterable[Mapping[str, object]],
    windows: Iterable[Mapping[str, object]],
) -> JoinResult:
    """Match HSE operator/lease/day to closed WAR intervention intervals.

    HSE columns follow scripts/exploration/intervention_hse_phase1a_explore.py
    (2026-05-18). WAR identity columns follow intervention/activity_aggregator.py
    and war_vessel_crossref.py; date names follow rig_fleet/war_acquirer.py.
    Closed endpoints follow intervention/intervention_demand.py's inclusive-day
    convention. No tolerance or missing-end fallback is introduced.

    Overlapping or duplicate windows yield ambiguity rather than duplicated
    incidents. Original window positions survive rejected rows. No inputs are
    modified. Complexity depends on windows per operator/lease, not their product
    across every operator/lease in the dataset.
    """
    by_identity: dict[tuple[str, str], list[tuple[date, date, int]]] = defaultdict(list)
    invalid = []
    for index, row in enumerate(windows):
        key = normalize_join_key(
            row.get("BUS_ASC_NAME"), row.get("BOTM_LEASE_NUM"), row.get("WAR_START_DT")
        )
        end = _calendar_day(row.get("WAR_END_DT"))
        if key is None or end is None or end < key[2]:
            invalid.append(index)
            continue
        by_identity[key[:2]].append((key[2], end, index))

    matches = []
    for row in incidents:
        key = normalize_join_key(
            row.get("operator"), row.get("lease_number"), row.get("incident_date")
        )
        if key is None:
            matches.append(IncidentMatch("invalid_key", ()))
            continue
        candidates = tuple(
            index
            for start, end, index in by_identity.get(key[:2], ())
            if start <= key[2] <= end
        )
        if not candidates:
            status = "unmatched"
        elif len(candidates) == 1:
            status = "matched"
        else:
            status = "ambiguous"
        matches.append(IncidentMatch(status, candidates))
    return JoinResult(tuple(matches), tuple(invalid))
