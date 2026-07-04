"""Norway SODIR reference-chain runner (#716).

Minimal vertical slice:
``SodirAdapter.fetch`` -> ``to_fdas_production`` -> ``CashflowEngine`` and
``sodir_field_to_concept`` -> ``recommend``. The economics output is explicitly
pre-tax chain plumbing, not a Norway investment NPV headline.
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
from worldenergydata.field_development.recommendation import recommend
from worldenergydata.production.unified.query import ProductionQuery
from worldenergydata.sodir.field_concept import build_norway_field_concept


def run_norway_reference_chain(
    *,
    adapter,
    field_meta: Dict[str, Any],
    field_name: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    oil_price_usd_bbl: float = 75.0,
) -> Dict[str, Any]:
    """Run the #716 one-field Norway chain slice.

    Args:
        adapter: production adapter exposing ``fetch(ProductionQuery)``.
        field_meta: processed SODIR field metadata from ``FieldProcessor``.
        field_name: SODIR field name to fetch and report.
        start: optional inclusive ``YYYY-MM`` lower bound.
        end: optional inclusive ``YYYY-MM`` upper bound.
        oil_price_usd_bbl: flat oil-price deck for the plumbing run.

    Returns:
        Dictionary with unified/FDAS production, FieldConcept, ranked concepts,
        and finite pre-tax cashflow metrics labeled as chain plumbing.
    """
    unified = adapter.fetch(
        ProductionQuery(
            regions=["ncs"],
            fields=[field_name],
            start=start,
            end=end,
        )
    )
    fdas_production = to_fdas_production(unified)
    field_concept = build_norway_field_concept(field_meta)
    ranked_concepts = recommend(field_concept)

    first_oil = _first_oil_date(fdas_production)
    wti_prices = {
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
        wti_prices,
        first_oil,
    )

    return {
        "field_name": field_name,
        "unified_production": unified,
        "fdas_production": fdas_production,
        "field_concept": field_concept,
        "ranked_concepts": ranked_concepts,
        "economics_label": "chain_plumbing_pre_tax",
        "pre_tax_metrics": _pre_tax_metrics(cashflows),
    }


def _first_oil_date(fdas_production: pd.DataFrame) -> datetime:
    if fdas_production.empty:
        return datetime(1970, 1, 1)
    first_period = str(fdas_production["YEAR_MONTH"].min())
    return datetime.strptime(first_period, "%Y-%m")


def _pre_tax_metrics(cashflows) -> Dict[str, float]:
    return {
        "months": len(cashflows),
        "gross_revenue_usd": float(sum(cf.oil_revenue_usd for cf in cashflows)),
        "net_cashflow_usd": float(sum(cf.net_cashflow_usd for cf in cashflows)),
    }
