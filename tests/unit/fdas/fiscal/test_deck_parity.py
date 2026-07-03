"""Suite 5 — us_gom deck parity (do-not-ship-without gate, #714).

The `us_gom` deck holds the SAME per-dev-system royalty rates as the legacy
``AssumptionsManager`` path. Therefore, for every development system, a
deck-driven ``CashflowEngine`` must produce a cashflow stream that is
byte-identical to the deckless (legacy) engine — the deck overrides royalty
ONLY, every other assumption still flows through the untouched
``AssumptionsManager``. We assert on the FULL component vectors (not just NPV
totals) so a divergence in any line item is caught.
"""

from datetime import datetime

import pandas as pd

import numpy as np

from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.core.financial import calculate_npv
from worldenergydata.fdas.fiscal import DEV_SYSTEMS, get_fiscal_terms

_COMPONENT_FIELDS = (
    "oil_production_bbl",
    "oil_revenue_usd",
    "royalty_usd",
    "variable_opex_usd",
    "fixed_opex_usd",
    "drilling_capex_usd",
    "facilities_capex_usd",
    "host_capex_usd",
    "net_cashflow_usd",
)


def _fixture():
    prod = pd.DataFrame(
        {
            "YEAR_MONTH": ["2025-01", "2025-02", "2025-03", "2025-04"],
            "MONTHLY_OIL_BBL": [120000.0, 110000.0, 95000.0, 80000.0],
        }
    )
    wti = {"2025-01": 75.0, "2025-02": 78.5, "2025-03": 72.0, "2025-04": 80.0}
    timeline = {"drilling_monthly": {"2024-10": 30.0, "2024-11": 28.0}}
    first_oil = datetime(2025, 1, 1)
    return prod, timeline, wti, first_oil


def test_deckless_vs_us_gom_identical_component_vectors():
    us_gom = get_fiscal_terms("us_gom")
    prod, timeline, wti, first_oil = _fixture()

    for ds in DEV_SYSTEMS:
        legacy = CashflowEngine(AssumptionsManager(), dev_system=ds)
        decked = CashflowEngine(
            AssumptionsManager(), dev_system=ds, fiscal_terms=us_gom
        )

        cf_legacy = legacy.generate_monthly_cashflow(
            prod.copy(), timeline, wti, first_oil
        )
        cf_decked = decked.generate_monthly_cashflow(
            prod.copy(), timeline, wti, first_oil
        )

        assert len(cf_legacy) == len(cf_decked) > 0, ds
        for a, b in zip(cf_legacy, cf_decked):
            assert a.year_month == b.year_month, ds
            for field in _COMPONENT_FIELDS:
                assert getattr(a, field) == getattr(b, field), (ds, field, a.year_month)


def test_deckless_vs_us_gom_identical_npv():
    us_gom = get_fiscal_terms("us_gom")
    prod, timeline, wti, first_oil = _fixture()

    for ds in DEV_SYSTEMS:
        legacy = CashflowEngine(AssumptionsManager(), dev_system=ds)
        decked = CashflowEngine(
            AssumptionsManager(), dev_system=ds, fiscal_terms=us_gom
        )
        v_legacy = [
            c.net_cashflow_usd
            for c in legacy.generate_monthly_cashflow(prod.copy(), timeline, wti, first_oil)
        ]
        v_decked = [
            c.net_cashflow_usd
            for c in decked.generate_monthly_cashflow(prod.copy(), timeline, wti, first_oil)
        ]
        assert calculate_npv(np.array(v_legacy), 0.10) == calculate_npv(
            np.array(v_decked), 0.10
        ), ds


def test_calculate_royalty_parity_direct():
    """Direct royalty parity: deck vs legacy across all dev systems."""
    us_gom = get_fiscal_terms("us_gom")
    revenue = {"2025-01": 9_000_000.0, "2025-02": 7_050_000.0}
    for ds in DEV_SYSTEMS:
        legacy = CashflowEngine(AssumptionsManager(), dev_system=ds)
        decked = CashflowEngine(
            AssumptionsManager(), dev_system=ds, fiscal_terms=us_gom
        )
        assert legacy.calculate_royalty(revenue) == decked.calculate_royalty(revenue), ds


def test_explicit_rate_arg_overrides_deck():
    """An explicit royalty_rate arg wins over both deck and assumptions."""
    us_gom = get_fiscal_terms("us_gom")
    revenue = {"2025-01": 1_000_000.0}
    decked = CashflowEngine(AssumptionsManager(), dev_system="subsea15", fiscal_terms=us_gom)
    out = decked.calculate_royalty(revenue, royalty_rate=0.0)
    assert out["2025-01"] == 0.0
