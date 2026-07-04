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
    """Run the #717 one-field UKCS chain slice."""
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
    if dev_system == "unknown":
        dev_system = "subsea15"

    cashflows = CashflowEngine(
        AssumptionsManager(),
        dev_system=dev_system,
        fiscal_terms=get_fiscal_terms("uk"),
    ).generate_monthly_cashflow(
        fdas_production,
        {"drilling_monthly": {}},
        price_deck,
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
