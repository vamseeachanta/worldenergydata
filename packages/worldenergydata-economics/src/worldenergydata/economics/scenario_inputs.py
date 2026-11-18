"""Explicit inputs for deterministic development scenarios, in USD and barrels.

Every index refers to a period of ``duration_years`` years. Production day counts
are supplied separately: no calendar conversion is inferred. All assumptions are
required, including explicit zeros and empty tuples. Immutable tuples prevent
mutation through a frozen dataclass. See scenario.py and scenario_README.md for
method, limitations and the Input gaps register.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


def _finite(value: float, name: str, minimum: float | None = None) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    if not isfinite(value) or (minimum is not None and value < minimum):
        raise ValueError(f"{name} is outside its permitted range")


def _index(value: int, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _series(values: tuple[float, ...], name: str, minimum: float | None = None) -> None:
    if not isinstance(values, tuple):
        raise ValueError(f"{name} must be an immutable tuple")
    for value in values:
        _finite(value, name, minimum)


@dataclass(frozen=True)
class Periods:
    """Equal economic periods [years]; explicit production days in each period."""

    duration_years: float
    production_days: tuple[float, ...]

    def __post_init__(self) -> None:
        _finite(self.duration_years, "duration_years", 0.0)
        _series(self.production_days, "production_days", 0.0)
        if self.duration_years == 0 or not self.production_days:
            raise ValueError("Positive duration and a nonempty horizon are required")


@dataclass(frozen=True)
class WellSchedule:
    """Sequential drilling, completion and delay; integer durations in periods.

    First production index is start + drilling + completion + delay. Rate at
    that index is initial rate plus that period's addition; subsequently it is
    previous rate * current retention + current addition. Both tuples span the
    entire horizon. A reset is expressed by retention zero and a supplied
    addition. Additions before first production are invalid.
    """

    drilling_start_period: int
    drilling_periods: int
    completion_periods: int
    production_delay_periods: int
    initial_rate_barrels_per_day: float
    retention_fractions: tuple[float, ...]
    additions_barrels_per_day: tuple[float, ...]

    def __post_init__(self) -> None:
        for name in (
            "drilling_start_period",
            "drilling_periods",
            "completion_periods",
            "production_delay_periods",
        ):
            _index(getattr(self, name), name)
        _finite(self.initial_rate_barrels_per_day, "initial rate", 0.0)
        _series(self.retention_fractions, "retention", 0.0)
        _series(self.additions_barrels_per_day, "additions", 0.0)
        if any(value > 1 for value in self.retention_fractions):
            raise ValueError("Retention fractions must be at most one")
        if len(self.retention_fractions) != len(self.additions_barrels_per_day):
            raise ValueError("Retention and additions must share a horizon")


@dataclass(frozen=True)
class CostBreakdown:
    """Base components [USD]; engineering/contingency fractions are explicit.

    Engineering applies to all components. Contingency applies to the base,
    optionally including engineering. Schedule allocations are supplied separately.
    """

    components_usd: tuple[float, ...]
    engineering_fraction: float
    contingency_fraction: float
    contingency_includes_engineering: bool

    def __post_init__(self) -> None:
        _series(self.components_usd, "components_usd", 0.0)
        _finite(self.engineering_fraction, "engineering_fraction", 0.0)
        _finite(self.contingency_fraction, "contingency_fraction", 0.0)
        if type(self.contingency_includes_engineering) is not bool:
            raise ValueError("Contingency basis must be an explicit boolean")


@dataclass(frozen=True)
class Expenditure:
    """Nonnegative scheduled outflow [USD]; category is capital or operating."""

    period_index: int
    category: str
    amount_usd: float

    def __post_init__(self) -> None:
        _index(self.period_index, "period_index")
        _finite(self.amount_usd, "amount_usd", 0.0)
        if self.category not in ("capital", "operating"):
            raise ValueError("Expenditure category must be capital or operating")


@dataclass(frozen=True)
class ScenarioInputs:
    """One deterministic USD scenario; decks span the full period horizon.

    Net share applies to (gross revenue - variable operating cost). Scheduled
    outflows are then subtracted without that share. First discount period zero
    means time zero; one means the end of the first supplied period. Discount
    rate is a fraction per period of periods.duration_years, never annualized.
    """

    name: str
    periods: Periods
    wells: tuple[WellSchedule, ...]
    expenditures: tuple[Expenditure, ...]
    oil_prices_usd_per_barrel: tuple[float, ...]
    variable_costs_usd_per_barrel: tuple[float, ...]
    net_margin_fractions: tuple[float, ...]
    discount_rate_per_period: float
    first_discount_period: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Scenario name is required")
        if not isinstance(self.periods, Periods):
            raise ValueError("Scenario periods are required")
        count = len(self.periods.production_days)
        _series(self.oil_prices_usd_per_barrel, "oil prices")
        _series(self.variable_costs_usd_per_barrel, "variable costs", 0.0)
        _series(self.net_margin_fractions, "net margin fractions", 0.0)
        for values in (
            self.oil_prices_usd_per_barrel,
            self.variable_costs_usd_per_barrel,
            self.net_margin_fractions,
        ):
            if len(values) != count:
                raise ValueError("Scenario decks must span the horizon")
        if any(value > 1 for value in self.net_margin_fractions):
            raise ValueError("Net margin fractions must be at most one")
        for values, kind in (
            (self.wells, WellSchedule),
            (self.expenditures, Expenditure),
        ):
            if not isinstance(values, tuple) or any(
                not isinstance(v, kind) for v in values
            ):
                raise ValueError("Scenario schedules must be immutable typed tuples")
        _finite(self.discount_rate_per_period, "discount rate")
        _index(self.first_discount_period, "first discount period")
        if self.discount_rate_per_period <= -1:
            raise ValueError("Discount rate must exceed minus one")
