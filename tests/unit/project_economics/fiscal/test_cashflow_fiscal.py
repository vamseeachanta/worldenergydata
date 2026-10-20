"""Suite 6 — non-US decks + declarative-fields fences (#714).

Norway (`none`) and UK (flat 0.0) royalty regimes run through the engine; and
the declarative metadata fields (price_marker, currency, discount_rate) are
provably NOT consumed by the v1 royalty seam — editing them changes nothing.
"""

import dataclasses
from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.project_economics.analysis.cashflow import CashflowEngine
from worldenergydata.project_economics.core.config import AssumptionsManager
from worldenergydata.project_economics.fiscal import DEV_SYSTEMS, get_fiscal_terms


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
    eng = CashflowEngine(
        AssumptionsManager(), dev_system="subsea15", fiscal_terms=norway
    )
    cashflows = eng.generate_monthly_cashflow(
        prod,
        {"drilling_monthly": {}},
        {"2025-01": 75.0, "2025-02": 76.0},
        datetime(2025, 1, 1),
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
    eng_a = CashflowEngine(
        AssumptionsManager(), dev_system="subsea15", fiscal_terms=us_gom
    )
    eng_b = CashflowEngine(
        AssumptionsManager(), dev_system="subsea15", fiscal_terms=mutated
    )
    assert eng_a.calculate_royalty(_revenue()) == eng_b.calculate_royalty(_revenue())


def _synthetic_terms():
    from worldenergydata.project_economics.fiscal import validate_deck

    return validate_deck(
        {
            "schema_version": 1,
            "country": "synthetic",
            "source_url": "https://example.org/synthetic",
            "source_ref": "Synthetic seam fixture",
            "revision": "1",
            "effective_date": "2026-01-01",
            "royalty": {
                "model": "sliding_scale",
                "bands": [
                    {"max_rate_bpd": 5000, "rate": 0.05},
                    {"max_rate_bpd": 15000, "rate": 0.075},
                    {"max_rate_bpd": None, "rate": 0.15},
                ],
            },
        }
    )


@pytest.mark.parametrize(
    "rate, expected",
    [
        (4000, 50000),
        (5000, 50000),
        (5001, 75000),
        (60000, 150000),
    ],
)
def test_synthetic_band_selection(rate, expected):
    """Synthetic revenue 1,000,000 times 0.05/0.075/0.15 is 50,000/75,000/150,000."""
    eng = CashflowEngine(AssumptionsManager(), fiscal_terms=_synthetic_terms())
    result = eng.calculate_royalty(
        {"2025-01": 1_000_000},
        production_rate_bpd_monthly={"2025-01": rate},
    )
    assert result["2025-01"] == expected
    assert result.production_rate_basis == "calendar-day average per month"


@pytest.mark.parametrize(
    "rates",
    [
        None,
        {},
        {"2025-02": 1},
        {"2025-01": None},
        {"2025-01": float("nan")},
        {"2025-01": -1},
    ],
)
def test_sliding_scale_missing_or_invalid_rate_raises(rates):
    eng = CashflowEngine(AssumptionsManager(), fiscal_terms=_synthetic_terms())
    with pytest.raises(ValueError, match="production"):
        eng.calculate_royalty({"2025-01": 1_000_000}, production_rate_bpd_monthly=rates)


@pytest.mark.parametrize(
    "month, volume, expected",
    [
        ("2025-01", 124000, 4000),
        ("2025-04", 120000, 4000),
        ("2025-02", 112000, 4000),
        ("2024-02", 116000, 4000),
    ],
)
def test_calendar_month_daily_rate_and_basis(month, volume, expected):
    """124000/31, 120000/30, 112000/28 and leap-year 116000/29 all give 4000 bpd."""
    eng = CashflowEngine(AssumptionsManager(), fiscal_terms=_synthetic_terms())
    prod = pd.DataFrame({"YEAR_MONTH": [month], "MONTHLY_OIL_BBL": [volume]})
    rows = eng.generate_monthly_cashflow(
        prod,
        {"drilling_monthly": {}},
        {month: 10},
        datetime.fromisoformat(month + "-01"),
    )
    result = next(row for row in rows if row.year_month == month)
    assert result.production_rate_bpd == expected
    assert result.production_rate_basis == "calendar-day average per month"
    assert result.royalty_usd == volume * 10 * 0.05


@pytest.mark.parametrize("volume", [None, float("nan")])
def test_sliding_scale_missing_monthly_volume_raises(volume):
    eng = CashflowEngine(AssumptionsManager(), fiscal_terms=_synthetic_terms())
    prod = pd.DataFrame({"YEAR_MONTH": ["2025-01"], "MONTHLY_OIL_BBL": [volume]})
    with pytest.raises(ValueError, match="volume"):
        eng.generate_monthly_cashflow(
            prod, {"drilling_monthly": {}}, {"2025-01": 10}, datetime(2025, 1, 1)
        )
