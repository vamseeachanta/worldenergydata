"""
Tests for cross-database marine safety correlation analysis.

Covers CrossDatabaseAnalyzer, CrossDatabaseQuery, CrossDatabaseResult
with 25+ test cases verifying data shape, filtering, correlations,
trend analysis, and risk-hotspot computation.
"""

import pandas as pd
import pytest

from worldenergydata.marine_safety.cross_database import (
    CrossDatabaseAnalyzer,
    CrossDatabaseQuery,
    CrossDatabaseResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def analyzer() -> CrossDatabaseAnalyzer:
    return CrossDatabaseAnalyzer()


@pytest.fixture
def full_result(analyzer: CrossDatabaseAnalyzer) -> CrossDatabaseResult:
    """Result from a default (no-filter) query over all 4 sources."""
    return analyzer.query(CrossDatabaseQuery())


@pytest.fixture
def full_data(full_result: CrossDatabaseResult) -> pd.DataFrame:
    return full_result.data


# ---------------------------------------------------------------------------
# CrossDatabaseQuery defaults
# ---------------------------------------------------------------------------


class TestCrossDatabaseQueryDefaults:
    def test_default_sources_includes_all_four(self):
        q = CrossDatabaseQuery()
        assert set(q.sources) == {"maib", "imo", "emsa", "tsb"}

    def test_default_optional_filters_are_none(self):
        q = CrossDatabaseQuery()
        assert q.incident_types is None
        assert q.vessel_types is None
        assert q.start_year is None
        assert q.end_year is None
        assert q.regions is None


# ---------------------------------------------------------------------------
# query() — return type and basic structure
# ---------------------------------------------------------------------------


class TestQueryReturnType:
    def test_query_returns_cross_database_result(self, full_result):
        assert isinstance(full_result, CrossDatabaseResult)

    def test_result_data_is_dataframe(self, full_result):
        assert isinstance(full_result.data, pd.DataFrame)

    def test_result_query_preserved(self, analyzer):
        q = CrossDatabaseQuery()
        result = analyzer.query(q)
        assert result.query is q

    def test_result_total_incidents_matches_dataframe_len(self, full_result):
        assert full_result.total_incidents == len(full_result.data)


# ---------------------------------------------------------------------------
# Schema columns
# ---------------------------------------------------------------------------


class TestSchemaColumns:
    REQUIRED_COLUMNS = [
        "source",
        "incident_id",
        "date",
        "incident_type",
        "vessel_type",
        "region",
        "fatalities",
        "injuries",
        "severity",
        "description",
    ]

    def test_all_required_columns_present(self, full_data):
        for col in self.REQUIRED_COLUMNS:
            assert col in full_data.columns, f"Missing column: {col}"

    def test_fatalities_is_integer_type(self, full_data):
        assert pd.api.types.is_integer_dtype(full_data["fatalities"])

    def test_injuries_is_integer_type(self, full_data):
        assert pd.api.types.is_integer_dtype(full_data["injuries"])

    def test_no_null_incident_ids(self, full_data):
        assert full_data["incident_id"].notna().all()

    def test_no_null_dates(self, full_data):
        assert full_data["date"].notna().all()


# ---------------------------------------------------------------------------
# Dataset size requirements
# ---------------------------------------------------------------------------


class TestDatasetSize:
    def test_total_incidents_at_least_200(self, full_result):
        assert full_result.total_incidents >= 200

    def test_all_four_sources_present(self, full_result):
        assert set(full_result.by_source.keys()) == {"maib", "imo", "emsa", "tsb"}

    def test_each_source_has_at_least_50_incidents(self, full_result):
        for src, count in full_result.by_source.items():
            assert count >= 50, f"{src} has only {count} incidents"

    def test_by_source_counts_match_dataframe_groupby(self, full_result):
        df = full_result.data
        for src, count in full_result.by_source.items():
            actual = int((df["source"] == src).sum())
            assert actual == count, f"{src}: by_source={count}, groupby={actual}"


# ---------------------------------------------------------------------------
# Filtering — sources
# ---------------------------------------------------------------------------


class TestFilterBySources:
    def test_filter_maib_only(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(sources=["maib"]))
        assert set(result.data["source"].unique()) == {"maib"}

    def test_filter_maib_and_imo(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(sources=["maib", "imo"]))
        assert set(result.data["source"].unique()).issubset({"maib", "imo"})

    def test_filter_two_sources_excludes_others(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(sources=["emsa", "tsb"]))
        assert "maib" not in result.data["source"].values
        assert "imo" not in result.data["source"].values

    def test_by_source_only_contains_requested_sources(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(sources=["maib", "imo"]))
        assert set(result.by_source.keys()) == {"maib", "imo"}


# ---------------------------------------------------------------------------
# Filtering — incident types
# ---------------------------------------------------------------------------


class TestFilterByIncidentType:
    def test_filter_collision_only(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(incident_types=["collision"]))
        assert set(result.data["incident_type"].unique()) == {"collision"}

    def test_filter_two_incident_types(self, analyzer):
        result = analyzer.query(
            CrossDatabaseQuery(incident_types=["collision", "grounding"])
        )
        types = set(result.data["incident_type"].unique())
        assert types.issubset({"collision", "grounding"})

    def test_filter_incident_type_reduces_count(self, analyzer, full_result):
        result = analyzer.query(CrossDatabaseQuery(incident_types=["fire"]))
        assert result.total_incidents < full_result.total_incidents


# ---------------------------------------------------------------------------
# Filtering — year range
# ---------------------------------------------------------------------------


class TestFilterByYear:
    def test_start_year_2020_excludes_earlier(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(start_year=2020))
        years = pd.to_datetime(result.data["date"]).dt.year
        assert (years >= 2020).all()

    def test_end_year_2019_excludes_later(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(end_year=2019))
        years = pd.to_datetime(result.data["date"]).dt.year
        assert (years <= 2019).all()

    def test_year_range_combines_start_and_end(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(start_year=2018, end_year=2020))
        years = pd.to_datetime(result.data["date"]).dt.year
        assert (years >= 2018).all()
        assert (years <= 2020).all()


# ---------------------------------------------------------------------------
# Filtering — regions
# ---------------------------------------------------------------------------


class TestFilterByRegion:
    def test_filter_north_sea(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(regions=["north_sea"]))
        assert set(result.data["region"].unique()) == {"north_sea"}

    def test_filter_multiple_regions(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(regions=["north_sea", "atlantic"]))
        assert set(result.data["region"].unique()).issubset({"north_sea", "atlantic"})


# ---------------------------------------------------------------------------
# Combined filters (AND logic)
# ---------------------------------------------------------------------------


class TestCombinedFilters:
    def test_source_and_type_combined(self, analyzer):
        result = analyzer.query(
            CrossDatabaseQuery(sources=["maib"], incident_types=["collision"])
        )
        assert set(result.data["source"].unique()) == {"maib"}
        assert set(result.data["incident_type"].unique()) == {"collision"}

    def test_source_and_year_combined(self, analyzer):
        result = analyzer.query(CrossDatabaseQuery(sources=["tsb"], start_year=2020))
        assert set(result.data["source"].unique()) == {"tsb"}
        years = pd.to_datetime(result.data["date"]).dt.year
        assert (years >= 2020).all()

    def test_three_filters_combined(self, analyzer):
        result = analyzer.query(
            CrossDatabaseQuery(
                sources=["maib", "emsa"],
                incident_types=["grounding"],
                regions=["north_sea"],
            )
        )
        assert set(result.data["source"].unique()).issubset({"maib", "emsa"})
        assert set(result.data["incident_type"].unique()) == {"grounding"}
        assert set(result.data["region"].unique()) == {"north_sea"}

    def test_no_filters_returns_all(self, analyzer, full_result):
        result = analyzer.query(CrossDatabaseQuery())
        assert result.total_incidents == full_result.total_incidents


# ---------------------------------------------------------------------------
# correlations()
# ---------------------------------------------------------------------------


class TestCorrelations:
    REQUIRED_KEYS = [
        "incident_type_severity",
        "vessel_type_region",
        "source_overlap_rate",
        "trend_yoy",
    ]

    def test_correlations_returns_dict(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        assert isinstance(corrs, dict)

    def test_correlations_contains_required_keys(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        for key in self.REQUIRED_KEYS:
            assert key in corrs, f"Missing key: {key}"

    def test_incident_type_severity_is_dataframe(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        assert isinstance(corrs["incident_type_severity"], pd.DataFrame)

    def test_vessel_type_region_is_dataframe(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        assert isinstance(corrs["vessel_type_region"], pd.DataFrame)

    def test_source_overlap_rate_is_float(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        assert isinstance(corrs["source_overlap_rate"], float)

    def test_source_overlap_rate_between_0_and_1(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        rate = corrs["source_overlap_rate"]
        assert 0.0 <= rate <= 1.0

    def test_trend_yoy_is_dataframe(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        assert isinstance(corrs["trend_yoy"], pd.DataFrame)

    def test_trend_yoy_has_year_column(self, analyzer, full_data):
        corrs = analyzer.correlations(full_data)
        assert "year" in corrs["trend_yoy"].columns


# ---------------------------------------------------------------------------
# trend_analysis()
# ---------------------------------------------------------------------------


class TestTrendAnalysis:
    def test_returns_dataframe(self, analyzer, full_data):
        trend = analyzer.trend_analysis(full_data)
        assert isinstance(trend, pd.DataFrame)

    def test_has_year_column(self, analyzer, full_data):
        trend = analyzer.trend_analysis(full_data)
        assert "year" in trend.columns

    def test_has_count_column(self, analyzer, full_data):
        trend = analyzer.trend_analysis(full_data)
        assert "count" in trend.columns

    def test_years_span_expected_range(self, analyzer, full_data):
        trend = analyzer.trend_analysis(full_data)
        assert trend["year"].min() >= 2015
        assert trend["year"].max() <= 2024


# ---------------------------------------------------------------------------
# top_incident_types()
# ---------------------------------------------------------------------------


class TestTopIncidentTypes:
    def test_returns_dataframe(self, analyzer, full_data):
        result = analyzer.top_incident_types(full_data)
        assert isinstance(result, pd.DataFrame)

    def test_default_returns_at_most_ten_rows(self, analyzer, full_data):
        result = analyzer.top_incident_types(full_data)
        assert len(result) <= 10

    def test_custom_n_returns_correct_rows(self, analyzer, full_data):
        result = analyzer.top_incident_types(full_data, n=5)
        assert len(result) == 5

    def test_has_incident_type_column(self, analyzer, full_data):
        result = analyzer.top_incident_types(full_data)
        assert "incident_type" in result.columns

    def test_has_count_column(self, analyzer, full_data):
        result = analyzer.top_incident_types(full_data)
        assert "count" in result.columns

    def test_sorted_descending_by_count(self, analyzer, full_data):
        result = analyzer.top_incident_types(full_data)
        counts = result["count"].tolist()
        assert counts == sorted(counts, reverse=True)


# ---------------------------------------------------------------------------
# risk_hotspots()
# ---------------------------------------------------------------------------


class TestRiskHotspots:
    def test_returns_dataframe(self, analyzer, full_data):
        hotspots = analyzer.risk_hotspots(full_data)
        assert isinstance(hotspots, pd.DataFrame)

    def test_indexed_by_region(self, analyzer, full_data):
        hotspots = analyzer.risk_hotspots(full_data)
        assert hotspots.index.name == "region"

    def test_columns_are_incident_types(self, analyzer, full_data):
        hotspots = analyzer.risk_hotspots(full_data)
        known_types = set(full_data["incident_type"].unique())
        for col in hotspots.columns:
            assert col in known_types

    def test_cell_values_are_non_negative(self, analyzer, full_data):
        hotspots = analyzer.risk_hotspots(full_data)
        assert (hotspots >= 0).all().all()

    def test_north_sea_row_present(self, analyzer, full_data):
        hotspots = analyzer.risk_hotspots(full_data)
        assert "north_sea" in hotspots.index
