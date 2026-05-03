"""Tests for lower_tertiary.portfolio_analytics (#376).

Verifies each cross-field analytics section against the approved plan:
- 3a technology generation aggregates by dev system
- 3b operator concentration produces working-interest-weighted shares
- 3c HSE per field surfaces minimum-viable flag pending #366
- 3d cost benchmark surfaces no_data flag pending #343
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
from worldenergydata.lower_tertiary.portfolio_analytics import (  # noqa: E402
    BENCHMARK_STATUS_NO_DATA,
    HSE_DATA_COMPLETENESS_MINIMUM,
    PortfolioAnalyticsRun,
    analyze_cost_benchmark,
    analyze_hse_per_field,
    analyze_operator_concentration,
    analyze_technology_generation,
    portfolio_analytics_to_csv,
    portfolio_analytics_to_html,
    run_portfolio_analytics,
)
from worldenergydata.lower_tertiary.portfolio_economics import (  # noqa: E402
    run_portfolio,
)


@pytest.fixture(scope="module")
def economics_run():
    """Shared economics run — slow, share across the module."""
    return run_portfolio()


@unit
class TestTechnologyGeneration:
    """3a — aggregates by dev system from yaml + economics."""

    def test_returns_dataframe_with_expected_columns(self, economics_run):
        df = analyze_technology_generation(LT_FIELDS_2026, economics_run=economics_run)
        for col in (
            "dev_system",
            "field_count",
            "fields",
            "total_capex_mm_usd",
            "mean_capex_per_mmbbl_usd",
            "total_recoverable_mmbbl_proxy",
            "total_npv_mm_usd",
            "mean_breakeven_usd_per_bbl",
            "caveats",
        ):
            assert col in df.columns

    def test_field_count_sums_to_roster(self, economics_run):
        df = analyze_technology_generation(LT_FIELDS_2026, economics_run=economics_run)
        assert int(df["field_count"].sum()) == len(LT_FIELDS_2026)

    def test_subsea_20k_group_includes_anchor(self, economics_run):
        df = analyze_technology_generation(LT_FIELDS_2026, economics_run=economics_run)
        sub20k = df[df["dev_system"] == "Subsea 20K"]
        assert len(sub20k) == 1
        assert "anchor" in sub20k.iloc[0]["fields"]

    def test_caveat_present_per_row(self, economics_run):
        df = analyze_technology_generation(LT_FIELDS_2026, economics_run=economics_run)
        assert df["caveats"].notna().all()
        assert df["caveats"].str.contains("OGOR-grounded").all()


@unit
class TestOperatorConcentration:
    """3b — working-interest-weighted aggregation."""

    def test_chevron_appears_via_anchor_partners(self):
        df = analyze_operator_concentration(LT_FIELDS_2026)
        chevron = df[df["company"] == "Chevron"]
        assert not chevron.empty
        # Chevron operates Anchor (62.5%), Big Foot (60%) — at minimum should
        # cover ≥2 fields' WI participation.
        assert int(chevron.iloc[0]["field_count"]) >= 2

    def test_share_capex_pct_sums_to_100(self):
        df = analyze_operator_concentration(LT_FIELDS_2026)
        # Allow small float tolerance.
        assert abs(df["share_capex_pct"].sum() - 100.0) < 0.5

    def test_kaskida_pre_fid_yaml_resolves_via_operator_only(self):
        """Yamls without partners block must still surface their operator."""
        df = analyze_operator_concentration(["kaskida"])
        assert not df.empty
        # BP operates Kaskida.
        bp_row = df[df["company"] == "BP"]
        assert len(bp_row) == 1


@unit
class TestHseMinimumViable:
    """3c — emits one row per field with minimum-viable flag."""

    def test_one_row_per_field(self):
        df = analyze_hse_per_field(LT_FIELDS_2026)
        assert len(df) == len(LT_FIELDS_2026)
        assert set(df["field_id"]) == set(LT_FIELDS_2026)

    def test_every_row_flagged_minimum_viable(self):
        df = analyze_hse_per_field(LT_FIELDS_2026)
        assert (df["data_completeness"] == HSE_DATA_COMPLETENESS_MINIMUM).all()


@unit
class TestCostBenchmark:
    """3d — every roster field gets a row, all flagged no_data pending #343."""

    def test_one_row_per_field(self, economics_run):
        df = analyze_cost_benchmark(LT_FIELDS_2026, economics_run=economics_run)
        assert len(df) == len(LT_FIELDS_2026)
        assert set(df["field_id"]) == set(LT_FIELDS_2026)

    def test_every_row_flagged_no_data(self, economics_run):
        df = analyze_cost_benchmark(LT_FIELDS_2026, economics_run=economics_run)
        assert (df["benchmark_status"] == BENCHMARK_STATUS_NO_DATA).all()

    def test_modelled_capex_matches_yaml(self, economics_run):
        """Anchor yaml has total_mm_usd: 5600 — verify it surfaces."""
        df = analyze_cost_benchmark(LT_FIELDS_2026, economics_run=economics_run)
        anchor_row = df[df["field_id"] == "anchor"].iloc[0]
        assert anchor_row["modelled_capex_mm_usd"] == pytest.approx(5600.0)


@unit
class TestRunPortfolioAnalytics:
    """Orchestrator bundles all four sections."""

    @pytest.fixture(scope="class")
    def run(self, economics_run):
        return run_portfolio_analytics(economics_run=economics_run)

    def test_returns_run_dataclass(self, run):
        assert isinstance(run, PortfolioAnalyticsRun)
        assert run.timestamp_utc

    def test_all_four_sections_populated(self, run):
        for name in ("technology", "operator", "hse", "cost_benchmark"):
            assert isinstance(run.section(name), pd.DataFrame)
            assert not run.section(name).empty

    def test_section_unknown_raises(self, run):
        with pytest.raises(KeyError):
            run.section("nonexistent")


@unit
class TestRendering:
    """CSV + HTML renderers complete and surface caveats."""

    def test_csv_writes_four_files(self, tmp_path, economics_run):
        run = run_portfolio_analytics(economics_run=economics_run)
        paths = portfolio_analytics_to_csv(run, tmp_path)
        assert set(paths.keys()) == {"technology", "operator", "hse", "cost_benchmark"}
        for path in paths.values():
            assert path.is_file()

    def test_html_includes_caveats(self, tmp_path, economics_run):
        run = run_portfolio_analytics(economics_run=economics_run)
        out = tmp_path / "analytics.html"
        portfolio_analytics_to_html(run, out)
        contents = out.read_text(encoding="utf-8")
        assert "#366" in contents  # HSE caveat
        assert "#343" in contents  # cost benchmark caveat
        assert "Lower Tertiary Portfolio Analytics" in contents
