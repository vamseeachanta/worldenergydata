"""Country-neutral per-well metadata; milestones never imply active rig days."""

from dataclasses import dataclass
from datetime import date
from math import isfinite

WellKey = tuple[str, str, str]


def require_text(value: str, label: str) -> None:
    """Require a canonical nonempty identity without silently rewriting it."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"Invalid {label}: expected nonempty trimmed text")


@dataclass(frozen=True)
class WellRecord:
    """One source-scoped well, explicitly linked to a development.

    Country and source namespaces prevent collisions between national IDs.
    A foreign identifier is never relabelled as a US API well number.
    Unknown dates/depths are None; a measured depth of zero remains zero.
    """

    country: str
    source: str
    well_id: str
    development: str
    spud_date: date | None
    water_depth_m: float | None

    def __post_init__(self) -> None:
        for label in ("country", "source", "well_id", "development"):
            require_text(getattr(self, label), label)
        if self.spud_date is not None and type(self.spud_date) is not date:
            raise ValueError("spud_date must be a calendar date or None")
        value = self.water_depth_m
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not isfinite(value)
            or value < 0
        ):
            raise ValueError("water_depth_m must be finite and nonnegative or None")

    @property
    def key(self) -> WellKey:
        return self.country, self.source, self.well_id
