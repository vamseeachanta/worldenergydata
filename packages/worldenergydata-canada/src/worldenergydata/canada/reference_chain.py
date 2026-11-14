"""Canada C-NLOER reference-chain runner (#719).

Minimal vertical slice mirroring the merged Norway (#716) / Spain (#763) chains:
``CanadaAdapter.fetch`` -> ``to_fdas_production`` -> ``CashflowEngine`` and
``build_canada_field_concept`` -> ``recommend``. Economics are explicitly pre-tax
chain plumbing, not a Canada investment NPV headline.

Explicit field-concept overrides (#815) select dry-tree GBS or FPSO/subsea
buckets even in shallow water. Royalty and OPEX remain generic bucket defaults,
not Canada fiscal terms; host CAPEX retains the engine's MM/USD unit defect.
Unmapped fields retain depth classification or the missing-depth default;
``dev_system_source`` records the selection method in the result and metrics.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

import pandas as pd

from worldenergydata.canada.development_wells import DevelopmentWell
from worldenergydata.canada.field_concept import (
    build_canada_field_concept,
    resolve_canada_dev_system,
)
from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.field_development.recommendation import recommend
from worldenergydata.production.unified.query import ProductionQuery

_ECONOMICS_LIMITATIONS = (
    "Royalty and OPEX are generic bucket defaults, not Canada fiscal terms.",
    "Host CAPEX uses MM inputs emitted in a USD-labelled metric without conversion; "
    "these outputs are not a qualified USD capital valuation.",
)


def run_canada_reference_chain(
    *,
    adapter,
    field_meta: dict[str, Any],
    field_name: str,
    development_wells: Iterable[DevelopmentWell] = (),
    start: str | None = None,
    end: str | None = None,
    oil_price_usd_bbl: float = 75.0,
) -> dict[str, Any]:
    """Run the #719 one-field Canada C-NLOER chain slice."""
    field_concept = build_canada_field_concept(
        field_meta, development_wells=development_wells
    )
    if str(field_name).strip().casefold() != str(field_concept.name).strip().casefold():
        raise ValueError("field_name must match the field_meta field name")
    dev_system, dev_system_source = resolve_canada_dev_system(
        field_concept.name, field_concept.water_depth_m
    )
    unified = adapter.fetch(
        ProductionQuery(
            regions=["canada"],
            fields=[field_name],
            start=start,
            end=end,
        )
    )
    fdas_production = to_fdas_production(unified)
    ranked_concepts = recommend(field_concept)

    first_oil = _first_oil_date(fdas_production)
    price_deck = {
        str(year_month): oil_price_usd_bbl
        for year_month in fdas_production.get("YEAR_MONTH", pd.Series(dtype="object"))
    }

    cashflows = CashflowEngine(
        AssumptionsManager(), dev_system=dev_system
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
        "dev_system": dev_system,
        "dev_system_source": dev_system_source,
        "economics_limitations": _ECONOMICS_LIMITATIONS,
        "pre_tax_metrics": _pre_tax_metrics(cashflows, dev_system, dev_system_source),
    }


def _first_oil_date(fdas_production: pd.DataFrame) -> datetime:
    if fdas_production.empty:
        return datetime(1970, 1, 1)
    first_period = str(fdas_production["YEAR_MONTH"].min())
    return datetime.strptime(first_period, "%Y-%m")


def _pre_tax_metrics(
    cashflows, dev_system: str, dev_system_source: str
) -> dict[str, Any]:
    return {
        "months": len(cashflows),
        "gross_revenue_usd": float(sum(cf.oil_revenue_usd for cf in cashflows)),
        "royalty_usd": float(sum(cf.royalty_usd for cf in cashflows)),
        "host_capex_usd": float(sum(cf.host_capex_usd for cf in cashflows)),
        "net_cashflow_usd": float(sum(cf.net_cashflow_usd for cf in cashflows)),
        # Record the override, depth classification or missing-depth default.
        "dev_system_source": dev_system_source,
        "economics_limitations": _ECONOMICS_LIMITATIONS,
    }
