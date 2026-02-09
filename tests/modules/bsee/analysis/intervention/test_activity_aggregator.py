"""Tests for WAR activity aggregation engine (WRK-115 Phase 1).

TDD Red phase: all tests written before implementation.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.activity_aggregator import (
    WARActivityAggregator,
    classify_activity,
)


# ---------------------------------------------------------------------------
# classify_activity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rig_type,expected",
    [
        ("drillship", "drilling"),
        ("semi_submersible", "drilling"),
        ("jack_up", "drilling"),
        ("platform_rig", "drilling"),
        ("tender_assisted", "drilling"),
        ("inland_barge", "drilling"),
        ("submersible", "drilling"),
        ("wireline_unit", "intervention"),
        ("coil_tubing_unit", "intervention"),
        ("lift_boat", "intervention"),
        ("snubbing_unit", "intervention"),
        ("workover_rig", "intervention"),
        ("support_vessel", "intervention"),
        ("pumping_unit", "intervention"),
        ("unknown", "unknown"),
        ("land_rig", "unknown"),
        ("something_else", "unknown"),
    ],
)
def test_classify_activity(rig_type: str, expected: str) -> None:
    assert classify_activity(rig_type) == expected


# ---------------------------------------------------------------------------
# Fixtures — synthetic data
# ---------------------------------------------------------------------------


def _make_war_df() -> pd.DataFrame:
    """Synthetic WAR DataFrame with 15 rows across 3 years."""
    return pd.DataFrame(
        {
            "RIG_NAME": [
                "DEEPWATER PATHFINDER",  # drillship (heuristic)
                "DEEPWATER PATHFINDER",  # drillship (heuristic)
                "OCEAN STAR",  # semi-sub (heuristic)
                "OCEAN STAR",  # semi-sub (heuristic)
                "ROWAN GORILLA V",  # jack_up (fleet)
                "ROWAN GORILLA V",  # jack_up (fleet)
                "ROWAN GORILLA V",  # jack_up (fleet) — same well
                "WIRELINE UNIT 7",  # wireline_unit (fleet)
                "WIRELINE UNIT 7",  # wireline_unit (fleet)
                "COIL TUBING ALPHA",  # coil_tubing_unit (heuristic)
                "LIFT BOAT 99",  # lift_boat (heuristic)
                "LIFT BOAT 99",  # lift_boat (heuristic)
                "MYSTERY RIG",  # unknown (not in fleet, no keyword)
                "DEEPWATER PATHFINDER",  # drillship 2022
                "WIRELINE UNIT 7",  # wireline_unit 2022
            ],
            "WAR_START_DT": [
                "1/15/2020",
                "3/20/2020",
                "6/1/2020",
                "7/4/2020",
                "2/10/2021",
                "5/22/2021",
                "8/30/2021",
                "4/11/2021",
                "9/15/2021",
                "11/3/2021",
                "1/8/2020",
                "12/25/2020",
                "3/3/2021",
                "6/6/2022",
                "10/10/2022",
            ],
            "API_WELL_NUMBER": [
                "W001",
                "W002",
                "W003",
                "W003",
                "W004",
                "W004",
                "W004",
                "W005",
                "W006",
                "W007",
                "W008",
                "W008",
                "W009",
                "W010",
                "W011",
            ],
            "BOTM_LEASE_NUM": [
                "L100",
                "L100",
                "L200",
                "L200",
                "L300",
                "L300",
                "L300",
                "L400",
                "L400",
                "L500",
                "L600",
                "L600",
                "L700",
                "L100",
                "L400",
            ],
            "AREA_CODE": [
                "GC",
                "GC",
                "WR",
                "WR",
                "HI",
                "HI",
                "HI",
                "GC",
                "GC",
                "MC",
                "ST",
                "ST",
                "VR",
                "GC",
                "GC",
            ],
        }
    )


def _make_fleet_df() -> pd.DataFrame:
    """Synthetic fleet DataFrame with known rig types."""
    return pd.DataFrame(
        {
            "RIG_NAME": [
                "ROWAN GORILLA V",
                "WIRELINE UNIT 7",
                "SOME OTHER RIG",
            ],
            "RIG_TYPE": [
                "jack_up",
                "wireline_unit",
                "platform_rig",
            ],
        }
    )


# ---------------------------------------------------------------------------
# _join_rig_types
# ---------------------------------------------------------------------------


class TestJoinRigTypes:
    """Verify enrichment of WAR data with rig type and activity category."""

    def test_matched_records_get_fleet_rig_type(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        agg = WARActivityAggregator(war_df, fleet_df)
        result = agg._join_rig_types()

        # ROWAN GORILLA V is in fleet as jack_up
        rowan_rows = result[result["RIG_NAME"] == "ROWAN GORILLA V"]
        assert (rowan_rows["RIG_TYPE"] == "jack_up").all()

    def test_unmatched_records_get_heuristic_rig_type(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        agg = WARActivityAggregator(war_df, fleet_df)
        result = agg._join_rig_types()

        # DEEPWATER PATHFINDER not in fleet — heuristic should classify as drillship
        dp_rows = result[result["RIG_NAME"] == "DEEPWATER PATHFINDER"]
        assert (dp_rows["RIG_TYPE"] == "drillship").all()

    def test_unknown_rig_fallback(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        agg = WARActivityAggregator(war_df, fleet_df)
        result = agg._join_rig_types()

        # MYSTERY RIG not in fleet and no keyword match -> unknown
        mystery_rows = result[result["RIG_NAME"] == "MYSTERY RIG"]
        assert (mystery_rows["RIG_TYPE"] == "unknown").all()

    def test_year_column_extracted(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        agg = WARActivityAggregator(war_df, fleet_df)
        result = agg._join_rig_types()

        assert "YEAR" in result.columns
        assert set(result["YEAR"].unique()) == {2020, 2021, 2022}

    def test_activity_category_populated(self) -> None:
        war_df = _make_war_df()
        fleet_df = _make_fleet_df()
        agg = WARActivityAggregator(war_df, fleet_df)
        result = agg._join_rig_types()

        assert "ACTIVITY_CATEGORY" in result.columns
        # All rows should have a non-null category
        assert result["ACTIVITY_CATEGORY"].notna().all()
        # Check specific known categories
        dp_rows = result[result["RIG_NAME"] == "DEEPWATER PATHFINDER"]
        assert (dp_rows["ACTIVITY_CATEGORY"] == "drilling").all()

        wl_rows = result[result["RIG_NAME"] == "WIRELINE UNIT 7"]
        assert (wl_rows["ACTIVITY_CATEGORY"] == "intervention").all()


# ---------------------------------------------------------------------------
# aggregate_by_year_and_type
# ---------------------------------------------------------------------------


class TestAggregateByYearAndType:
    """Verify groupby [YEAR, RIG_TYPE] aggregation."""

    def test_output_columns(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_type()

        expected_cols = {
            "YEAR",
            "RIG_TYPE",
            "activity_count",
            "unique_wells",
            "unique_leases",
            "unique_areas",
        }
        assert set(result.columns) == expected_cols

    def test_activity_count_per_group(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_type()

        # 2020, drillship: DEEPWATER PATHFINDER appears 2 times
        row = result[
            (result["YEAR"] == 2020) & (result["RIG_TYPE"] == "drillship")
        ]
        assert row["activity_count"].iloc[0] == 2

        # 2021, jack_up: ROWAN GORILLA V appears 3 times
        row = result[
            (result["YEAR"] == 2021) & (result["RIG_TYPE"] == "jack_up")
        ]
        assert row["activity_count"].iloc[0] == 3

    def test_unique_wells_counts_distinct(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_type()

        # 2021, jack_up: 3 rows but all same well W004 -> unique_wells = 1
        row = result[
            (result["YEAR"] == 2021) & (result["RIG_TYPE"] == "jack_up")
        ]
        assert row["unique_wells"].iloc[0] == 1

        # 2020, drillship: 2 rows with W001, W002 -> unique_wells = 2
        row = result[
            (result["YEAR"] == 2020) & (result["RIG_TYPE"] == "drillship")
        ]
        assert row["unique_wells"].iloc[0] == 2

    def test_unique_leases_counts_distinct(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_type()

        # 2020, semi_submersible: 2 rows both L200 -> unique_leases = 1
        row = result[
            (result["YEAR"] == 2020) & (result["RIG_TYPE"] == "semi_submersible")
        ]
        assert row["unique_leases"].iloc[0] == 1

    def test_sorted_by_year_and_rig_type(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_type()

        years = result["YEAR"].tolist()
        assert years == sorted(years)


# ---------------------------------------------------------------------------
# aggregate_by_year_and_category
# ---------------------------------------------------------------------------


class TestAggregateByYearAndCategory:
    """Verify groupby [YEAR, ACTIVITY_CATEGORY] aggregation."""

    def test_output_columns(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_category()

        expected_cols = {
            "YEAR",
            "ACTIVITY_CATEGORY",
            "activity_count",
            "unique_wells",
            "unique_leases",
            "unique_areas",
        }
        assert set(result.columns) == expected_cols

    def test_drilling_count_per_year(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_category()

        # 2020 drilling: DEEPWATER PATHFINDER (2) + OCEAN STAR (2) = 4
        row = result[
            (result["YEAR"] == 2020)
            & (result["ACTIVITY_CATEGORY"] == "drilling")
        ]
        assert row["activity_count"].iloc[0] == 4

    def test_intervention_count_per_year(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_category()

        # 2020 intervention: LIFT BOAT 99 (2) = 2
        row = result[
            (result["YEAR"] == 2020)
            & (result["ACTIVITY_CATEGORY"] == "intervention")
        ]
        assert row["activity_count"].iloc[0] == 2

    def test_unknown_category_present(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        result = agg.aggregate_by_year_and_category()

        # 2021: MYSTERY RIG -> unknown category
        row = result[
            (result["YEAR"] == 2021)
            & (result["ACTIVITY_CATEGORY"] == "unknown")
        ]
        assert row["activity_count"].iloc[0] == 1


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    """Verify summary dictionary."""

    def test_total_war_records(self) -> None:
        war_df = _make_war_df()
        agg = WARActivityAggregator(war_df, _make_fleet_df())
        summary = agg.get_summary()

        assert summary["total_war_records"] == len(war_df)

    def test_year_range(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        summary = agg.get_summary()

        assert summary["year_range"] == (2020, 2022)

    def test_rig_type_counts(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        summary = agg.get_summary()

        rig_counts = summary["rig_type_counts"]
        # drillship: rows 0,1,13 = 3
        assert rig_counts["drillship"] == 3
        # jack_up: rows 4,5,6 = 3
        assert rig_counts["jack_up"] == 3
        # wireline_unit: rows 7,8,14 = 3
        assert rig_counts["wireline_unit"] == 3

    def test_category_counts(self) -> None:
        agg = WARActivityAggregator(_make_war_df(), _make_fleet_df())
        summary = agg.get_summary()

        cat_counts = summary["category_counts"]
        assert "drilling" in cat_counts
        assert "intervention" in cat_counts
        assert "unknown" in cat_counts
        # Total should equal total_war_records
        assert sum(cat_counts.values()) == summary["total_war_records"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case handling: missing dates, empty DataFrames."""

    def test_missing_war_start_dt_falls_back_to_war_end_dt(self) -> None:
        """When WAR_START_DT is NaN, YEAR should come from WAR_END_DT."""
        war_df = pd.DataFrame(
            {
                "RIG_NAME": ["DEEPWATER ATLAS", "DEEPWATER ATLAS"],
                "WAR_START_DT": [None, "5/1/2023"],
                "WAR_END_DT": ["12/31/2023", "5/15/2023"],
                "API_WELL_NUMBER": ["W100", "W101"],
                "BOTM_LEASE_NUM": ["L900", "L901"],
                "AREA_CODE": ["GC", "GC"],
            }
        )
        fleet_df = pd.DataFrame(
            {"RIG_NAME": ["DEEPWATER ATLAS"], "RIG_TYPE": ["drillship"]}
        )
        agg = WARActivityAggregator(war_df, fleet_df)
        result = agg._join_rig_types()

        assert result["YEAR"].tolist() == [2023, 2023]

    def test_empty_war_dataframe(self) -> None:
        """Empty WAR data should produce empty aggregation, not crash."""
        war_df = pd.DataFrame(
            columns=[
                "RIG_NAME",
                "WAR_START_DT",
                "API_WELL_NUMBER",
                "BOTM_LEASE_NUM",
                "AREA_CODE",
            ]
        )
        fleet_df = pd.DataFrame(
            {"RIG_NAME": ["SOME RIG"], "RIG_TYPE": ["drillship"]}
        )
        agg = WARActivityAggregator(war_df, fleet_df)

        by_type = agg.aggregate_by_year_and_type()
        assert len(by_type) == 0
        assert set(by_type.columns) == {
            "YEAR",
            "RIG_TYPE",
            "activity_count",
            "unique_wells",
            "unique_leases",
            "unique_areas",
        }

        by_cat = agg.aggregate_by_year_and_category()
        assert len(by_cat) == 0

        summary = agg.get_summary()
        assert summary["total_war_records"] == 0
        assert summary["year_range"] == (None, None)
        assert summary["rig_type_counts"] == {}
        assert summary["category_counts"] == {}
