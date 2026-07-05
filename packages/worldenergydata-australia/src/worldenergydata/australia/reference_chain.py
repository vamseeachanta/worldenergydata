"""Australia field-development reference-chain runner (#721).

SCREENING-ONLY slice: Australia has no open per-field offshore production source,
so this chain proves the F2 wiring (metadata -> FieldConcept -> ``recommend()``)
WITHOUT real volumes. ``AustraliaAdapter.fetch`` returns an empty STANDARD_COLUMNS
frame; the cashflow step therefore yields zero months. The return dict labels this
unambiguously (``production_available=False``) so the zeroed economics are never
mistaken for a screening result. It deliberately does NOT fabricate a volume
series (AU offshore production history is a paid-source boundary).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from worldenergydata.australia.field_concept import build_australia_field_concept
from worldenergydata.fdas.adapters.contract import to_fdas_production
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    dev_system_from_water_depth_m,
)
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.field_development.recommendation import recommend
from worldenergydata.production.unified.query import ProductionQuery


def run_australia_reference_chain(
    *,
    adapter,
    field_meta: Dict[str, Any],
    field_name: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    oil_price_usd_bbl: float = 75.0,
) -> Dict[str, Any]:
    """Run the #721 one-field Australia screening-only chain slice."""
    unified = adapter.fetch(
        ProductionQuery(
            regions=["australia"],
            fields=[field_name],
            start=start,
            end=end,
        )
    )
    fdas_production = to_fdas_production(unified)
    field_concept = build_australia_field_concept(field_meta)
    ranked_concepts = recommend(field_concept)

    # No production -> derive dev_system from depth, run a zero-month cashflow.
    dev_system = dev_system_from_water_depth_m(field_concept.water_depth_m)
    if dev_system == "unknown":
        dev_system = "subsea15"
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
        datetime(1970, 1, 1),
    )

    return {
        "field_name": field_name,
        "unified_production": unified,
        "fdas_production": fdas_production,
        "field_concept": field_concept,
        "ranked_concepts": ranked_concepts,
        "dev_system": dev_system,
        "production_available": False,
        "concept_screening_label": "fieldconcept_screening_only_no_production",
        "economics_label": "no_production_source_placeholder",
        "pre_tax_metrics": _pre_tax_metrics(cashflows),
    }


def _pre_tax_metrics(cashflows) -> Dict[str, float]:
    return {
        "months": len(cashflows),
        "gross_revenue_usd": float(sum(cf.oil_revenue_usd for cf in cashflows)),
        "net_cashflow_usd": float(sum(cf.net_cashflow_usd for cf in cashflows)),
    }
