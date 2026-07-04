"""Suites C/D/F — country conformance + parity guard + honesty guard (#715).

Uses committed SYNTHETIC per-region STANDARD_COLUMNS fixtures (not live
adapter.fetch(), which needs repo data absent in CI per CLAUDE.md) so the suite
validates the *transform contract* deterministically. A live-fetch lane is a
documented follow-on (skip-with-reason, never hollow-green).
"""

import logging

import pandas as pd
import pytest

from worldenergydata.fdas.adapters.contract import (
    FDAS_PRODUCTION_COLUMNS,
    to_fdas_production,
)
from worldenergydata.fdas.adapters.field_concept_normalizer import (
    FieldMapEntry,
    FieldMetaMapping,
    number_from,
    year_from,
)
from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager

# One representative unified-schema row set per region key (mirrors what each
# AbstractProductionAdapter.fetch() emits: STANDARD_COLUMNS).
_REGION_FIXTURES = {
    "ncs": ("Troll", 2024, 100000.0, 40000.0),  # Norway
    "ukcs": ("Forties", 2024, 80000.0, 30000.0),  # UK
    "gom": ("Thunder Horse", 2024, 120000.0, 60000.0),
    "spain": ("Casablanca", 2024, 5000.0, 1000.0),
    "brazil": ("Tupi", 2024, 200000.0, 90000.0),
}


def _unified_frame(region, field_name, year, oil, gas):
    return pd.DataFrame(
        [
            (region, field_name, year, m, oil, gas, oil * 0.02, oil * 0.001, region)
            for m in (1, 2, 3)
        ],
        columns=[
            "region",
            "field_name",
            "year",
            "month",
            "oil_bbl",
            "gas_mcf",
            "water_bbl",
            "condensate_bbl",
            "source",
        ],
    )


@pytest.mark.parametrize("region", sorted(_REGION_FIXTURES))
def test_country_frame_normalizes_to_valid_fdas_production(region):
    field_name, year, oil, gas = _REGION_FIXTURES[region]
    out = to_fdas_production(_unified_frame(region, field_name, year, oil, gas))
    assert list(out.columns) == list(FDAS_PRODUCTION_COLUMNS)
    assert len(out) == 3
    assert (out["MONTHLY_OIL_BBL"] >= 0).all()
    assert (out["MONTHLY_GAS_MCF"] >= 0).all()
    # YEAR_MONTH parseable + DEV_NAME carried
    assert all(pd.Period(v, freq="M") for v in out["YEAR_MONTH"])
    assert (out["DEV_NAME"] == field_name).all()


def test_representative_metadata_normalizes_to_valid_field_concept():
    mapping = FieldMetaMapping(
        {
            "name": FieldMapEntry("field"),
            "region": FieldMapEntry("area"),
            "water_depth_m": FieldMapEntry("wd", number_from),
            "year_first_oil": FieldMapEntry("first_oil", year_from),
        }
    )
    from worldenergydata.fdas.adapters.field_concept_normalizer import to_field_concept

    fc = to_field_concept(
        {"field": "Troll", "area": "North Sea", "wd": "340", "first_oil": "1996"},
        mapping,
    )
    assert fc.name == "Troll"
    assert fc.water_depth_m == 340.0
    assert fc.year_first_oil == 1996


def test_parity_guard_canonical_bbl_columns():
    """Suite D guard: the FDAS production contract uses MONTHLY_OIL_BBL — the
    column the cashflow engine reads — NOT the legacy bsee_adapter _VOLUME."""
    assert "MONTHLY_OIL_BBL" in FDAS_PRODUCTION_COLUMNS
    assert "MONTHLY_GAS_MCF" in FDAS_PRODUCTION_COLUMNS
    assert not any("VOLUME" in c for c in FDAS_PRODUCTION_COLUMNS)


def test_honesty_guard_warns_on_empty_drilling_timeline(caplog):
    """Suite F (review B1): an empty drilling timeline must emit a WARNING so the
    silent-zero-drilling-CAPEX case is visible; the number is still 0."""
    prod = pd.DataFrame(
        {"YEAR_MONTH": ["2025-01", "2025-02"], "MONTHLY_OIL_BBL": [100000.0, 90000.0]}
    )
    eng = CashflowEngine(AssumptionsManager(), dev_system="subsea15")
    from datetime import datetime

    with caplog.at_level(logging.WARNING):
        cashflows = eng.generate_monthly_cashflow(
            prod,
            {"drilling_monthly": {}},
            {"2025-01": 75.0, "2025-02": 76.0},
            datetime(2025, 1, 1),
        )
    assert cashflows
    assert all(cf.drilling_capex_usd == 0.0 for cf in cashflows)  # still 0
    assert any("drilling CAPEX is 0" in r.message for r in caplog.records)  # but loud
