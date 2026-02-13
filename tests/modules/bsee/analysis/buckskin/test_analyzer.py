"""Tests for BuckskinAnalyzer — field-level analytics for Buckskin.

The analyzer receives the dict output of BuckskinExtractor.extract_all()
and computes production summaries, wellbore inventories, drilling
timelines, WAR activity summaries, and benchmark validations.
"""

from __future__ import annotations

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Shared synthetic data fixtures
# ---------------------------------------------------------------------------

BUCKSKIN_BLOCKS = [785, 828, 829, 830, 871, 872]


@pytest.fixture()
def production_df() -> pd.DataFrame:
    """Realistic production data across multiple blocks and years."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "6080400001",
                "6080400001",
                "6080400001",
                "6080400002",
                "6080400002",
                "6080400003",
                "6080400003",
                "6080400003",
            ],
            "LEASE_NUMBER": [
                "G35123",
                "G35123",
                "G35123",
                "G35124",
                "G35124",
                "G35125",
                "G35125",
                "G35125",
            ],
            "BOTM_AREA_CODE": ["KC"] * 8,
            "BOTM_BLOCK_NUM": [785, 785, 785, 829, 829, 872, 872, 872],
            "PROD_YEAR": [2019, 2020, 2021, 2020, 2021, 2019, 2020, 2021],
            # Oil in barrels
            "MON_O_PROD_VOL": [
                500_000,
                1_200_000,
                800_000,
                600_000,
                400_000,
                300_000,
                900_000,
                700_000,
            ],
            # Gas in MCF
            "MON_G_PROD_VOL": [
                250_000,
                600_000,
                400_000,
                300_000,
                200_000,
                150_000,
                450_000,
                350_000,
            ],
            # Water in barrels
            "MON_WTR_PROD_VOL": [
                50_000,
                120_000,
                80_000,
                60_000,
                40_000,
                30_000,
                90_000,
                70_000,
            ],
        }
    )


@pytest.fixture()
def wells_df() -> pd.DataFrame:
    """Realistic well inventory across blocks with varied types."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "6080400001",
                "6080400002",
                "6080400003",
                "6080400004",
                "6080400005",
            ],
            "WELL_NAME": [
                "BUCKSKIN A-1",
                "BUCKSKIN A-2",
                "BUCKSKIN B-1",
                "BUCKSKIN EXP-1",
                "BUCKSKIN EXP-2",
            ],
            "BOTM_AREA_CODE": ["KC"] * 5,
            "BOTM_BLOCK_NUM": [785, 829, 872, 828, 830],
            "WATER_DEPTH": [6800.0, 6900.0, 6850.0, 6750.0, 6920.0],
            "WELL_SPUD_DATE": [
                "2009-04-15",
                "2015-07-22",
                "2017-11-03",
                "2012-02-10",
                "2020-05-30",
            ],
            "WELL_TYPE_CODE": ["D", "D", "D", "E", "E"],
        }
    )


