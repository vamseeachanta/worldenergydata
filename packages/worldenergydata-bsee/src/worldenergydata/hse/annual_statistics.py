# ABOUTME: Pure annual counts of supplied incident records with declared coverage.
# ABOUTME: Retains provenance and keeps missing observations distinct from zero.

"""An incident-count slice, independent of importer and database operations.

Each validated, distinct incident id contributes one incident to its calendar
year/type group. Calendar years run from January 1 through December 31.
Severity labels never establish the number of injured or deceased people.
OPEN: person-count totals and complete-year zero filling require an established
source grain; rates also require a cited public exposure denominator.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal


@dataclass(frozen=True)
class AnnualTypeCount:
    """An observed group; coverage dates are the source/year intersection."""

    year: int
    incident_type: str
    count: int
    coverage_start: date
    coverage_end: date
    partial_coverage: bool
    unit: Literal["incidents"] = "incidents"


@dataclass(frozen=True)
class AnnualStatistics:
    """Counts and a snapshot of caller-supplied provenance.

    ``empty_input`` means no supplied incidents, not measured zero incidents.
    Coverage describes the supplied source interval, not independent proof of
    reporting completeness. No unobserved year/type combinations are emitted.
    """

    rows: tuple[AnnualTypeCount, ...]
    coverage_start: date
    coverage_end: date
    source_metadata: dict[str, object]
    status: Literal["observed_incidents", "empty_input"]


def _calendar_date(value: object, field: str, *, allow_datetime: bool = False) -> date:
    """Use the calendar date as supplied, without timezone conversion."""
    if isinstance(value, datetime):
        if allow_datetime:
            return value.date()
    elif isinstance(value, date):
        return value
    elif isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            if allow_datetime:
                try:
                    return datetime.fromisoformat(value).date()
                except ValueError:
                    pass
    raise ValueError(f"{field} must be a parseable ISO date")


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonblank string")
    return value


def build_annual_statistics(
    incidents: Iterable[Mapping[str, object]],
    *,
    coverage_start: date | str,
    coverage_end: date | str,
    source_metadata: Mapping[str, object],
) -> AnnualStatistics:
    """Build sorted observed annual type counts, or raise before aggregation.

    Records require ``incident_id`` (a unique nonblank string),
    ``incident_date`` (a date, datetime or ISO string), and ``incident_type``
    (a nonblank string). Ids and types are retained verbatim. For normalized
    importer records, callers must map ``bsee_incident_id`` to ``incident_id``.
    Additional fields, including severity, do not affect the counts.

    Coverage requires inclusive date-only bounds, even for empty input.
    Incident timestamps use their supplied local calendar date. Metadata is
    deep-copied; inputs are never modified. All records must validate before
    any counts are aggregated. Missing years and types remain absent.
    """
    start = _calendar_date(coverage_start, "coverage_start")
    end = _calendar_date(coverage_end, "coverage_end")
    if start > end:
        raise ValueError("coverage_start must be on or before coverage_end")

    seen: set[str] = set()
    validated: list[tuple[int, str]] = []
    for record in incidents:
        if not isinstance(record, Mapping):
            raise ValueError("each incident must be a mapping")
        incident_id = _required_text(record.get("incident_id"), "incident_id")
        if incident_id in seen:
            raise ValueError("duplicate incident_id")
        seen.add(incident_id)
        incident_date = _calendar_date(
            record.get("incident_date"), "incident_date", allow_datetime=True
        )
        incident_type = _required_text(record.get("incident_type"), "incident_type")
        if not start <= incident_date <= end:
            raise ValueError("incident_date is outside declared coverage")
        validated.append((incident_date.year, incident_type))

    counts = Counter(validated)
    rows = []
    for (year, incident_type), count in sorted(counts.items()):
        # Calendar boundaries, not empirical constants: January 1 to December 31.
        year_start, year_end = date(year, 1, 1), date(year, 12, 31)
        row_start, row_end = max(start, year_start), min(end, year_end)
        rows.append(
            AnnualTypeCount(
                year=year,
                incident_type=incident_type,
                count=count,
                coverage_start=row_start,
                coverage_end=row_end,
                partial_coverage=row_start != year_start or row_end != year_end,
            )
        )

    return AnnualStatistics(
        rows=tuple(rows),
        coverage_start=start,
        coverage_end=end,
        source_metadata=deepcopy(dict(source_metadata)),
        status="observed_incidents" if rows else "empty_input",
    )
