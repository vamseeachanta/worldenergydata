"""
ABOUTME: Carbon cost sensitivity analysis for field development economics.
ABOUTME: NPV-vs-carbon-price curve, breakeven solver, and tornado chart output.

Public API
----------
carbon_npv_curve      — NPV sweep over a range of carbon prices
breakeven_carbon_price — solve for NPV = 0 carbon price
tornado_sensitivity   — per-parameter swing analysis for tornado charts

Design note
-----------
``carbon_npv_curve`` and ``breakeven_carbon_price`` use the
``emission_tco2_per_period`` field stored by
:func:`~worldenergydata.economics.dcf.build_cash_flow_schedule` to
recompute carbon costs at arbitrary prices without redundant input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from scipy.optimize import brentq

from worldenergydata.economics.dcf import (
    CashFlowSchedule,
    build_cash_flow_schedule,
    calculate_npv,
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CarbonSensitivityResult:
    """Output from :func:`carbon_npv_curve`.

    Attributes
    ----------
    carbon_prices:
        Array of carbon prices evaluated (USD/tonne CO2).
    npv_values:
        NPV for each carbon price (USD).
    base_npv:
        NPV at carbon_price = 0 (USD).
    discount_rate:
        Discount rate used in NPV calculations.
    """

    carbon_prices: np.ndarray
    npv_values: np.ndarray
    base_npv: float
    discount_rate: float


@dataclass
class TornadoEntry:
    """Single parameter row in a tornado sensitivity chart.

    Attributes
    ----------
    parameter:
        Human-readable parameter name (e.g. "Oil price (USD/boe)").
    low_npv:
        NPV when parameter is at its low scenario value.
    high_npv:
        NPV when parameter is at its high scenario value.
    base_npv:
        NPV at base-case parameter value.
    swing:
        Absolute range ``abs(high_npv - low_npv)``.
    low_value:
        Parameter value for the low scenario.
    high_value:
        Parameter value for the high scenario.
    base_value:
        Parameter value for the base case.
    """

    parameter: str
    low_npv: float
    high_npv: float
    base_npv: float
    swing: float
    low_value: float
    high_value: float
    base_value: float


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------


def carbon_npv_curve(
    base_schedule: CashFlowSchedule,
    discount_rate: float,
    carbon_prices: np.ndarray,
) -> CarbonSensitivityResult:
    """Compute NPV for a range of carbon prices.

    The *base_schedule* supplies the production profile, capex, opex, and
    revenue.  Emission volumes are taken from
    ``base_schedule.emission_tco2_per_period`` (set by
    :func:`~worldenergydata.economics.dcf.build_cash_flow_schedule`).

    At each carbon price the per-period carbon cost is recomputed as::

        carbon_cost_t = emission_tco2_t * carbon_price

    Parameters
    ----------
    base_schedule:
        Reference schedule built via :func:`build_cash_flow_schedule`.
        Must have ``emission_tco2_per_period`` populated.
    discount_rate:
        Annual discount rate (fractional).
    carbon_prices:
        1-D array of carbon prices to evaluate (USD/tonne CO2).

    Returns
    -------
    CarbonSensitivityResult
    """
    emissions = _get_emissions(base_schedule)

    # base NPV is computed with carbon_price = 0
    zero_carbon_sched = _schedule_at_price(base_schedule, emissions, 0.0)
    base_npv = calculate_npv(zero_carbon_sched, discount_rate).npv

    npv_values: list[float] = []
    for price in carbon_prices:
        sched_p = _schedule_at_price(base_schedule, emissions, float(price))
        npv_values.append(calculate_npv(sched_p, discount_rate).npv)

    return CarbonSensitivityResult(
        carbon_prices=np.asarray(carbon_prices, dtype=float),
        npv_values=np.asarray(npv_values, dtype=float),
        base_npv=base_npv,
        discount_rate=discount_rate,
    )


def breakeven_carbon_price(
    base_schedule: CashFlowSchedule,
    discount_rate: float,
    search_upper: float = 2000.0,
) -> Optional[float]:
    """Find the carbon price at which NPV = 0 (breakeven).

    Uses :func:`scipy.optimize.brentq` on the interval
    ``[0, search_upper]``.

    Parameters
    ----------
    base_schedule:
        Reference schedule built via :func:`build_cash_flow_schedule`.
        Must have ``emission_tco2_per_period`` populated.
    discount_rate:
        Annual discount rate (fractional).
    search_upper:
        Upper bound of the carbon price search range (USD/tonne CO2).
        Default 2 000 USD/tonne.

    Returns
    -------
    float or None
        Breakeven carbon price, or ``None`` if no sign change found
        (project is always profitable or always unprofitable across the
        search range).
    """
    emissions = _get_emissions(base_schedule)

    def _npv_at_price(price: float) -> float:
        sched = _schedule_at_price(base_schedule, emissions, price)
        return calculate_npv(sched, discount_rate).npv

    npv_low = _npv_at_price(0.0)
    npv_high = _npv_at_price(search_upper)

    if npv_low * npv_high > 0:
        return None

    try:
        result = brentq(_npv_at_price, 0.0, search_upper, xtol=1e-6, rtol=1e-9)
        return float(result)
    except ValueError:
        return None


def tornado_sensitivity(
    years: List[int],
    production_boe_per_year: List[float],
    oil_price_usd_per_boe: float,
    opex_usd_per_boe: float,
    capex_by_year: List[float],
    carbon_cost_usd_per_tonne: float,
    scope1_tco2_per_boe: float,
    scope2_tco2_per_boe: float,
    discount_rate: float,
    swing_fraction: float = 0.20,
) -> List[TornadoEntry]:
    """Generate tornado chart data by varying each key parameter ±swing_fraction.

    Each parameter is varied individually while all others are held at the
    base-case value.  The resulting low/high NPVs form one bar on the tornado
    chart.  Entries are sorted by absolute swing (largest first).

    Parameters
    ----------
    years, production_boe_per_year, oil_price_usd_per_boe, opex_usd_per_boe,
    capex_by_year, carbon_cost_usd_per_tonne, scope1_tco2_per_boe,
    scope2_tco2_per_boe:
        Base-case field economics inputs.
    discount_rate:
        Base-case discount rate for NPV calculations.
    swing_fraction:
        Fractional deviation applied to each parameter (default ±20%).

    Returns
    -------
    list[TornadoEntry]
        Sorted by swing descending.
    """
    base_schedule = build_cash_flow_schedule(
        years=years,
        production_boe_per_year=production_boe_per_year,
        oil_price_usd_per_boe=oil_price_usd_per_boe,
        opex_usd_per_boe=opex_usd_per_boe,
        capex_by_year=capex_by_year,
        carbon_cost_usd_per_tonne=carbon_cost_usd_per_tonne,
        scope1_tco2_per_boe=scope1_tco2_per_boe,
        scope2_tco2_per_boe=scope2_tco2_per_boe,
    )
    base_npv = calculate_npv(base_schedule, discount_rate).npv

    def _npv_for(dr: float = discount_rate, **overrides) -> float:
        kw = dict(
            years=years,
            production_boe_per_year=production_boe_per_year,
            oil_price_usd_per_boe=oil_price_usd_per_boe,
            opex_usd_per_boe=opex_usd_per_boe,
            capex_by_year=capex_by_year,
            carbon_cost_usd_per_tonne=carbon_cost_usd_per_tonne,
            scope1_tco2_per_boe=scope1_tco2_per_boe,
            scope2_tco2_per_boe=scope2_tco2_per_boe,
        )
        kw.update(overrides)
        sched = build_cash_flow_schedule(**kw)
        return calculate_npv(sched, dr).npv

    f = swing_fraction
    parameters = [
        dict(
            label="Oil price (USD/boe)",
            base=oil_price_usd_per_boe,
            low=oil_price_usd_per_boe * (1 - f),
            high=oil_price_usd_per_boe * (1 + f),
            kwarg="oil_price_usd_per_boe",
        ),
        dict(
            label="Opex (USD/boe)",
            base=opex_usd_per_boe,
            low=opex_usd_per_boe * (1 - f),
            high=opex_usd_per_boe * (1 + f),
            kwarg="opex_usd_per_boe",
        ),
        dict(
            label="Carbon price (USD/tonne CO2)",
            base=carbon_cost_usd_per_tonne,
            low=carbon_cost_usd_per_tonne * (1 - f),
            high=carbon_cost_usd_per_tonne * (1 + f),
            kwarg="carbon_cost_usd_per_tonne",
        ),
        dict(
            label="Discount rate",
            base=discount_rate,
            low=discount_rate * (1 - f),
            high=discount_rate * (1 + f),
            kwarg="__rate__",
        ),
    ]

    entries: list[TornadoEntry] = []
    for param in parameters:
        kwarg = param["kwarg"]
        if kwarg == "__rate__":
            low_npv = _npv_for(dr=param["low"])
            high_npv = _npv_for(dr=param["high"])
        else:
            low_npv = _npv_for(**{kwarg: param["low"]})
            high_npv = _npv_for(**{kwarg: param["high"]})

        swing = abs(high_npv - low_npv)
        entries.append(
            TornadoEntry(
                parameter=param["label"],
                low_npv=low_npv,
                high_npv=high_npv,
                base_npv=base_npv,
                swing=swing,
                low_value=param["low"],
                high_value=param["high"],
                base_value=param["base"],
            )
        )

    entries.sort(key=lambda e: e.swing, reverse=True)
    return entries


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_emissions(schedule: CashFlowSchedule) -> np.ndarray:
    """Extract emission volumes (tCO2/period) from schedule.

    Falls back to zeros if ``emission_tco2_per_period`` is not set.
    """
    if schedule.emission_tco2_per_period is not None:
        return np.asarray(schedule.emission_tco2_per_period, dtype=float)
    n = len(schedule.years)
    return np.zeros(n, dtype=float)


def _schedule_at_price(
    base: CashFlowSchedule,
    emission_volumes: np.ndarray,
    carbon_price: float,
) -> CashFlowSchedule:
    """Return a new schedule with carbon_cost recalculated at *carbon_price*."""
    new_carbon = emission_volumes * carbon_price
    return CashFlowSchedule(
        years=base.years,
        capex=base.capex,
        revenue=base.revenue,
        opex=base.opex,
        carbon_cost=new_carbon.tolist(),
        emission_tco2_per_period=base.emission_tco2_per_period,
    )