@pytest.fixture()
def war_df() -> pd.DataFrame:
    """WAR activity records with various activity codes."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "6080400001",
                "6080400001",
                "6080400002",
                "6080400003",
                "6080400003",
                "6080400004",
            ],
            "RIG_NAME": [
                "DEEPWATER PROTEUS",
                "Q5000",
                "DEEPWATER PROTEUS",
                "ISLAND PERFORMER",
                "ISLAND PERFORMER",
                "DEEPWATER PROTEUS",
            ],
            "BOTM_AREA_CODE": ["KC"] * 6,
            "BOTM_BLOCK_NUM": [785, 785, 829, 872, 872, 828],
            "WAR_RPT_START_DT": [
                "2017-01-05",
                "2019-06-10",
                "2018-03-15",
                "2017-08-20",
                "2020-01-08",
                "2012-05-01",
            ],
            "WAR_RPT_END_DT": [
                "2017-04-30",
                "2019-07-20",
                "2018-06-30",
                "2017-12-15",
                "2020-04-22",
                "2012-08-15",
            ],
            "WAR_ACTIVITY_CODE": ["DRILL", "WO", "DRILL", "COMPL", "SI", "DRILL"],
        }
    )


@pytest.fixture()
def leases_df() -> pd.DataFrame:
    """Lease records for Buckskin blocks."""
    return pd.DataFrame(
        {
            "LEASE_NUMBER": ["G35123", "G35124", "G35125"],
            "AREA_CODE": ["KC", "KC", "KC"],
            "BLOCK_NUM": [785, 829, 872],
            "LEASE_EFF_DATE": ["2005-06-01", "2005-06-01", "2005-06-01"],
        }
    )


@pytest.fixture()
def completions_df() -> pd.DataFrame:
    """Completion records for Buckskin wells."""
    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "6080400001",
                "6080400002",
                "6080400003",
            ],
            "COMP_DATE": ["2018-12-15", "2019-09-20", "2018-06-01"],
            "COMP_STATUS_CODE": ["COM", "COM", "COM"],
        }
    )


@pytest.fixture()
def buckskin_data(
    production_df: pd.DataFrame,
    wells_df: pd.DataFrame,
    war_df: pd.DataFrame,
    leases_df: pd.DataFrame,
    completions_df: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Complete data dict as returned by BuckskinExtractor.extract_all()."""
    return {
        "production": production_df,
        "wells": wells_df,
        "war_activity": war_df,
        "leases": leases_df,
        "completions": completions_df,
    }


@pytest.fixture()
def empty_data() -> dict[str, pd.DataFrame]:
    """Data dict with all-empty DataFrames for edge-case testing."""
    return {
        "production": pd.DataFrame(),
        "wells": pd.DataFrame(),
        "war_activity": pd.DataFrame(),
        "leases": pd.DataFrame(),
        "completions": pd.DataFrame(),
    }


# ---------------------------------------------------------------------------
# Production summary
# ---------------------------------------------------------------------------


