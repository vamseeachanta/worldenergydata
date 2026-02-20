"""Tests for LNG terminal queryable API (LngTerminalClient / LngTerminalQuery)."""
import pytest
import pandas as pd

from worldenergydata.lng_terminals.query import (
    LngTerminalClient,
    LngTerminalQuery,
    LngTerminalResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> LngTerminalClient:
    return LngTerminalClient()


@pytest.fixture()
def all_result(client: LngTerminalClient) -> LngTerminalResult:
    return client.query(LngTerminalQuery())


# ---------------------------------------------------------------------------
# Basic query contract
# ---------------------------------------------------------------------------


def test_query_returns_lng_terminal_result(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery())
    assert isinstance(result, LngTerminalResult)


def test_result_data_is_dataframe(all_result: LngTerminalResult) -> None:
    assert isinstance(all_result.data, pd.DataFrame)


def test_result_has_all_required_columns(all_result: LngTerminalResult) -> None:
    required = {
        "terminal_name",
        "country",
        "region",
        "type",
        "status",
        "capacity_mtpa",
        "operator",
        "year_commissioned",
        "latitude",
        "longitude",
        "source",
    }
    assert required.issubset(set(all_result.data.columns))


def test_dataset_has_at_least_40_terminals(all_result: LngTerminalResult) -> None:
    assert all_result.total_count >= 40


def test_total_count_matches_dataframe_length(all_result: LngTerminalResult) -> None:
    assert all_result.total_count == len(all_result.data)


def test_total_capacity_matches_sum_of_data_column(
    all_result: LngTerminalResult,
) -> None:
    expected = float(all_result.data["capacity_mtpa"].sum())
    assert abs(all_result.total_capacity_mtpa - expected) < 1e-6


def test_result_query_field_is_populated(client: LngTerminalClient) -> None:
    q = LngTerminalQuery()
    result = client.query(q)
    assert result.query is q


def test_empty_query_returns_all_terminals(
    client: LngTerminalClient, all_result: LngTerminalResult
) -> None:
    """Two separate empty queries should return the same row count."""
    second = client.query(LngTerminalQuery())
    assert second.total_count == all_result.total_count


# ---------------------------------------------------------------------------
# LngTerminalQuery dataclass defaults
# ---------------------------------------------------------------------------


def test_query_defaults_are_all_none() -> None:
    q = LngTerminalQuery()
    assert q.region is None
    assert q.country is None
    assert q.terminal_type is None
    assert q.status is None
    assert q.min_capacity_mtpa is None
    assert q.max_capacity_mtpa is None


# ---------------------------------------------------------------------------
# Region filter
# ---------------------------------------------------------------------------


def test_filter_by_single_region(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(region=["asia_pacific"]))
    assert result.total_count > 0
    assert all(result.data["region"] == "asia_pacific")


def test_filter_by_region_excludes_others(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(region=["europe"]))
    assert set(result.data["region"]) == {"europe"}


def test_filter_by_multiple_regions(client: LngTerminalClient) -> None:
    result = client.query(
        LngTerminalQuery(region=["north_america", "middle_east"])
    )
    assert result.total_count > 0
    assert set(result.data["region"]).issubset({"north_america", "middle_east"})


def test_filter_by_unknown_region_returns_empty(
    client: LngTerminalClient,
) -> None:
    result = client.query(LngTerminalQuery(region=["nonexistent_region"]))
    assert result.total_count == 0


# ---------------------------------------------------------------------------
# Country filter
# ---------------------------------------------------------------------------


def test_filter_by_country(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(country=["US"]))
    assert result.total_count > 0
    assert all(result.data["country"] == "US")


def test_filter_by_country_case_insensitive(client: LngTerminalClient) -> None:
    upper = client.query(LngTerminalQuery(country=["US"]))
    lower = client.query(LngTerminalQuery(country=["us"]))
    assert upper.total_count == lower.total_count


def test_filter_by_multiple_countries(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(country=["US", "AU"]))
    assert set(result.data["country"]).issubset({"US", "AU"})


# ---------------------------------------------------------------------------
# Type filter
# ---------------------------------------------------------------------------


def test_filter_by_type_import(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(terminal_type=["import"]))
    assert result.total_count > 0
    assert all(result.data["type"] == "import")


def test_filter_by_type_export(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(terminal_type=["export"]))
    assert result.total_count > 0
    assert all(result.data["type"] == "export")


def test_filter_by_type_import_excludes_export(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(terminal_type=["import"]))
    assert "export" not in result.data["type"].values


# ---------------------------------------------------------------------------
# Status filter
# ---------------------------------------------------------------------------


def test_filter_by_status_operational(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(status=["operational"]))
    assert result.total_count > 0
    assert all(result.data["status"] == "operational")


def test_filter_by_status_under_construction(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(status=["under_construction"]))
    assert result.total_count > 0
    assert all(result.data["status"] == "under_construction")


# ---------------------------------------------------------------------------
# Capacity filter
# ---------------------------------------------------------------------------


def test_filter_by_min_capacity(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(min_capacity_mtpa=10.0))
    assert result.total_count > 0
    assert all(result.data["capacity_mtpa"] >= 10.0)


def test_filter_by_max_capacity(client: LngTerminalClient) -> None:
    result = client.query(LngTerminalQuery(max_capacity_mtpa=5.0))
    assert result.total_count > 0
    assert all(result.data["capacity_mtpa"] <= 5.0)


def test_filter_by_min_and_max_capacity(client: LngTerminalClient) -> None:
    result = client.query(
        LngTerminalQuery(min_capacity_mtpa=5.0, max_capacity_mtpa=15.0)
    )
    assert result.total_count > 0
    assert all(result.data["capacity_mtpa"] >= 5.0)
    assert all(result.data["capacity_mtpa"] <= 15.0)


def test_impossible_capacity_range_returns_empty(
    client: LngTerminalClient,
) -> None:
    result = client.query(
        LngTerminalQuery(min_capacity_mtpa=1000.0, max_capacity_mtpa=0.1)
    )
    assert result.total_count == 0


# ---------------------------------------------------------------------------
# list_regions / list_countries
# ---------------------------------------------------------------------------


def test_list_regions_returns_non_empty_list(client: LngTerminalClient) -> None:
    regions = client.list_regions()
    assert isinstance(regions, list)
    assert len(regions) > 0


def test_list_regions_contains_expected_regions(client: LngTerminalClient) -> None:
    regions = client.list_regions()
    assert "asia_pacific" in regions
    assert "europe" in regions
    assert "north_america" in regions


def test_list_countries_returns_non_empty_list(client: LngTerminalClient) -> None:
    countries = client.list_countries()
    assert isinstance(countries, list)
    assert len(countries) > 0


def test_list_countries_contains_expected_countries(
    client: LngTerminalClient,
) -> None:
    countries = client.list_countries()
    assert "US" in countries
    assert "AU" in countries


# ---------------------------------------------------------------------------
# summary_by_region
# ---------------------------------------------------------------------------


def test_summary_by_region_returns_dataframe(client: LngTerminalClient) -> None:
    summary = client.summary_by_region()
    assert isinstance(summary, pd.DataFrame)


def test_summary_by_region_has_required_columns(
    client: LngTerminalClient,
) -> None:
    summary = client.summary_by_region()
    assert {"region", "count", "total_capacity_mtpa"}.issubset(set(summary.columns))


def test_summary_by_region_count_sums_to_total(
    client: LngTerminalClient, all_result: LngTerminalResult
) -> None:
    summary = client.summary_by_region()
    assert int(summary["count"].sum()) == all_result.total_count
