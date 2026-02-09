"""Tests for WellDesignAnalyzer (WRK-116 Phase 6).

TDD test suite verifying well design analysis across 5 modules:
casing program, casing grade analysis, completion analysis,
geology analysis, and pressure envelope.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.well_design_analyzer import (
    WellDesignAnalyzer,
)

_EXPECTED_KEYS = frozenset({
    "casing_program",
    "casing_grade_analysis",
    "completion_analysis",
    "geology_analysis",
    "pressure_envelope",
})


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture()
def tubulars_df() -> pd.DataFrame:
    return pd.DataFrame({
        "API_WELL_NUMBER": ["W001", "W001", "W001", "W002", "W002"],
        "CSNG_INTV_TYPE_CD": ["C", "C", "L", "C", "C"],
        "CSNG_HOLE_SIZE": [36.0, 17.5, 12.25, 36.0, 17.5],
        "CASING_SIZE": [30.0, 13.375, 9.625, 30.0, 13.375],
        "CASING_WEIGHT": [310.0, 72.0, 53.5, 310.0, 72.0],
        "CASING_GRADE": ["X-80", "P-110", "P-110", "X-80", "N-80"],
        "CSNG_CEMENT_VOL": [2500.0, 1800.0, 900.0, 2600.0, 1700.0],
        "CSNG_SETTING_BOTM_MD": [2000.0, 8500.0, 15000.0, 1800.0, 7200.0],
        "CSNG_SETTING_TOP_MD": [0.0, 0.0, 7000.0, 0.0, 0.0],
    })


@pytest.fixture()
def perforations_df() -> pd.DataFrame:
    return pd.DataFrame({
        "API_WELL_NUMBER": ["W001", "W001", "W002"],
        "PERF_TOP_MD": [14000.0, 14500.0, 13000.0],
        "PERF_BASE_MD": [14200.0, 14800.0, 13500.0],
        "PERF_TOP_TVD": [13500.0, 14000.0, 12500.0],
        "PERF_BOTM_TVD": [13700.0, 14300.0, 13000.0],
    })


@pytest.fixture()
def geology_df() -> pd.DataFrame:
    return pd.DataFrame({
        "API_WELL_NUMBER": ["W001", "W001", "W002", "W002"],
        "GEO_MARKER_NAME": ["MIOCENE", "PLIOCENE", "MIOCENE", "EOCENE"],
        "TOP_MD": [5000.0, 3000.0, 4800.0, 8000.0],
    })


@pytest.fixture()
def hc_intervals_df() -> pd.DataFrame:
    return pd.DataFrame({
        "API_WELL_NUMBER": ["W001", "W001", "W002"],
        "INTERVAL_NAME": ["Zone A", "Zone B", "Zone C"],
        "TOP_MD": [14000.0, 14500.0, 13000.0],
        "BOTTOM_MD": [14200.0, 14800.0, 13500.0],
        "HYDROCARBON_TYPE_CD": ["O", "G", "O"],
    })


@pytest.fixture()
def bop_df() -> pd.DataFrame:
    return pd.DataFrame({
        "API_WELL_NUMBER": ["W001", "W001", "W002"],
        "BOP_TEST_DATE": ["2023-01-15", "2023-02-10", "2023-03-05"],
        "RAM_TST_PRSS": [10000.0, 10500.0, 11000.0],
        "ANNULAR_TST_PRSS": [5000.0, 5200.0, 5500.0],
        "BUS_ASC_NAME": ["OP_A", "OP_A", "OP_B"],
    })


# -- 1. Top-level contract ---------------------------------------------------


class TestAnalyzeContract:
    """Verify analyze() returns dict with all 5 module keys."""

    def test_analyze_returns_dict_with_five_keys(
        self,
        tubulars_df: pd.DataFrame,
        perforations_df: pd.DataFrame,
        geology_df: pd.DataFrame,
        hc_intervals_df: pd.DataFrame,
        bop_df: pd.DataFrame,
    ) -> None:
        analyzer = WellDesignAnalyzer(
            tubulars_df=tubulars_df,
            perforations_df=perforations_df,
            geology_df=geology_df,
            hc_intervals_df=hc_intervals_df,
            bop_df=bop_df,
        )
        result = analyzer.analyze()
        assert isinstance(result, dict)
        assert set(result.keys()) == _EXPECTED_KEYS


# -- 2. Casing program -------------------------------------------------------


class TestCasingProgram:
    """Verify casing program analysis from tubulars data."""

    def test_casing_program_total_records(
        self, tubulars_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(tubulars_df=tubulars_df)
        result = analyzer.analyze()["casing_program"]
        assert result["total_casing_records"] == 5
        assert result["unique_wells"] == 2

    def test_casing_program_grade_distribution(
        self, tubulars_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(tubulars_df=tubulars_df)
        grades = analyzer.analyze()["casing_program"]["grade_distribution"]
        assert isinstance(grades, pd.DataFrame)
        assert "CASING_GRADE" in grades.columns
        assert "count" in grades.columns
        grade_list = grades["CASING_GRADE"].tolist()
        assert "P-110" in grade_list
        assert "X-80" in grade_list

    def test_casing_program_hole_size_sorted(
        self, tubulars_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(tubulars_df=tubulars_df)
        sizes = analyzer.analyze()["casing_program"]["hole_size_distribution"]
        assert isinstance(sizes, pd.DataFrame)
        size_vals = sizes["CSNG_HOLE_SIZE"].tolist()
        assert size_vals == sorted(size_vals)


# -- 3. Casing grade analysis ------------------------------------------------


class TestCasingGradeAnalysis:
    """Verify casing grade deep-dive analysis."""

    def test_casing_grade_most_common(
        self, tubulars_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(tubulars_df=tubulars_df)
        result = analyzer.analyze()["casing_grade_analysis"]
        # P-110 appears twice, X-80 appears twice, N-80 once
        assert result["most_common_grade"] in ("P-110", "X-80")

    def test_casing_grade_by_grade_has_avg_weight(
        self, tubulars_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(tubulars_df=tubulars_df)
        by_grade = analyzer.analyze()["casing_grade_analysis"]["by_grade"]
        assert isinstance(by_grade, pd.DataFrame)
        assert "avg_weight" in by_grade.columns
        assert "avg_setting_depth" in by_grade.columns
        assert "count" in by_grade.columns


# -- 4. Completion analysis ---------------------------------------------------


class TestCompletionAnalysis:
    """Verify completion/perforation analysis."""

    def test_completion_depth_stats(
        self, perforations_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(perforations_df=perforations_df)
        result = analyzer.analyze()["completion_analysis"]
        assert result["total_perforations"] == 3
        assert result["unique_wells"] == 2
        stats = result["depth_stats"]
        assert "mean_perf_top" in stats
        assert "mean_perf_base" in stats
        assert "max_depth" in stats
        assert stats["max_depth"] == pytest.approx(14800.0)

    def test_completion_by_well(
        self, perforations_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(perforations_df=perforations_df)
        by_well = analyzer.analyze()["completion_analysis"]["by_well"]
        assert isinstance(by_well, pd.DataFrame)
        assert "API_WELL_NUMBER" in by_well.columns
        assert "perf_count" in by_well.columns
        assert "interval_ft" in by_well.columns
        # W001: max base 14800 - min top 14000 = 800
        w001 = by_well.loc[
            by_well["API_WELL_NUMBER"] == "W001", "interval_ft"
        ].iloc[0]
        assert w001 == pytest.approx(800.0)


# -- 5. Geology analysis -----------------------------------------------------


class TestGeologyAnalysis:
    """Verify geology and hydrocarbon analysis."""

    def test_geology_formation_distribution(
        self, geology_df: pd.DataFrame
    ) -> None:
        analyzer = WellDesignAnalyzer(geology_df=geology_df)
        result = analyzer.analyze()["geology_analysis"]
        assert result["total_markers"] == 4
        assert result["unique_formations"] == 3
        dist = result["formation_distribution"]
        assert isinstance(dist, pd.DataFrame)
        assert "GEO_MARKER_NAME" in dist.columns
        assert "count" in dist.columns
        assert "mean_depth" in dist.columns

    def test_geology_hydrocarbon_summary(
        self,
        geology_df: pd.DataFrame,
        hc_intervals_df: pd.DataFrame,
    ) -> None:
        analyzer = WellDesignAnalyzer(
            geology_df=geology_df,
            hc_intervals_df=hc_intervals_df,
        )
        result = analyzer.analyze()["geology_analysis"]
        hc = result["hydrocarbon_summary"]
        assert hc is not None
        assert hc["total_intervals"] == 3
        assert hc["by_type"]["O"] == 2
        assert hc["by_type"]["G"] == 1


# -- 6. Pressure envelope ----------------------------------------------------


class TestPressureEnvelope:
    """Verify BOP pressure envelope analysis."""

    def test_pressure_envelope_stats(self, bop_df: pd.DataFrame) -> None:
        analyzer = WellDesignAnalyzer(bop_df=bop_df)
        result = analyzer.analyze()["pressure_envelope"]
        assert result["total_tests"] == 3
        assert result["ram_pressure_stats"]["max"] == pytest.approx(11000.0)
        assert result["annular_pressure_stats"]["max"] == pytest.approx(5500.0)
        assert "mean" in result["ram_pressure_stats"]
        assert "mean" in result["annular_pressure_stats"]


# -- 7. Edge cases ------------------------------------------------------------


class TestEdgeCases:
    """Verify graceful handling of None and partial inputs."""

    def test_all_none_inputs_graceful(self) -> None:
        analyzer = WellDesignAnalyzer()
        result = analyzer.analyze()
        assert set(result.keys()) == _EXPECTED_KEYS
        assert result["casing_program"]["total_casing_records"] == 0
        assert result["completion_analysis"]["total_perforations"] == 0
        assert result["geology_analysis"]["total_markers"] == 0
        assert result["pressure_envelope"]["total_tests"] == 0

    def test_tubulars_only(self, tubulars_df: pd.DataFrame) -> None:
        analyzer = WellDesignAnalyzer(tubulars_df=tubulars_df)
        result = analyzer.analyze()
        assert result["casing_program"]["total_casing_records"] == 5
        assert result["completion_analysis"]["total_perforations"] == 0
        assert result["geology_analysis"]["total_markers"] == 0
        assert result["pressure_envelope"]["total_tests"] == 0
