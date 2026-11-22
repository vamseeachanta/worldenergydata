"""UKCS NSTA reference-chain runner (#717).

Minimal vertical slice:
``UkcsAdapter.fetch`` -> ``to_fdas_production`` -> ``CashflowEngine`` and
``build_uk_field_concept`` -> ``recommend``. The economics output is explicitly
pre-tax chain plumbing, not a UK investment NPV headline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    dev_system_from_water_depth_m,
)
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import get_fiscal_terms
from worldenergydata.field_development.recommendation import recommend
from worldenergydata.production.unified.query import ProductionQuery
from worldenergydata.ukcs.field_concept import build_uk_field_concept


def run_ukcs_reference_chain(
    *,
    adapter,
    field_meta: Dict[str, Any],
    field_name: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    oil_price_usd_bbl: float = 75.0,
) -> Dict[str, Any]:
    """Run the UKCS chain with a flat assumed Brent price in USD/BBL.

    oil_price_usd_bbl is a scenario input, not a fetched benchmark quote.
    """
    unified = adapter.fetch(
        ProductionQuery(
            regions=["ukcs"],
            fields=[field_name],
            start=start,
            end=end,
        )
    )
    fdas_production = to_fdas_production(unified)
    field_concept = build_uk_field_concept(field_meta)
    ranked_concepts = recommend(field_concept)

    first_oil = _first_oil_date(fdas_production)
    price_deck = {
        str(year_month): oil_price_usd_bbl
        for year_month in fdas_production.get("YEAR_MONTH", pd.Series(dtype="object"))
    }
    dev_system = dev_system_from_water_depth_m(field_concept.water_depth_m)
    fallback = dev_system == "unknown"
    if fallback:
        dev_system = "subsea15"

    assumptions = AssumptionsManager()
    cashflows = CashflowEngine(
        assumptions,
        dev_system=dev_system,
        fiscal_terms=get_fiscal_terms("uk"),
    ).generate_monthly_cashflow(
        fdas_production,
        {"drilling_monthly": {}},
        price_deck,
        first_oil,
        oil_prices_by_marker={"brent": price_deck},
    )

    return {
        "field_name": field_name,
        "unified_production": unified,
        "fdas_production": fdas_production,
        "field_concept": field_concept,
        "ranked_concepts": ranked_concepts,
        "economics_label": "chain_plumbing_pre_tax",
        "pre_tax_metrics": _pre_tax_metrics(cashflows),
        "cashflow_basis": {
            "development_system": dev_system,
            "development_system_basis": (
                "fallback: water depth unknown"
                if fallback
                else "classified from water_depth_m"
            ),
            "assumptions_source": "FDAS DEFAULT_ASSUMPTIONS",
            "oil_price_usd_bbl": oil_price_usd_bbl,
            "variable_opex_usd_per_bbl": assumptions.get(
                dev_system, "VARIABLE_OPEX_$/BBL", 12.0
            ),
            "assumed_first_oil": first_oil.strftime("%Y-%m"),
            "first_oil_basis": "first selected production observation",
            "cashflow_window": {
                "first_period": cashflows[0].year_month if cashflows else None,
                "last_period": cashflows[-1].year_month if cashflows else None,
                "row_count": len(cashflows),
            },
            "host_capex_assumption_mm_usd": assumptions.get(
                dev_system, "HOST_CAPEX_MM"
            ),
            "applied_costs_usd": {
                name: float(sum(getattr(cf, name + "_usd") for cf in cashflows))
                for name in (
                    "variable_opex",
                    "fixed_opex",
                    "drilling_capex",
                    "facilities_capex",
                    "host_capex",
                )
            },
        },
    }


def build_uk_field_concept_from_meta(field_meta: Dict[str, Any]):
    """Compatibility alias for callers that prefer explicit meta wording."""
    return build_uk_field_concept(field_meta)


def _first_oil_date(fdas_production: pd.DataFrame) -> datetime:
    if fdas_production.empty:
        return datetime(1970, 1, 1)
    first_period = str(fdas_production["YEAR_MONTH"].min())
    return datetime.strptime(first_period, "%Y-%m")


def _pre_tax_metrics(cashflows) -> Dict[str, float]:
    return {
        "months": len(cashflows),
        "gross_revenue_usd": float(sum(cf.oil_revenue_usd for cf in cashflows)),
        "royalty_usd": float(sum(cf.royalty_usd for cf in cashflows)),
        "net_cashflow_usd": float(sum(cf.net_cashflow_usd for cf in cashflows)),
    }
