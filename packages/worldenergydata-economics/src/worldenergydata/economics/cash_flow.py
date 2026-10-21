"""Annual cash-flow schedules and production-to-cost accounting.

Valuation belongs to worldenergydata.fdas.core.financial. Schedule years are
labels; array position supplies the valuation period (first entry at t=0).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


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

    years: list[int]
    capex: list[float]
    revenue: list[float]
    opex: list[float]
    carbon_cost: list[float]
    emission_tco2_per_period: list[float] | None = field(default=None)

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
        if self.emission_tco2_per_period is not None and len(
            self.emission_tco2_per_period
        ) != len(self.years):
            raise ValueError(
                "emission_tco2_per_period must have the same length as years"
            )

    def net_cashflows(self) -> np.ndarray:
        """Return revenue less outflows; pass to FDAS with an explicit period.

        Accounting identity from the former economics/dcf.py (2026).
        Years are labels; rows are consecutive, equally spaced annual periods.
        """
        return (
            np.asarray(self.revenue, dtype=float)
            - np.asarray(self.opex, dtype=float)
            - np.asarray(self.capex, dtype=float)
            - np.asarray(self.carbon_cost, dtype=float)
        )


def build_cash_flow_schedule(
    years: list[int],
    production_boe_per_year: list[float],
    oil_price_usd_per_boe: float,
    opex_usd_per_boe: float,
    capex_by_year: list[float],
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
