"""Suite 6 — non-US decks + declarative-fields fences (#714).

Norway (`none`) and UK (flat 0.0) royalty regimes run through the engine; and
the declarative metadata fields (price_marker, currency, discount_rate) are
provably NOT consumed by the v1 royalty seam — editing them changes nothing.
"""

import dataclasses

from datetime import datetime

import pandas as pd

from worldenergydata.fdas.analysis.cashflow import CashflowEngine
from worldenergydata.fdas.core.config import AssumptionsManager
from worldenergydata.fdas.fiscal import DEV_SYSTEMS, get_fiscal_terms


def _revenue():
    return {"2025-01": 5_000_000.0, "2025-02": 4_200_000.0}


def test_norway_none_yields_zero_royalty():
    norway = get_fiscal_terms("norway")
    for ds in DEV_SYSTEMS:
        eng = CashflowEngine(AssumptionsManager(), dev_system=ds, fiscal_terms=norway)
        out = eng.calculate_royalty(_revenue())
        assert all(v == 0.0 for v in out.values()), ds


def test_uk_flat_zero_yields_zero_royalty():
    uk = get_fiscal_terms("uk")
    for ds in DEV_SYSTEMS:
        eng = CashflowEngine(AssumptionsManager(), dev_system=ds, fiscal_terms=uk)
        out = eng.calculate_royalty(_revenue())
        assert all(v == 0.0 for v in out.values()), ds


def test_norway_full_cashflow_runs():
    """A `none`-royalty deck must run the full monthly cashflow path."""
    norway = get_fiscal_terms("norway")
    prod = pd.DataFrame(
        {"YEAR_MONTH": ["2025-01", "2025-02"], "MONTHLY_OIL_BBL": [100000.0, 90000.0]}
    )
    eng = CashflowEngine(AssumptionsManager(), dev_system="subsea15", fiscal_terms=norway)
    cashflows = eng.generate_monthly_cashflow(
        prod, {"drilling_monthly": {}}, {"2025-01": 75.0, "2025-02": 76.0}, datetime(2025, 1, 1)
    )
    assert cashflows
    # every royalty line is zero under the `none` regime
    assert all(cf.royalty_usd == 0.0 for cf in cashflows)


def test_declarative_fields_are_not_consumed():
    """Editing declarative metadata (price_marker/currency/discount_rate) must
    NOT change the royalty the engine computes — proving they are unconsumed in
    v1 (the revenue/NPV seam is deferred to #716)."""
    us_gom = get_fiscal_terms("us_gom")
    mutated = dataclasses.replace(
        us_gom, price_marker="brent", currency="EUR", discount_rate=0.99
    )
    eng_a = CashflowEngine(AssumptionsManager(), dev_system="subsea15", fiscal_terms=us_gom)
    eng_b = CashflowEngine(AssumptionsManager(), dev_system="subsea15", fiscal_terms=mutated)
    assert eng_a.calculate_royalty(_revenue()) == eng_b.calculate_royalty(_revenue())
