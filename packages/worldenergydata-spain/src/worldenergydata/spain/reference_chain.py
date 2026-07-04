"""Spain CORES reference-chain runner (#763)."""

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
from worldenergydata.spain.field_concept import build_spain_field_concept


def run_spain_reference_chain(
    *,
    adapter,
    field_meta: Dict[str, Any],
    field_name: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    oil_price_usd_bbl: float = 75.0,
) -> Dict[str, Any]:
    """Run the one-field Spain CORES chain slice."""
    unified = adapter.fetch(
        ProductionQuery(
            regions=["spain"],
            fields=[field_name],
            start=start,
            end=end,
        )
    )
    fdas_production = to_fdas_production(unified)
    field_concept = build_spain_field_concept(field_meta)
    ranked_concepts = recommend(field_concept)

    first_oil = _first_oil_date(fdas_production)
    price_deck = {
        str(year_month): oil_price_usd_bbl
        for year_month in fdas_production.get("YEAR_MONTH", pd.Series(dtype="object"))
    }
    dev_system = _spain_dev_system(field_meta, field_concept.water_depth_m)
    cashflows = CashflowEngine(
        AssumptionsManager(),
        dev_system=dev_system,
    ).generate_monthly_cashflow(
        fdas_production,
        {"drilling_monthly": {}},
        price_deck,
        first_oil,
    )

    onshore_flag = _is_onshore(field_meta)
    return {
        "field_name": field_name,
        "unified_production": unified,
        "fdas_production": fdas_production,
        "field_concept": field_concept,
        "ranked_concepts": ranked_concepts,
        "concept_screening_label": "wiring_only_onshore_sparse_metadata",
        "economics_label": "chain_plumbing_pre_tax",
        "dev_system": dev_system,
        "pre_tax_metrics": _pre_tax_metrics(cashflows, onshore_flag),
    }


def _spain_dev_system(field_meta: Dict[str, Any], water_depth_m: Any) -> str:
    if _is_onshore(field_meta):
        return "dry"
    dev_system = dev_system_from_water_depth_m(water_depth_m)
    if dev_system == "unknown":
        return "dry"
    return dev_system


def _is_onshore(field_meta: Dict[str, Any]) -> bool:
    env = str(
        field_meta.get("environment") or field_meta.get("environment_type") or ""
    ).lower()
    return env in {"onshore", "land", "terra"}


def _first_oil_date(fdas_production: pd.DataFrame) -> datetime:
    if fdas_production.empty:
        return datetime(1970, 1, 1)
    first_period = str(fdas_production["YEAR_MONTH"].min())
    return datetime.strptime(first_period, "%Y-%m")


def _pre_tax_metrics(cashflows, onshore_model_mismatch: bool) -> Dict[str, float]:
    return {
        "months": len(cashflows),
        "gross_revenue_usd": float(sum(cf.oil_revenue_usd for cf in cashflows)),
        "royalty_usd": float(sum(cf.royalty_usd for cf in cashflows)),
        "host_capex_usd": float(sum(cf.host_capex_usd for cf in cashflows)),
        "net_cashflow_usd": float(sum(cf.net_cashflow_usd for cf in cashflows)),
        "onshore_model_mismatch": onshore_model_mismatch,
    }
