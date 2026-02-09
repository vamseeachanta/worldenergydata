"""Tests for ActivityEnrichmentEngine (WRK-116 Phase 2).

TDD test suite verifying multi-source join enrichment of WAR data
with fleet, borehole, and paleowells data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.enrichment_engine import (
    ActivityEnrichmentEngine,
)


# -- Basic contract tests ---------------------------------------------------


class TestEnrichBasicContract:
    """Verify the engine satisfies basic DataFrame contracts."""

    def test_enrich_returns_dataframe(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        assert isinstance(result, pd.DataFrame)

    def test_enrich_preserves_row_count(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame, paleowells_era_map: dict[str, str],
    ) -> None:
        engine = ActivityEnrichmentEngine(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        result = engine.enrich()
        assert len(result) == len(war_df)

    def test_empty_war_returns_empty(
        self, empty_war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(empty_war_df, fleet_df)
        result = engine.enrich()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


# -- Step 1: WAR to Fleet join tests ----------------------------------------


class TestFleetJoin:
    """Verify WAR-to-fleet join and heuristic fallback."""

    def test_rig_type_from_fleet_join(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        rowan_rows = result[result["RIG_NAME"] == "ROWAN GORILLA V"]
        assert (rowan_rows["RIG_TYPE"] == "jack_up").all()

    def test_rig_type_heuristic_fallback(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        dp_rows = result[result["RIG_NAME"] == "DEEPWATER PATHFINDER"]
        assert (dp_rows["RIG_TYPE"] == "drillship").all()

    def test_activity_category_drilling(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        drillship_rows = result[result["RIG_TYPE"] == "drillship"]
        assert (drillship_rows["ACTIVITY_CATEGORY"] == "drilling").all()
        jackup_rows = result[result["RIG_TYPE"] == "jack_up"]
        assert (jackup_rows["ACTIVITY_CATEGORY"] == "drilling").all()

    def test_activity_category_intervention(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        wireline_rows = result[result["RIG_TYPE"] == "wireline_unit"]
        assert (wireline_rows["ACTIVITY_CATEGORY"] == "intervention").all()
        liftboat_rows = result[result["RIG_TYPE"] == "lift_boat"]
        assert (liftboat_rows["ACTIVITY_CATEGORY"] == "intervention").all()

    def test_activity_category_unknown(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        mystery_rows = result[result["RIG_NAME"] == "MYSTERY RIG"]
        assert (mystery_rows["ACTIVITY_CATEGORY"] == "unknown").all()

    def test_year_parsed_from_war_start_dt(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        assert set(result["YEAR"].dropna().unique()) == {2020, 2021, 2022}


# -- Step 2: Borehole join tests --------------------------------------------


class TestBoreholeJoin:
    """Verify WAR-to-borehole join and derived columns."""

    def test_borehole_join_adds_depth(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame,
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df, borehole_df)
        result = engine.enrich()
        matched = result[result["API_WELL_NUMBER"].isin(
            ["W001", "W002", "W003", "W004", "W005", "W006", "W007", "W008"]
        )]
        assert matched["BH_TOTAL_MD"].notna().all()

    def test_borehole_join_unmatched_wells_have_nan(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame,
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df, borehole_df)
        result = engine.enrich()
        unmatched = result[result["API_WELL_NUMBER"].isin(
            ["W009", "W010", "W011"]
        )]
        assert unmatched["BH_TOTAL_MD"].isna().all()

    def test_drilling_days_computed(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame,
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df, borehole_df)
        result = engine.enrich()
        w001 = result[result["API_WELL_NUMBER"] == "W001"].iloc[0]
        # 2020-01-10 minus 2019-11-01 = 70 days
        assert w001["DRILLING_DAYS"] == 70.0

    def test_negative_drilling_days_clamped(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
    ) -> None:
        """If WELL_SPUD_DATE > TOTAL_DEPTH_DATE, DRILLING_DAYS must be NaN."""
        bh = pd.DataFrame({
            "API_WELL_NUMBER": ["W001"],
            "WELL_SPUD_DATE": ["2020-06-01"],
            "TOTAL_DEPTH_DATE": ["2020-01-01"],
            "BH_TOTAL_MD": [10000.0],
            "WATER_DEPTH": [4500.0],
            "BOREHOLE_STAT_CD": ["COM"],
            "WELL_NAME_SUFFIX": ["ST00BP00"],
        })
        engine = ActivityEnrichmentEngine(war_df, fleet_df, bh)
        result = engine.enrich()
        w001 = result[result["API_WELL_NUMBER"] == "W001"].iloc[0]
        assert pd.isna(w001["DRILLING_DAYS"])

    def test_water_depth_coalesce(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
    ) -> None:
        """WAR WATER_DEPTH takes priority; borehole fills NaN gaps."""
        bh = pd.DataFrame({
            "API_WELL_NUMBER": ["W007", "W009"],
            "WELL_SPUD_DATE": ["2021-09-10", "2021-01-01"],
            "TOTAL_DEPTH_DATE": ["2021-11-25", "2021-03-01"],
            "BH_TOTAL_MD": [8200.0, 5000.0],
            "WATER_DEPTH": [950.0, 1500.0],
            "BOREHOLE_STAT_CD": ["COM", "DRL"],
            "WELL_NAME_SUFFIX": ["ST00BP00", "ST00BP00"],
        })
        engine = ActivityEnrichmentEngine(war_df, fleet_df, bh)
        result = engine.enrich()
        # W007 has WAR WATER_DEPTH = NaN, borehole = 950 -> 950
        w007 = result[result["API_WELL_NUMBER"] == "W007"].iloc[0]
        assert w007["WATER_DEPTH_FINAL"] == 950.0
        # W001 has WAR WATER_DEPTH = 4500, borehole not in this bh -> WAR wins
        w001 = result[result["API_WELL_NUMBER"] == "W001"].iloc[0]
        assert w001["WATER_DEPTH_FINAL"] == 4500.0

    def test_water_depth_column_conflict(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame,
    ) -> None:
        """Borehole WATER_DEPTH renamed to BH_WATER_DEPTH, no collision."""
        engine = ActivityEnrichmentEngine(war_df, fleet_df, borehole_df)
        result = engine.enrich()
        assert "BH_WATER_DEPTH" in result.columns
        assert "WATER_DEPTH" in result.columns
        col_counts = list(result.columns).count("WATER_DEPTH")
        assert col_counts == 1

    def test_no_borehole_skips_enrichment(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df, borehole_df=None)
        result = engine.enrich()
        assert "BH_TOTAL_MD" not in result.columns
        assert "DRILLING_DAYS" not in result.columns


class TestBoreholeColumnCollision:
    """Regression: WAR zip includes mv_war_boreholes_view.txt columns."""

    def test_war_with_preexisting_bh_columns(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame,
    ) -> None:
        """When WAR already has BH_TOTAL_MD etc., join must not produce _x/_y."""
        war_with_bh = war_df.copy()
        war_with_bh["BH_TOTAL_MD"] = 9999.0
        war_with_bh["WELL_SPUD_DATE"] = "2019-01-01"
        war_with_bh["TOTAL_DEPTH_DATE"] = "2019-06-01"
        war_with_bh["WELL_NAME_SUFFIX"] = "ST00BP00"

        engine = ActivityEnrichmentEngine(war_with_bh, fleet_df, borehole_df)
        result = engine.enrich()

        assert "BH_TOTAL_MD" in result.columns
        assert "BH_TOTAL_MD_x" not in result.columns
        assert "BH_TOTAL_MD_y" not in result.columns
        matched = result[result["API_WELL_NUMBER"] == "W001"]
        assert matched["BH_TOTAL_MD"].notna().all()

    def test_join_stats_with_preexisting_columns(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame,
    ) -> None:
        """get_join_stats() must report >0% borehole match rate."""
        war_with_bh = war_df.copy()
        war_with_bh["BH_TOTAL_MD"] = float("nan")
        war_with_bh["WELL_SPUD_DATE"] = pd.NaT

        engine = ActivityEnrichmentEngine(war_with_bh, fleet_df, borehole_df)
        engine.enrich()
        stats = engine.get_join_stats()
        assert stats["borehole_match_rate"] > 0.0


# -- Step 3: Water depth classification tests --------------------------------


class TestWaterDepthClassification:
    """Verify depth classification thresholds."""

    def test_water_depth_class_shallow(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        shallow = result[result["WATER_DEPTH"] < 200]
        assert (shallow["WATER_DEPTH_CLASS"] == "Shallow").all()

    def test_water_depth_class_deep(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        deep = result[
            (result["WATER_DEPTH"] >= 1000) & (result["WATER_DEPTH"] < 5000)
        ]
        assert len(deep) > 0
        assert (deep["WATER_DEPTH_CLASS"] == "Deep").all()

    def test_water_depth_class_ultra_deep(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        ultra = result[result["WATER_DEPTH"] >= 5000]
        assert len(ultra) > 0
        assert (ultra["WATER_DEPTH_CLASS"] == "Ultra-deep").all()


# -- Step 4: Paleowells era mapping tests ------------------------------------


class TestGeologicalEraMapping:
    """Verify era mapping from paleowells data."""

    def test_geological_era_mapping(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        paleowells_era_map: dict[str, str],
    ) -> None:
        engine = ActivityEnrichmentEngine(
            war_df, fleet_df, era_map=paleowells_era_map,
        )
        result = engine.enrich()
        w001 = result[result["API_WELL_NUMBER"] == "W001"].iloc[0]
        assert w001["GEOLOGICAL_ERA"] == "Miocene"
        w003 = result[result["API_WELL_NUMBER"] == "W003"].iloc[0]
        assert w003["GEOLOGICAL_ERA"] == "Eocene"

    def test_era_unmapped_wells_nan(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        paleowells_era_map: dict[str, str],
    ) -> None:
        engine = ActivityEnrichmentEngine(
            war_df, fleet_df, era_map=paleowells_era_map,
        )
        result = engine.enrich()
        # W009 is not in the era map
        w009 = result[result["API_WELL_NUMBER"] == "W009"].iloc[0]
        assert pd.isna(w009["GEOLOGICAL_ERA"])

    def test_no_era_map_skips_era(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df, era_map=None)
        result = engine.enrich()
        assert "GEOLOGICAL_ERA" not in result.columns


# -- Step 5: Memory optimization tests --------------------------------------


class TestCategoryDtypeOptimization:
    """Verify category dtype casting for memory efficiency."""

    def test_category_dtype_optimization(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame
    ) -> None:
        engine = ActivityEnrichmentEngine(war_df, fleet_df)
        result = engine.enrich()
        assert result["RIG_TYPE"].dtype.name == "category"
        assert result["ACTIVITY_CATEGORY"].dtype.name == "category"
        assert result["AREA_CODE"].dtype.name == "category"
        assert result["WATER_DEPTH_CLASS"].dtype.name == "category"


# -- Join stats tests --------------------------------------------------------


class TestJoinStats:
    """Verify get_join_stats() output structure and values."""

    def test_get_join_stats_keys(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame, paleowells_era_map: dict[str, str],
    ) -> None:
        engine = ActivityEnrichmentEngine(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        engine.enrich()
        stats = engine.get_join_stats()
        expected_keys = {
            "total_war_records",
            "fleet_match_rate",
            "borehole_match_rate",
            "era_match_rate",
            "water_depth_fill_rate",
        }
        assert set(stats.keys()) == expected_keys

    def test_get_join_stats_values(
        self, war_df: pd.DataFrame, fleet_df: pd.DataFrame,
        borehole_df: pd.DataFrame, paleowells_era_map: dict[str, str],
    ) -> None:
        engine = ActivityEnrichmentEngine(
            war_df, fleet_df, borehole_df, paleowells_era_map,
        )
        engine.enrich()
        stats = engine.get_join_stats()
        assert stats["total_war_records"] == 15
        assert 0.0 <= stats["fleet_match_rate"] <= 1.0
        assert 0.0 <= stats["borehole_match_rate"] <= 1.0
        assert 0.0 <= stats["era_match_rate"] <= 1.0
        assert 0.0 <= stats["water_depth_fill_rate"] <= 1.0
