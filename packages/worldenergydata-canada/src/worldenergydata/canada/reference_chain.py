"""Canada C-NLOER reference-chain runner (#719).

Minimal vertical slice mirroring the merged Norway (#716) / Spain (#763) chains:
``CanadaAdapter.fetch`` -> ``to_fdas_production`` -> ``CashflowEngine`` and
``build_canada_field_concept`` -> ``recommend``. Economics are explicitly pre-tax
chain plumbing, not a Canada investment NPV headline.

Dev-system: the primary field Hibernia is a shallow-water (~80 m) Gravity-Based
Structure with dry trees, so the depth classifier's ``dry`` result is accurate.
For the FPSO+subsea fields it is a documented simplification (see
``dev_system_source`` in the metrics + the #719 per-field-concept follow-on).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from worldenergydata.canada.field_concept import build_canada_field_concept
from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    dev_system_from_water_depth_m,
)
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.field_development.recommendation import recommend
from worldenergydata.production.unified.query import ProductionQuery


def run_canada_reference_chain(
    *,
    adapter,
    field_meta: dict[str, Any],
    field_name: str,
    start: str | None = None,
    end: str | None = None,
    oil_price_usd_bbl: float = 75.0,
    gas_prices: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run a one-field Canada chain with optional realized USD/Mcf gas prices.

    Gas pricing requires standardized saleable ``gas_mcf`` input and a price
    for every production month; FDAS validates both. CNSOER gas-equivalent
    native rows require a supported realization basis before this chain.
    No gas deck preserves oil-only revenue and reports ``gas_revenue_usd`` as
    ``None`` (unpriced); an explicit zero-price deck reports 0.0 (priced zero).
    The default fiscal/cost assumptions remain illustrative, rather than
    Canadian field investment economics.
    """
    unified = adapter.fetch(
        ProductionQuery(
            regions=["canada"],
            fields=[field_name],
            start=start,
            end=end,
        )
    )
    fdas_production = to_fdas_production(unified)
    field_concept = build_canada_field_concept(field_meta)
    ranked_concepts = recommend(field_concept)

    first_oil = _first_oil_date(fdas_production)
    price_deck = {
        str(year_month): oil_price_usd_bbl
        for year_month in fdas_production.get("YEAR_MONTH", pd.Series(dtype="object"))
    }
    dev_system = dev_system_from_water_depth_m(field_concept.water_depth_m)
    if dev_system == "unknown":
        dev_system = "subsea15"

    cashflows = CashflowEngine(
        AssumptionsManager(), dev_system=dev_system
    ).generate_monthly_cashflow(
        fdas_production,
        {"drilling_monthly": {}},
        price_deck,
        first_oil,
        gas_prices=gas_prices,
    )

    return {
        "field_name": field_name,
        "unified_production": unified,
        "fdas_production": fdas_production,
        "field_concept": field_concept,
        "ranked_concepts": ranked_concepts,
        "economics_label": "chain_plumbing_pre_tax",
        "dev_system": dev_system,
        "pre_tax_metrics": _pre_tax_metrics(
            cashflows, dev_system, gas_priced=gas_prices is not None
        ),
    }


def _first_oil_date(fdas_production: pd.DataFrame) -> datetime:
    if fdas_production.empty:
        return datetime(1970, 1, 1)
    first_period = str(fdas_production["YEAR_MONTH"].min())
    return datetime.strptime(first_period, "%Y-%m")


def _pre_tax_metrics(cashflows, dev_system: str, *, gas_priced: bool) -> dict[str, Any]:
    return {
        "months": len(cashflows),
        # Revenue = quantity * realized unit price, summed across streams.
        # Source: OpenStax, Principles of Managerial Accounting (2019), section
        # 3.2, sales dollars from units times selling price; implemented by the
        # existing FDAS monthly_gas_revenue function without unit conversion.
        "gross_revenue_usd": float(sum(cf.total_revenue_usd for cf in cashflows)),
        "oil_revenue_usd": float(sum(cf.oil_revenue_usd for cf in cashflows)),
        "gas_revenue_usd": (
            float(sum(cf.gas_revenue_usd for cf in cashflows)) if gas_priced else None
        ),
        "royalty_usd": float(sum(cf.royalty_usd for cf in cashflows)),
        "host_capex_usd": float(sum(cf.host_capex_usd for cf in cashflows)),
        "net_cashflow_usd": float(sum(cf.net_cashflow_usd for cf in cashflows)),
        # dev_system from the depth classifier (see module docstring); per-field
        # GBS-vs-FPSO/subsea concept override is a #719 follow-on.
        "dev_system_source": "depth_classifier",
    }
