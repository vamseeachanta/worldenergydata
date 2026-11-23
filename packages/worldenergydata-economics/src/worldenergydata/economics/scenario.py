"""Development schedule to production, expenditure, revenue, cash flow and NPV.

Inputs: frozen scenario_inputs dataclasses; USD, USD/barrel, barrels/day,
production days and an explicit period duration in years. Rates are fractions
per economic period. No default engineering or economic assumption is supplied.

Method: sequential well timing; recursive retention plus additions; rate times
supplied production days; component costs and explicit percentage bases; margin
revenue times net share; subtract scheduled capital and operating expenditure;
discount each net flow at an explicit integer period offset. Shared dcf functions
perform revenue multiplication, net cash flow and discounting.

Limits: deterministic piecewise-constant rates, whole-period activity timing,
oil only, no reservoir constraints, fiscal regime, inflation, IRR or optimization.
Taxes, abandonment and other outflows require explicit scheduled expenditures.
No engineering standard is inferred from a legacy engineering workbook.

Input gaps: rates, retention, additions, timing, day counts, price decks,
operating costs, shares, cost estimates, allocation bases, rounding and discount
basis require qualified sources. Required inputs replace unsourced assumptions;
USD denomination does not establish price year or estimate freshness. See the
adjacent scenario_README.md for the complete input responsibility register.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import accumulate

from .scenario_costs import activity_cost_usd, cost_breakdown, expenditure_profile_usd
from .scenario_finance import (
    discounted_cash_flow_usd,
    net_cash_flow_usd,
    npv_usd,
    revenue_usd,
)
from .scenario_inputs import Periods, ScenarioInputs, WellSchedule, _finite, _series

__all__ = [
    "Periods",
    "ScenarioInputs",
    "WellSchedule",
    "ProductionProfile",
    "ScenarioResult",
    "ScenarioComparison",
    "production_profile",
    "evaluate_scenario",
    "compare_scenarios",
    "activity_cost_usd",
    "cost_breakdown",
    "expenditure_profile_usd",
    "discounted_cash_flow_usd",
    "net_cash_flow_usd",
    "npv_usd",
    "revenue_usd",
]


@dataclass(frozen=True)
class ProductionProfile:
    """Period rates [barrels/day] and period volumes [barrels]."""

    rates_barrels_per_day: tuple[float, ...]
    volumes_barrels: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.rates_barrels_per_day) != len(self.volumes_barrels):
            raise ValueError("Rates and volumes must share a horizon")
        _series(self.rates_barrels_per_day, "rates_barrels_per_day", 0.0)
        _series(self.volumes_barrels, "volumes_barrels", 0.0)


def production_profile(well: WellSchedule, periods: Periods) -> ProductionProfile:
    """Apply supplied retention and additions after drilling and completion."""
    count = len(periods.production_days)
    if len(well.retention_fractions) != count:
        raise ValueError("Well schedule must span the period horizon")
    first = (
        well.drilling_start_period
        + well.drilling_periods
        + well.completion_periods
        + well.production_delay_periods
    )
    if any(well.additions_barrels_per_day[:first]):
        raise ValueError("Production additions precede completion and delay")
    rates = []
    previous = 0.0
    for index in range(count):
        if index < first:
            rate = 0.0
        elif index == first:
            rate = (
                well.initial_rate_barrels_per_day
                + well.additions_barrels_per_day[index]
            )
        else:
            rate = (
                previous * well.retention_fractions[index]
                + well.additions_barrels_per_day[index]
            )
        rates.append(rate)
        previous = rate
    return ProductionProfile(
        tuple(rates),
        tuple(rate * days for rate, days in zip(rates, periods.production_days)),
    )


@dataclass(frozen=True)
class ScenarioResult:
    """Scenario output; all currency quantities are USD, with original slots."""

    name: str
    wells: tuple[ProductionProfile, ...]
    production: ProductionProfile
    gross_revenue_usd: tuple[float, ...]
    variable_operating_cost_usd: tuple[float, ...]
    net_margin_revenue_usd: tuple[float, ...]
    capital_cost_usd: tuple[float, ...]
    scheduled_operating_cost_usd: tuple[float, ...]
    net_cash_flow_usd: tuple[float, ...]
    cumulative_cash_flow_usd: tuple[float, ...]
    discounted_cash_flow_usd: tuple[float, ...]
    npv_usd: float

    def __post_init__(self) -> None:
        for name in (
            "gross_revenue_usd",
            "variable_operating_cost_usd",
            "net_margin_revenue_usd",
            "capital_cost_usd",
            "scheduled_operating_cost_usd",
            "net_cash_flow_usd",
            "cumulative_cash_flow_usd",
            "discounted_cash_flow_usd",
        ):
            _series(getattr(self, name), name)
        _finite(self.npv_usd, "npv_usd")


def evaluate_scenario(inputs: ScenarioInputs) -> ScenarioResult:
    """Evaluate one scenario without workbook dependencies or input mutation."""
    count = len(inputs.periods.production_days)
    wells = tuple(production_profile(well, inputs.periods) for well in inputs.wells)
    rates = tuple(
        sum(well.rates_barrels_per_day[i] for well in wells) for i in range(count)
    )
    volumes = tuple(
        rate * days for rate, days in zip(rates, inputs.periods.production_days)
    )
    gross = revenue_usd(volumes, inputs.oil_prices_usd_per_barrel)
    variable = revenue_usd(volumes, inputs.variable_costs_usd_per_barrel)
    margin = tuple(
        (revenue - cost) * share
        for revenue, cost, share in zip(gross, variable, inputs.net_margin_fractions)
    )
    capital = expenditure_profile_usd(inputs.expenditures, count, "capital")
    operating = expenditure_profile_usd(inputs.expenditures, count, "operating")
    flows = net_cash_flow_usd(margin, capital, operating)
    discounted = discounted_cash_flow_usd(
        flows, inputs.discount_rate_per_period, inputs.first_discount_period
    )
    return ScenarioResult(
        inputs.name,
        wells,
        ProductionProfile(rates, volumes),
        gross,
        variable,
        margin,
        capital,
        operating,
        flows,
        tuple(accumulate(flows)),
        discounted,
        sum(discounted),
    )


@dataclass(frozen=True)
class ScenarioComparison:
    """Input-order results and NPV increments relative to the first scenario."""

    scenarios: tuple[ScenarioResult, ...]
    incremental_npv_usd: tuple[float, ...]


def compare_scenarios(inputs: tuple[ScenarioInputs, ...]) -> ScenarioComparison:
    """Compare USD scenarios sharing horizon, day counts, period and discount basis."""
    if not isinstance(inputs, tuple) or not inputs:
        raise ValueError("A nonempty immutable scenario tuple is required")
    basis = inputs[0]
    if len({item.name for item in inputs}) != len(inputs):
        raise ValueError("Comparison scenario names must be unique")
    for item in inputs[1:]:
        if (
            item.periods != basis.periods
            or item.discount_rate_per_period != basis.discount_rate_per_period
            or item.first_discount_period != basis.first_discount_period
        ):
            raise ValueError("Comparison requires identical period and discount bases")
    results = tuple(evaluate_scenario(item) for item in inputs)
    increments = tuple(item.npv_usd - results[0].npv_usd for item in results)
    _series(increments, "incremental_npv_usd")
    return ScenarioComparison(results, increments)
