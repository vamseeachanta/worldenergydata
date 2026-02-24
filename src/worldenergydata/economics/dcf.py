"""
ABOUTME: Discounted cash flow — NPV and MIRR for field development economics.
ABOUTME: Integrates with decline curve production profiles via CashFlowSchedule.

Formulas
--------
NPV:
    NPV = sum(CF_t / (1+r)^t  for t in 0..n)
    CF_t = revenue_t - opex_t - capex_t - carbon_cost_t

MIRR:
    MIRR = (FV_positive / PV_negative)^(1/n) - 1
    FV_positive = future value of positive CF at reinvestment_rate
    PV_negative = present value of negative CF at finance_rate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CashFlowSchedule:
    """Per-period cash flow components for a field development project.

    All primary lists must share the same length (one entry per period, t=0..n).

    Attributes
    ----------
    years:
        Period indices (e.g. [0, 1, 2, ..., n]).  Used for labelling.
    capex:
        Capital expenditures (USD).  Positive values are outflows.
    revenue:
        Gross revenue (USD).  Positive values are inflows.
    opex:
        Operating expenditures (USD).  Positive values are outflows.
    carbon_cost:
        Carbon tax / ETS cost (USD).  Positive values are outflows.
    emission_tco2_per_period:
        Optional: total CO2-equivalent emissions per period (tCO2).
        When populated (by :func:`build_cash_flow_schedule`), this allows
        :func:`~worldenergydata.economics.carbon.carbon_npv_curve` and
        :func:`~worldenergydata.economics.carbon.breakeven_carbon_price`
        to recalculate carbon costs at arbitrary carbon prices.
    """

    years: List[int]
    capex: List[float]
    revenue: List[float]
    opex: List[float]
    carbon_cost: List[float]
    emission_tco2_per_period: Optional[List[float]] = field(default=None)

    def __post_init__(self) -> None:
        lengths = {
            "years": len(self.years),
            "capex": len(self.capex),
            "revenue": len(self.revenue),
            "opex": len(self.opex),
            "carbon_cost": len(self.carbon_cost),
        }
        unique = set(lengths.values())
        if len(unique) != 1:
            raise ValueError(
                f"CashFlowSchedule arrays must have the same length: {lengths}"
            )
        if self.emission_tco2_per_period is not None:
            if len(self.emission_tco2_per_period) != len(self.years):
                raise ValueError(
                    "emission_tco2_per_period must have the same length as years"
                )


@dataclass
class NPVResult:
    """Output from :func:`calculate_npv`.

    Attributes
    ----------
    npv:
        Net present value (USD).
    discount_rate:
        Discount rate used (fractional, e.g. 0.10 for 10%).
    net_cash_flows:
        Undiscounted net cash flow per period.
    discounted_cash_flows:
        Discounted net cash flow per period.
    """

    npv: float
    discount_rate: float
    net_cash_flows: List[float]
    discounted_cash_flows: List[float]


@dataclass
class MIRRResult:
    """Output from :func:`calculate_mirr`.

    Attributes
    ----------
    mirr:
        Modified internal rate of return (fractional).
    finance_rate:
        Rate used to discount negative cash flows.
    reinvestment_rate:
        Rate used to compound positive cash flows.
    pv_negatives:
        Present value of negative cash flows (positive number).
    fv_positives:
        Future value of positive cash flows.
    n_periods:
        Number of periods in the schedule.
    """

    mirr: float
    finance_rate: float
    reinvestment_rate: float
    pv_negatives: float
    fv_positives: float
    n_periods: int


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def calculate_npv(
    schedule: CashFlowSchedule,
    discount_rate: float,
) -> NPVResult:
    """Compute net present value for a cash flow schedule.

    Parameters
    ----------
    schedule:
        Per-period revenue, capex, opex, and carbon cost.
    discount_rate:
        Annual discount rate (fractional).  Must be > -1.

    Returns
    -------
    NPVResult
        NPV, per-period net and discounted cash flows.

    Raises
    ------
    ValueError
        If *discount_rate* <= -1.
    """
    if discount_rate <= -1.0:
        raise ValueError(
            f"discount_rate must be > -1, got {discount_rate}"
        )

    capex = np.asarray(schedule.capex, dtype=float)
    revenue = np.asarray(schedule.revenue, dtype=float)
    opex = np.asarray(schedule.opex, dtype=float)
    carbon = np.asarray(schedule.carbon_cost, dtype=float)

    net_cf = revenue - opex - capex - carbon

    n = len(net_cf)
    t = np.arange(n, dtype=float)
    discount_factors = (1.0 + discount_rate) ** t
    discounted_cf = net_cf / discount_factors

    npv_value = float(np.sum(discounted_cf))

    return NPVResult(
        npv=npv_value,
        discount_rate=discount_rate,
        net_cash_flows=net_cf.tolist(),
        discounted_cash_flows=discounted_cf.tolist(),
    )


def calculate_mirr(
    schedule: CashFlowSchedule,
    finance_rate: float,
    reinvestment_rate: float,
) -> MIRRResult:
    """Compute Modified Internal Rate of Return (MIRR).

    Parameters
    ----------
    schedule:
        Per-period revenue, capex, opex, and carbon cost.
    finance_rate:
        Rate used to discount negative cash flows to t=0.
    reinvestment_rate:
        Rate used to compound positive cash flows to t=n.

    Returns
    -------
    MIRRResult

    Raises
    ------
    ValueError
        If there are no negative net cash flows in the schedule.
    """
    capex = np.asarray(schedule.capex, dtype=float)
    revenue = np.asarray(schedule.revenue, dtype=float)
    opex = np.asarray(schedule.opex, dtype=float)
    carbon = np.asarray(schedule.carbon_cost, dtype=float)

    net_cf = revenue - opex - capex - carbon
    n = len(net_cf) - 1  # number of periods (t=0..n)

    neg_mask = net_cf < 0
    pos_mask = net_cf >= 0

    if not np.any(neg_mask):
        raise ValueError(
            "MIRR requires at least one negative net cash flow in the schedule."
        )

    t = np.arange(len(net_cf), dtype=float)

    # PV of negative cash flows discounted at finance_rate to t=0
    pv_neg_flows = net_cf[neg_mask] / (1.0 + finance_rate) ** t[neg_mask]
    pv_negatives = float(np.abs(np.sum(pv_neg_flows)))

    # FV of positive cash flows compounded at reinvestment_rate to t=n
    fv_pos_flows = net_cf[pos_mask] * (1.0 + reinvestment_rate) ** (n - t[pos_mask])
    fv_positives = float(np.sum(fv_pos_flows))

    mirr_value = float((fv_positives / pv_negatives) ** (1.0 / n) - 1.0)

    return MIRRResult(
        mirr=mirr_value,
        finance_rate=finance_rate,
        reinvestment_rate=reinvestment_rate,
        pv_negatives=pv_negatives,
        fv_positives=fv_positives,
        n_periods=n,
    )


# ---------------------------------------------------------------------------
# Convenience constructor
# ---------------------------------------------------------------------------


def build_cash_flow_schedule(
    years: List[int],
    production_boe_per_year: List[float],
    oil_price_usd_per_boe: float,
    opex_usd_per_boe: float,
    capex_by_year: List[float],
    carbon_cost_usd_per_tonne: float,
    scope1_tco2_per_boe: float,
    scope2_tco2_per_boe: float,
) -> CashFlowSchedule:
    """Construct a :class:`CashFlowSchedule` from field production parameters.

    Emission volumes (tCO2/period) are stored in
    ``emission_tco2_per_period`` so that carbon sensitivity functions can
    recompute carbon costs at arbitrary prices without additional inputs.

    Parameters
    ----------
    years:
        Period labels, e.g. ``[0, 1, 2, ..., n]``.
    production_boe_per_year:
        Annual production in barrels of oil equivalent (boe).
        t=0 is typically 0 (development phase).
    oil_price_usd_per_boe:
        Flat oil/gas price assumption (USD/boe).
    opex_usd_per_boe:
        Operating cost per boe (USD/boe).
    capex_by_year:
        Capital expenditure per period (USD).
    carbon_cost_usd_per_tonne:
        Carbon price (USD/tonne CO2).
    scope1_tco2_per_boe:
        Scope 1 emission intensity (tCO2/boe).
    scope2_tco2_per_boe:
        Scope 2 emission intensity (tCO2/boe).

    Returns
    -------
    CashFlowSchedule
        With ``emission_tco2_per_period`` populated.
    """
    prod = np.asarray(production_boe_per_year, dtype=float)
    emission_intensity = scope1_tco2_per_boe + scope2_tco2_per_boe

    revenue = prod * oil_price_usd_per_boe
    opex = prod * opex_usd_per_boe
    emission_volumes = prod * emission_intensity
    carbon = emission_volumes * carbon_cost_usd_per_tonne

    return CashFlowSchedule(
        years=list(years),
        capex=list(np.asarray(capex_by_year, dtype=float)),
        revenue=revenue.tolist(),
        opex=opex.tolist(),
        carbon_cost=carbon.tolist(),
        emission_tco2_per_period=emission_volumes.tolist(),
    )
