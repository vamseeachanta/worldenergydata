"""Tests for lower_tertiary.portfolio_economics (#375).

Verifies that:
- A single field analysis produces all expected fields
- A portfolio run covers all 10 LT-2026 fields
- Sensitivity table has the requested oil-price points
- Citations panel has the documented minimum entries per field
- CSV/HTML rendering completes without error
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tests.test_markers import unit  # noqa: E402
from worldenergydata.lower_tertiary.portfolio import LT_FIELDS_2026  # noqa: E402
from worldenergydata.lower_tertiary.portfolio_economics import (  # noqa: E402
    DEFAULT_OIL_PRICE_SENSITIVITY,
    FieldEconomicsResult,
    PortfolioEconomicsRun,
    analyze_field,
    portfolio_to_csv,
    portfolio_to_html,
    run_portfolio,
)

EXPECTED_CITATION_MIN = 8


@unit
class TestAnalyzeField:
    """Per-field analysis populates every required output field."""

    @pytest.fixture(scope="class")
    def anchor_result(self) -> FieldEconomicsResult:
        return analyze_field("anchor")

    def test_anchor_returns_field_economics_result(self, anchor_result):
        assert isinstance(anchor_result, FieldEconomicsResult)
        assert anchor_result.field_id == "anchor"
        assert anchor_result.display_name == "Anchor"
        assert anchor_result.status == "producing"
        assert anchor_result.operator == "Chevron"
        assert anchor_result.capex_mm_usd > 0
        assert anchor_result.plateau_mbopd > 0

    def test_anchor_metrics_finite(self, anchor_result):
        # NPV, MIRR, payback should be finite (IRR may be NaN if no sign change).
        assert anchor_result.npv_mm_usd == anchor_result.npv_mm_usd  # not NaN
        assert anchor_result.mirr_annual == anchor_result.mirr_annual

    def test_anchor_sensitivity_has_default_prices(self, anchor_result):
        prices = sorted(anchor_result.sensitivity["oil_price_usd_per_bbl"].tolist())
        assert prices == sorted(DEFAULT_OIL_PRICE_SENSITIVITY)

    def test_anchor_sensitivity_monotonic_in_oil_price(self, anchor_result):
        # NPV should be non-decreasing as oil price increases (no royalty/tax weirdness in v1).
        sorted_df = anchor_result.sensitivity.sort_values("oil_price_usd_per_bbl")
        npvs = sorted_df["npv_mm_usd"].tolist()
        for a, b in zip(npvs, npvs[1:]):
            assert b >= a, f"NPV not monotonic vs oil price: {npvs}"

    def test_anchor_citations_has_minimum_entries(self, anchor_result):
        assert isinstance(anchor_result.citations, pd.DataFrame)
        assert len(anchor_result.citations) >= EXPECTED_CITATION_MIN
        for col in ("input", "publisher", "code_id", "revision"):
            assert col in anchor_result.citations.columns

    def test_anchor_cashflow_basis_documented(self, anchor_result):
        assert anchor_result.cashflow_basis == "documented_decline_curve_v1"


@unit
class TestRunPortfolio:
    """Portfolio run covers every roster field."""

    @pytest.fixture(scope="class")
    def run(self) -> PortfolioEconomicsRun:
        return run_portfolio()

    def test_results_count_equals_roster(self, run):
        assert len(run.results) == len(LT_FIELDS_2026)

    def test_every_roster_field_present(self, run):
        ids = {r.field_id for r in run.results}
        assert ids == set(LT_FIELDS_2026)

    def test_run_metadata_captured(self, run):
        assert run.discount_rate == 0.10
        assert run.oil_price_usd_per_bbl == 70.0
        assert run.timestamp_utc  # non-empty string

    def test_summary_frame_has_all_expected_columns(self, run):
        df = run.to_summary_frame()
        for col in (
            "field_id",
            "display_name",
            "status",
            "operator",
            "capex_mm_usd",
            "npv_mm_usd",
            "irr_annual",
            "mirr_annual",
            "payback_years",
            "breakeven_oil_usd_per_bbl",
            "cashflow_basis",
        ):
            assert col in df.columns, f"summary frame missing column: {col}"
        for price in DEFAULT_OIL_PRICE_SENSITIVITY:
            col = f"npv_mm_usd_at_${int(price)}"
            assert col in df.columns


@unit
class TestRendering:
    """CSV + HTML rendering completes against fixtures."""

    def test_to_csv_writes_file(self, tmp_path):
        run = run_portfolio()
        out = tmp_path / "portfolio.csv"
        portfolio_to_csv(run, out)
        assert out.is_file()
        df = pd.read_csv(out)
        assert len(df) == len(LT_FIELDS_2026)

    def test_to_html_writes_file_and_includes_each_field(self, tmp_path):
        run = run_portfolio()
        out = tmp_path / "portfolio.html"
        portfolio_to_html(run, out)
        assert out.is_file()
        contents = out.read_text(encoding="utf-8")
        for fid in LT_FIELDS_2026:
            # Each field id should appear at least once (in its section header).
            assert fid in contents, f"HTML missing field id: {fid}"
        # And the citations panel should mention the BSEE royalty.
        assert "30 CFR" in contents
