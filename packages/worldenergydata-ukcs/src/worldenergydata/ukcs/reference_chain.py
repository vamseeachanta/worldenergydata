"""UKCS NSTA reference-chain runner (#717).

Minimal vertical slice:
``UkcsAdapter.fetch`` -> ``to_fdas_production`` -> ``CashflowEngine`` and
``build_uk_field_concept`` -> ``recommend``. The economics output is explicitly
pre-tax chain plumbing, not a UK investment NPV headline.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from math import isfinite
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
    drilling_timeline: dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run the #717 chain with explicit drilling days and nonempty production.

    Raises ValueError if the drilling basis or production is unavailable;
    nonnumeric drilling-day values raise TypeError.
    Costs retain the FDAS assumptions and pre-tax qualification limits.
    """
    drilling_monthly = (
        drilling_timeline.get("drilling_monthly")
        if isinstance(drilling_timeline, Mapping)
        else None
    )
    if not isinstance(drilling_monthly, Mapping) or not drilling_monthly:
        raise ValueError("drilling_timeline requires nonempty drilling_monthly")
    # Issue 1284: zero/unknown drilling effort cannot establish drilling capital.
    for month, days in drilling_monthly.items():
        try:
            datetime.strptime(month, "%Y-%m")
        except (TypeError, ValueError) as exc:
            raise ValueError("drilling_monthly requires year-month keys") from exc
        if isinstance(days, bool) or not isinstance(days, (int, float)):
            raise TypeError("drilling_monthly requires numeric days")
        if not isfinite(days) or days < 0:
            raise ValueError("drilling_monthly requires finite non-negative days")
    if not any(days > 0 for days in drilling_monthly.values()):
        raise ValueError("drilling_monthly requires positive drilling effort")
    unified = adapter.fetch(
        ProductionQuery(
            regions=["ukcs"],
            fields=[field_name],
            start=start,
            end=end,
        )
    )
    fdas_production = to_fdas_production(unified)
    first_oil = _first_oil_date(fdas_production)
    field_concept = build_uk_field_concept(field_meta)
    ranked_concepts = recommend(field_concept)

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
        drilling_timeline,
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
        raise ValueError("production is empty; cannot determine first-oil date")
    first_period = str(fdas_production["YEAR_MONTH"].min())
    return datetime.strptime(first_period, "%Y-%m")


def _pre_tax_metrics(cashflows) -> Dict[str, float]:
    return {
        "months": len(cashflows),
        "gross_revenue_usd": float(sum(cf.oil_revenue_usd for cf in cashflows)),
        "royalty_usd": float(sum(cf.royalty_usd for cf in cashflows)),
        "net_cashflow_usd": float(sum(cf.net_cashflow_usd for cf in cashflows)),
    }
