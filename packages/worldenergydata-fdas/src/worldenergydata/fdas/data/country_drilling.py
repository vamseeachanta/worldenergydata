"""Allocate explicitly supplied active drilling intervals to FDAS months.

Milestone spans are not activity evidence. See fdas.data's retirement of the
former duration estimator. No fallback duration or completion estimate exists.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from itertools import pairwise

from ..adapters.wells import WellKey, WellRecord, require_text


@dataclass(frozen=True)
class DrillingActivity:
    """An evidenced active drilling interval [start, end), in calendar days.

    The caller supplies records of active drilling, excluding suspension and
    completion. End is the first inactive day, not an inclusive milestone.
    Evidence identifies the source record or the explicit scenario assumption.
    """

    country: str
    source: str
    well_id: str
    start: date
    end: date
    evidence: str

    def __post_init__(self) -> None:
        for label in ("country", "source", "well_id", "evidence"):
            require_text(getattr(self, label), label)
        if type(self.start) is not date or type(self.end) is not date:
            raise ValueError("Activity endpoints must be calendar dates")
        if self.end <= self.start:
            raise ValueError("Activity end must follow start")

    @property
    def key(self) -> WellKey:
        return self.country, self.source, self.well_id


@dataclass(frozen=True)
class CountryDrillingTimeline:
    """Coverage is evaluated only for supplied wells in the named development.

    EVALUATED means input coverage and allocation succeeded; it does not qualify
    the source evidence as measured or establish unreported drilling activity.
    """

    status: str
    drilling_monthly: dict[str, int] | None
    missing_wells: tuple[WellKey, ...]
    activities: tuple[DrillingActivity, ...]

    def as_cashflow_input(self) -> dict:
        """Refuse incomplete coverage rather than silently pricing zero days."""
        if self.status != "EVALUATED" or self.drilling_monthly is None:
            raise ValueError("Drilling timeline NOT_EVALUATED: missing activity")
        return {"drilling_monthly": dict(self.drilling_monthly)}


def _allocate(activity: DrillingActivity, monthly: dict[str, int]) -> None:
    cursor = activity.start
    while cursor < activity.end:
        if (cursor.year, cursor.month) == (activity.end.year, activity.end.month):
            stop = activity.end
        else:
            # Gregorian month rollover; calendar constants, not engineering limits.
            stop = (
                date(cursor.year + 1, 1, 1)
                if cursor.month == 12
                else date(cursor.year, cursor.month + 1, 1)
            )
        # Hand-count basis: half-open day sets; no assumed utilization factor.
        monthly[f"{cursor.year:04d}-{cursor.month:02d}"] += (stop - cursor).days
        cursor = stop


def _activity_by_well(wells: dict, activities: Iterable[DrillingActivity]) -> dict:
    grouped = defaultdict(list)
    for activity in activities:
        if activity.key not in wells:
            raise ValueError("Activity references unknown well")
        spud = wells[activity.key].spud_date
        if spud is None or activity.start < spud:
            raise ValueError("Activity requires known spud on or before start")
        grouped[activity.key].append(activity)
    for intervals in grouped.values():
        intervals.sort(key=lambda item: item.start)
        for previous, current in pairwise(intervals):
            if current.start < previous.end:
                raise ValueError("Overlapping activity intervals for one well")
    return grouped


def build_drilling_timeline(
    wells: Iterable[WellRecord],
    activities: Iterable[DrillingActivity],
    *,
    development: str,
) -> CountryDrillingTimeline:
    """Sum active well-days by month; require activity for every selected well.

    Wells outside the development are ignored for coverage. Unknown activities
    and overlapping intervals fail, including outside the selected development.
    Missing coverage yields a null monthly result, never partial priced days.
    """
    require_text(development, "development")
    inventory = {}
    for well in wells:
        if well.key in inventory:
            raise ValueError("Duplicate well identity")
        inventory[well.key] = well
    selected = {key for key, row in inventory.items() if row.development == development}
    if not selected:
        raise ValueError("No wells for requested development")
    supplied = tuple(activities)
    grouped = _activity_by_well(inventory, supplied)
    missing = tuple(sorted(selected - grouped.keys()))
    if missing:
        return CountryDrillingTimeline("NOT_EVALUATED", None, missing, supplied)
    monthly = defaultdict(int)
    for key in sorted(selected):
        for activity in grouped[key]:
            _allocate(activity, monthly)
    return CountryDrillingTimeline(
        "EVALUATED", dict(sorted(monthly.items())), (), supplied
    )