class TestProductionSummary:
    """Tests for BuckskinAnalyzer.production_summary()."""

    def test_production_summary_cumulative_oil(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Cumulative oil is the total MON_O_PROD_VOL converted to MMBBL."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        summary = analyzer.production_summary()

        total_bbl = sum(buckskin_data["production"]["MON_O_PROD_VOL"])
        expected_mmbbl = total_bbl / 1_000_000
        assert summary["cumulative_oil_mmbbl"] == pytest.approx(
            expected_mmbbl, rel=1e-6
        )

    def test_production_summary_per_block(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Per-block breakdown sums oil to each BOTM_BLOCK_NUM."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        summary = analyzer.production_summary()

        per_block = summary["per_block"]
        # Block 785 total: 500k + 1.2M + 800k = 2.5M bbl
        assert per_block[785]["oil_bbl"] == pytest.approx(2_500_000, rel=1e-6)
        # Block 829 total: 600k + 400k = 1.0M bbl
        assert per_block[829]["oil_bbl"] == pytest.approx(1_000_000, rel=1e-6)
        # Block 872 total: 300k + 900k + 700k = 1.9M bbl
        assert per_block[872]["oil_bbl"] == pytest.approx(1_900_000, rel=1e-6)

    def test_production_summary_peak_rate(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Peak daily rate is max annual oil divided by 365."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        summary = analyzer.production_summary()

        # Annual sums: 2019=800k, 2020=2.7M, 2021=1.9M -- peak is 2020
        peak_annual = 1_200_000 + 600_000 + 900_000  # 2.7M
        expected_daily = peak_annual / 365
        assert summary["peak_oil_rate_bopd"] == pytest.approx(
            expected_daily, rel=1e-6
        )

    def test_production_summary_well_count(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Well count is the number of unique API numbers in production."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        summary = analyzer.production_summary()

        assert summary["producing_well_count"] == 3

    def test_production_summary_date_range(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """First and last production years are captured."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        summary = analyzer.production_summary()

        assert summary["first_production_year"] == 2019
        assert summary["last_production_year"] == 2021


# ---------------------------------------------------------------------------
# Wellbore inventory
# ---------------------------------------------------------------------------


class TestWellboreInventory:
    """Tests for BuckskinAnalyzer.wellbore_inventory()."""

    def test_wellbore_inventory_classifies_types(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """E = exploration, D = development based on WELL_TYPE_CODE."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        inventory = analyzer.wellbore_inventory()

        assert inventory["development_count"] == 3
        assert inventory["exploration_count"] == 2

    def test_wellbore_inventory_counts_per_block(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Well counts are broken down per block."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        inventory = analyzer.wellbore_inventory()

        per_block = inventory["per_block"]
        # One well each on blocks 785, 829, 872, 828, 830
        assert per_block[785] == 1
        assert per_block[829] == 1
        assert per_block[872] == 1
        assert per_block[828] == 1
        assert per_block[830] == 1


# ---------------------------------------------------------------------------
# Drilling timeline
# ---------------------------------------------------------------------------


class TestDrillingTimeline:
    """Tests for BuckskinAnalyzer.drilling_timeline()."""

    def test_drilling_timeline_ordered_by_date(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Spud dates are returned in chronological order."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        timeline = analyzer.drilling_timeline()

        dates = timeline["WELL_SPUD_DATE"].tolist()
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# WAR activity summary
# ---------------------------------------------------------------------------


class TestWarActivitySummary:
    """Tests for BuckskinAnalyzer.war_activity_summary()."""

    def test_war_activity_summary_groups_by_type(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Activities are grouped by WAR_ACTIVITY_CODE."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        summary = analyzer.war_activity_summary()

        assert set(summary.keys()) == {"DRILL", "WO", "COMPL", "SI"}

    def test_war_activity_summary_counts(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """Count of activities per type is correct."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        summary = analyzer.war_activity_summary()

        assert summary["DRILL"] == 3
        assert summary["WO"] == 1
        assert summary["COMPL"] == 1
        assert summary["SI"] == 1


# ---------------------------------------------------------------------------
# Benchmark validation
# ---------------------------------------------------------------------------


class TestValidateBenchmarks:
    """Tests for BuckskinAnalyzer.validate_benchmarks()."""

    def test_validate_benchmarks_first_oil_year(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """First oil year should be approximately 2019 for synthetic data."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        benchmarks = analyzer.validate_benchmarks()

        assert benchmarks["first_oil_year"] == 2019

    def test_validate_benchmarks_well_count_minimum(
        self, buckskin_data: dict[str, pd.DataFrame]
    ):
        """At least 2 producing wells in our synthetic data."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=buckskin_data)
        benchmarks = analyzer.validate_benchmarks()

        assert benchmarks["producing_well_count"] >= 2


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------


class TestEmptyData:
    """Tests for safe behavior with empty DataFrames."""

    def test_empty_data_production_summary_returns_defaults(
        self, empty_data: dict[str, pd.DataFrame]
    ):
        """Empty production DataFrame yields zeroed summary."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=empty_data)
        summary = analyzer.production_summary()

        assert summary["cumulative_oil_mmbbl"] == 0.0
        assert summary["producing_well_count"] == 0
        assert summary["peak_oil_rate_bopd"] == 0.0
        assert summary["first_production_year"] is None
        assert summary["last_production_year"] is None
        assert summary["per_block"] == {}

    def test_empty_data_wellbore_inventory_returns_defaults(
        self, empty_data: dict[str, pd.DataFrame]
    ):
        """Empty wells DataFrame yields zeroed inventory."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=empty_data)
        inventory = analyzer.wellbore_inventory()

        assert inventory["development_count"] == 0
        assert inventory["exploration_count"] == 0
        assert inventory["per_block"] == {}

    def test_empty_data_war_activity_summary_returns_defaults(
        self, empty_data: dict[str, pd.DataFrame]
    ):
        """Empty WAR DataFrame yields empty activity dict."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=empty_data)
        summary = analyzer.war_activity_summary()

        assert summary == {}

    def test_empty_data_validate_benchmarks_returns_defaults(
        self, empty_data: dict[str, pd.DataFrame]
    ):
        """Empty data yields safe benchmark defaults."""
        from worldenergydata.bsee.analysis.buckskin.analyzer import (
            BuckskinAnalyzer,
        )

        analyzer = BuckskinAnalyzer(data=empty_data)
        benchmarks = analyzer.validate_benchmarks()

        assert benchmarks["first_oil_year"] is None
        assert benchmarks["producing_well_count"] == 0
