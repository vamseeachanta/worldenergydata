"""Tests for ComprehensiveActivityAnalyzer (WRK-116 Phase 3).

TDD test suite verifying cross-cutting analysis of enriched WAR data
across 7 analysis modules: drilling efficiency, well depth, geological
era, cross-activity, well lifecycle, operator portfolio, and duration
benchmarking.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.comprehensive_analyzer import (
    ComprehensiveActivityAnalyzer,
)

_EXPECTED_KEYS = frozenset({
    "drilling_efficiency",
    "well_depth",
    "geological_era",
    "cross_activity",
    "well_lifecycle",
    "operator_portfolio",
    "duration_benchmarking",
})


# -- 1. Top-level contract ---------------------------------------------------


class TestAnalyzeContract:
    """Verify analyze() returns dict with all 7 module keys."""

    def test_analyze_returns_dict_with_seven_keys(
        self, enriched_df: pd.DataFrame
    ) -> None:
        analyzer = ComprehensiveActivityAnalyzer(enriched_df)
        result = analyzer.analyze()
        assert isinstance(result, dict)
        assert set(result.keys()) == _EXPECTED_KEYS


# -- 2. Drilling efficiency ---------------------------------------------------


class TestDrillingEfficiency:
    """Verify drilling efficiency module computations."""

    def test_drilling_efficiency_uses_actual_days(
        self, enriched_df: pd.DataFrame
    ) -> None:
        """DRILLING_DAYS from SPUD->TD, not WAR week count."""
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        eff = result["drilling_efficiency"]
        # W001 has 70 drilling days -- mean should reflect actual borehole data
        assert eff["total_wells_with_duration"] > 0
        assert eff["mean_drilling_days"] > 0.0
        assert isinstance(eff["mean_drilling_days"], float)

    def test_drilling_efficiency_by_rig_type_has_rows(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        by_rt = result["drilling_efficiency"]["by_rig_type"]
        assert isinstance(by_rt, pd.DataFrame)
        assert len(by_rt) > 0
        assert set(by_rt.columns) == {"RIG_TYPE", "mean_days", "median_days", "count"}

    def test_drilling_efficiency_only_drilling_category(
        self, enriched_df: pd.DataFrame
    ) -> None:
        """Intervention and unknown rows excluded from drilling efficiency."""
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        by_rt = result["drilling_efficiency"]["by_rig_type"]
        rig_types = set(by_rt["RIG_TYPE"].tolist())
        # Only drilling rig types should appear
        intervention_types = {"wireline_unit", "coil_tubing_unit", "lift_boat"}
        assert rig_types.isdisjoint(intervention_types)


# -- 3. Well depth ------------------------------------------------------------


class TestWellDepth:
    """Verify well depth module computations."""

    def test_well_depth_mean_and_max(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        wd = result["well_depth"]
        assert wd["mean_total_md"] > 0.0
        assert wd["max_total_md"] > 0.0
        assert isinstance(wd["mean_total_md"], float)
        assert isinstance(wd["max_total_md"], float)

    def test_well_depth_by_area(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        by_area = result["well_depth"]["by_area"]
        assert isinstance(by_area, pd.DataFrame)
        assert set(by_area.columns) == {"AREA_CODE", "mean_md", "max_md", "count"}
        assert len(by_area) > 0


# -- 4. Geological era --------------------------------------------------------


class TestGeologicalEra:
    """Verify geological era module computations."""

    def test_geological_era_distribution(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        era = result["geological_era"]
        assert era["wells_with_era"] > 0
        dist = era["era_distribution"]
        assert isinstance(dist, pd.DataFrame)
        assert "GEOLOGICAL_ERA" in dist.columns
        assert "activity_count" in dist.columns
        assert "unique_wells" in dist.columns
        # Miocene should appear (W001 + W002)
        miocene = dist[dist["GEOLOGICAL_ERA"] == "Miocene"]
        assert len(miocene) == 1
        assert miocene.iloc[0]["unique_wells"] >= 2

    def test_geological_era_by_category(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        by_cat = result["geological_era"]["era_by_category"]
        assert isinstance(by_cat, pd.DataFrame)
        assert set(by_cat.columns) == {"GEOLOGICAL_ERA", "ACTIVITY_CATEGORY", "count"}
        assert len(by_cat) > 0


# -- 5. Cross activity --------------------------------------------------------


class TestCrossActivity:
    """Verify cross-activity ratio computations."""

    def test_cross_activity_ratio(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        ca = result["cross_activity"]
        assert ca["drilling_count"] > 0
        assert ca["intervention_count"] > 0
        expected_ratio = ca["drilling_count"] / ca["intervention_count"]
        assert abs(ca["ratio"] - expected_ratio) < 1e-9

    def test_cross_activity_by_depth_class(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        by_dc = result["cross_activity"]["by_depth_class"]
        assert isinstance(by_dc, pd.DataFrame)
        assert set(by_dc.columns) == {
            "WATER_DEPTH_CLASS", "drilling", "intervention", "ratio",
        }
        assert len(by_dc) > 0


# -- 6. Well lifecycle --------------------------------------------------------


class TestWellLifecycle:
    """Verify well lifecycle module computations."""

    def test_well_lifecycle_status_distribution(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        wl = result["well_lifecycle"]
        dist = wl["status_distribution"]
        assert isinstance(dist, pd.DataFrame)
        assert set(dist.columns) == {"WELL_STATUS", "count", "pct"}
        statuses = set(dist["WELL_STATUS"].tolist())
        # COM, PA, DRL, ST, TA should appear from fixture data
        assert "COM" in statuses
        assert "PA" in statuses

    def test_well_lifecycle_completion_rate(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        wl = result["well_lifecycle"]
        rate = wl["completion_rate"]
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 1.0
        # W001=COM, W002=COM, W007=COM => 3 COM out of 8 with status
        # But multiple WAR rows per well means we count rows or unique wells.
        # The analyzer uses rows with known WELL_STATUS.
        assert rate > 0.0


# -- 7. Operator portfolio ----------------------------------------------------


class TestOperatorPortfolio:
    """Verify operator portfolio module computations."""

    def test_operator_portfolio_top_operators(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        top = result["operator_portfolio"]["top_operators"]
        assert isinstance(top, pd.DataFrame)
        assert set(top.columns) == {
            "BUS_ASC_NAME", "activity_count", "unique_wells", "unique_areas",
        }
        assert len(top) > 0
        # Sorted descending by activity_count
        counts = top["activity_count"].tolist()
        assert counts == sorted(counts, reverse=True)

    def test_operator_portfolio_by_depth_class(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        by_dc = result["operator_portfolio"]["by_depth_class"]
        assert isinstance(by_dc, pd.DataFrame)
        assert set(by_dc.columns) == {"BUS_ASC_NAME", "WATER_DEPTH_CLASS", "count"}
        assert len(by_dc) > 0


# -- 8. Duration benchmarking -------------------------------------------------


class TestDurationBenchmarking:
    """Verify duration benchmarking module computations."""

    def test_duration_benchmarking_quartiles(
        self, enriched_df: pd.DataFrame
    ) -> None:
        result = ComprehensiveActivityAnalyzer(enriched_df).analyze()
        db = result["duration_benchmarking"]
        quartiles = db["quartiles"]
        assert isinstance(quartiles, pd.DataFrame)
        assert set(quartiles.columns) == {"quartile", "min_days", "max_days"}
        assert len(quartiles) == 4
        assert set(quartiles["quartile"].tolist()) == {"Q1", "Q2", "Q3", "Q4"}


# -- 9. Edge cases: empty and missing data ------------------------------------


class TestEdgeCases:
    """Verify graceful handling of empty and partial data."""

    def test_empty_input_returns_empty_results(self) -> None:
        empty = pd.DataFrame(columns=[
            "RIG_NAME", "WAR_START_DT", "WAR_END_DT", "API_WELL_NUMBER",
            "BOTM_LEASE_NUM", "AREA_CODE", "BUS_ASC_NAME", "WATER_DEPTH",
            "RIG_TYPE", "ACTIVITY_CATEGORY", "YEAR",
        ])
        result = ComprehensiveActivityAnalyzer(empty).analyze()
        assert set(result.keys()) == _EXPECTED_KEYS
        assert result["drilling_efficiency"]["total_wells_with_duration"] == 0
        assert result["well_depth"]["mean_total_md"] == 0.0
        assert result["geological_era"]["wells_with_era"] == 0
        assert result["cross_activity"]["drilling_count"] == 0

    def test_missing_borehole_columns_graceful(self) -> None:
        """No BH_TOTAL_MD or DRILLING_DAYS columns -> modules return empty."""
        df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B"],
            "WAR_START_DT": ["1/1/2021", "2/1/2021"],
            "WAR_END_DT": ["1/7/2021", "2/7/2021"],
            "API_WELL_NUMBER": ["X001", "X002"],
            "BOTM_LEASE_NUM": ["L1", "L2"],
            "AREA_CODE": ["GC", "WR"],
            "BUS_ASC_NAME": ["SHELL", "BP"],
            "WATER_DEPTH": [3000.0, 5500.0],
            "RIG_TYPE": ["drillship", "semi_submersible"],
            "ACTIVITY_CATEGORY": ["drilling", "drilling"],
            "YEAR": pd.array([2021, 2021], dtype="Int64"),
            "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep"],
        })
        result = ComprehensiveActivityAnalyzer(df).analyze()
        assert result["drilling_efficiency"]["total_wells_with_duration"] == 0
        assert result["well_depth"]["mean_total_md"] == 0.0
        assert result["duration_benchmarking"]["quartiles"].empty

    def test_missing_era_column_graceful(self) -> None:
        """No GEOLOGICAL_ERA column -> era module returns empty."""
        df = pd.DataFrame({
            "RIG_NAME": ["RIG_A"],
            "WAR_START_DT": ["1/1/2021"],
            "WAR_END_DT": ["1/7/2021"],
            "API_WELL_NUMBER": ["X001"],
            "BOTM_LEASE_NUM": ["L1"],
            "AREA_CODE": ["GC"],
            "BUS_ASC_NAME": ["SHELL"],
            "WATER_DEPTH": [3000.0],
            "RIG_TYPE": ["drillship"],
            "ACTIVITY_CATEGORY": ["drilling"],
            "YEAR": pd.array([2021], dtype="Int64"),
            "WATER_DEPTH_CLASS": ["Deep"],
            "DRILLING_DAYS": [45.0],
            "BH_TOTAL_MD": [18000.0],
            "WELL_STATUS": ["COM"],
        })
        result = ComprehensiveActivityAnalyzer(df).analyze()
        assert result["geological_era"]["wells_with_era"] == 0
        assert result["geological_era"]["era_distribution"].empty

    def test_all_drilling_no_intervention(self) -> None:
        """Zero intervention rows -> ratio = 0.0 (no division by zero)."""
        df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B"],
            "WAR_START_DT": ["1/1/2021", "2/1/2021"],
            "WAR_END_DT": ["1/7/2021", "2/7/2021"],
            "API_WELL_NUMBER": ["X001", "X002"],
            "BOTM_LEASE_NUM": ["L1", "L2"],
            "AREA_CODE": ["GC", "WR"],
            "BUS_ASC_NAME": ["SHELL", "BP"],
            "WATER_DEPTH": [3000.0, 5500.0],
            "RIG_TYPE": ["drillship", "semi_submersible"],
            "ACTIVITY_CATEGORY": ["drilling", "drilling"],
            "YEAR": pd.array([2021, 2021], dtype="Int64"),
            "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep"],
            "DRILLING_DAYS": [45.0, 60.0],
            "BH_TOTAL_MD": [18000.0, 22000.0],
            "WELL_STATUS": ["COM", "PA"],
        })
        result = ComprehensiveActivityAnalyzer(df).analyze()
        ca = result["cross_activity"]
        assert ca["drilling_count"] == 2
        assert ca["intervention_count"] == 0
        assert ca["ratio"] == 0.0

    def test_single_year_data(self) -> None:
        """Only one year of data -> by_year still produces valid rows."""
        df = pd.DataFrame({
            "RIG_NAME": ["RIG_A", "RIG_B", "RIG_C"],
            "WAR_START_DT": ["1/1/2021", "2/1/2021", "3/1/2021"],
            "WAR_END_DT": ["1/7/2021", "2/7/2021", "3/7/2021"],
            "API_WELL_NUMBER": ["X001", "X002", "X003"],
            "BOTM_LEASE_NUM": ["L1", "L2", "L3"],
            "AREA_CODE": ["GC", "WR", "GC"],
            "BUS_ASC_NAME": ["SHELL", "BP", "SHELL"],
            "WATER_DEPTH": [3000.0, 5500.0, 1200.0],
            "RIG_TYPE": ["drillship", "semi_submersible", "jack_up"],
            "ACTIVITY_CATEGORY": ["drilling", "drilling", "drilling"],
            "YEAR": pd.array([2021, 2021, 2021], dtype="Int64"),
            "WATER_DEPTH_CLASS": ["Deep", "Ultra-deep", "Deep"],
            "DRILLING_DAYS": [45.0, 60.0, 30.0],
            "BH_TOTAL_MD": [18000.0, 22000.0, 12000.0],
            "WELL_STATUS": ["COM", "PA", "DRL"],
        })
        result = ComprehensiveActivityAnalyzer(df).analyze()
        by_year = result["drilling_efficiency"]["by_year"]
        assert isinstance(by_year, pd.DataFrame)
        assert len(by_year) == 1
        assert by_year.iloc[0]["count"] == 3
