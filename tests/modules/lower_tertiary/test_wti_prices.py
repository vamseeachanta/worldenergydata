"""
ABOUTME: Tests for WTI price loading and extension beyond V30 baseline
ABOUTME: Verifies load, extend, fallback, and source tracking for WRK-010
"""

from __future__ import annotations

import pandas as pd
import pytest

try:
    from worldenergydata.analysis.lower_tertiary.wti_prices import (
        V30_LAST_PRICE,
        get_wti_source_summary,
        load_extended_wti_prices,
        load_v30_wti_prices,
    )

    WTI_AVAILABLE = True
except ImportError:
    WTI_AVAILABLE = False

skip_no_wti = pytest.mark.skipif(not WTI_AVAILABLE, reason="wti_prices not importable")


@pytest.fixture(scope="module")
def v30_prices():
    """Load V30 WTI prices once per test module."""
    return load_v30_wti_prices()


# ---------------------------------------------------------------------------
# V30 baseline tests
# ---------------------------------------------------------------------------


@skip_no_wti
def test_v30_wti_loads_expected_range(v30_prices):
    df = v30_prices
    assert list(df.columns) == ["Month", "WTI_USD"]
    assert df["Month"].min() == pd.Timestamp("1986-01-01")
    assert df["Month"].max() == pd.Timestamp("2025-07-01")
    assert len(df) > 470


@skip_no_wti
def test_v30_last_month_price(v30_prices):
    jul_2025 = v30_prices[v30_prices["Month"] == pd.Timestamp("2025-07-01")]
    assert len(jul_2025) == 1
    assert jul_2025["WTI_USD"].iloc[0] == pytest.approx(68.39, abs=0.01)


# ---------------------------------------------------------------------------
# Extended price tests
# ---------------------------------------------------------------------------


@skip_no_wti
def test_extended_wti_fills_gap():
    df = load_extended_wti_prices(through_date="2025-10-01")
    assert "source" in df.columns
    assert df["Month"].max() >= pd.Timestamp("2025-10-01")

    gap_months = [pd.Timestamp(f"2025-{m:02d}-01") for m in (8, 9, 10)]
    for month in gap_months:
        rows = df[df["Month"] == month]
        assert len(rows) == 1, f"Missing row for {month}"
        assert rows["source"].iloc[0] != "v30_xlsx"


@skip_no_wti
def test_extended_within_v30_range_no_extension():
    df = load_extended_wti_prices(through_date="2025-06-01")
    assert (df["source"] == "v30_xlsx").all()


# ---------------------------------------------------------------------------
# Flat-forward fallback
# ---------------------------------------------------------------------------


@skip_no_wti
def test_flat_forward_fallback(monkeypatch):
    import worldenergydata.analysis.lower_tertiary.wti_prices as wti_mod

    monkeypatch.setattr(wti_mod, "_HAS_REQUESTS", False)
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    df = load_extended_wti_prices(through_date="2025-10-01")
    gap_months = [pd.Timestamp(f"2025-{m:02d}-01") for m in (8, 9, 10)]
    for month in gap_months:
        rows = df[df["Month"] == month]
        assert len(rows) == 1
        assert rows["source"].iloc[0] == "flat_forward"
        assert rows["WTI_USD"].iloc[0] == pytest.approx(V30_LAST_PRICE)


# ---------------------------------------------------------------------------
# Source tracking & overlap
# ---------------------------------------------------------------------------


@skip_no_wti
def test_source_tracking():
    df = load_extended_wti_prices(through_date="2025-10-01")
    summary = get_wti_source_summary(df)

    for key in ("v30_xlsx", "eia_github", "fred_api", "flat_forward"):
        assert key in summary

    assert summary["v30_xlsx"] > 470
    assert sum(summary.values()) == len(df)


@skip_no_wti
def test_v30_overlap_preserved():
    df = load_extended_wti_prices(through_date="2025-10-01")
    jul_rows = df[df["Month"] == pd.Timestamp("2025-07-01")]
    assert len(jul_rows) == 1
    assert jul_rows["source"].iloc[0] == "v30_xlsx"
    assert jul_rows["WTI_USD"].iloc[0] == pytest.approx(68.39, abs=0.01)
