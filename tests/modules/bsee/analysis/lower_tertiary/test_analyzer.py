"""Tests for LTAnalyzer — intermediate analysis layer for LT reports.

Run with:
    PYTHONPATH=src /usr/bin/python3 -m pytest \
        tests/modules/bsee/analysis/lower_tertiary/test_analyzer.py -v \
        --override-ini="addopts=-v --tb=short" \
        -W "default::pytest.PytestRemovedIn9Warning"
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.lower_tertiary.analyzer import LTAnalyzer


# -- Fixtures ----------------------------------------------------------------


def _make_mock_config() -> MagicMock:
    """Build a mock LTConfig with subsea/dry-tree fields and article metrics."""
    config = MagicMock()

    type(config).subsea_fields = PropertyMock(return_value={
        "Jack": {
            "area": "WR",
            "blocks": [718],
            "operator": "Chevron",
            "first_oil": 2014,
        },
        "Julia": {
            "area": "WR",
            "blocks": [540],
            "operator": "ExxonMobil",
            "first_oil": 2016,
        },
    })

    type(config).dry_tree_fields = PropertyMock(return_value={
        "Mars": {
            "area": "MC",
            "blocks": [687],
            "operator": "Shell",
            "first_oil": 1996,
        },
    })

    type(config).article_metrics = PropertyMock(return_value={
        "aggregate": {"total_investment_billion": 50},
        "recovery_factors": {"subsea": {"range_pct": [2, 10]}},
        "economics": {"mean_subsea_npv_billion": -1.2},
        "julia_deep_dive": {"oip_billion_bbl": 6},
        "validation_table": {"fields": [{"name": "Julia"}]},
        "source_attribution": "Test",
    })

    type(config).architecture = PropertyMock(return_value={
        "systems": ["TLP"],
    })

    type(config).output_config = PropertyMock(return_value={
        "reports": {
            "part1": {"title": "Test"},
        },
    })

    return config


def _make_mock_war() -> MagicMock:
    """Build a mock LTWarExtractor with field extraction and aggregates."""
    war = MagicMock()

    def _extract_field(name: str) -> pd.DataFrame:
        counts = {"Jack": 10, "Julia": 5, "Mars": 8}
        n = counts.get(name, 0)
        return pd.DataFrame({"row": range(n)}) if n else pd.DataFrame()

    war.extract_field.side_effect = _extract_field

    war.drilling_activity_by_year.return_value = pd.DataFrame({
        "field": ["Jack"],
        "year": [2020],
        "records": [10],
    })

    war.rig_utilization.return_value = pd.DataFrame({
        "rig_name": ["RIG A"],
        "field": ["Jack"],
        "records": [10],
    })

    subsea_df = pd.DataFrame({"row": range(10)})
    dry_tree_df = pd.DataFrame({"row": range(8)})
    war.subsea_vs_drytree_activity.return_value = {
        "subsea": subsea_df,
        "dry_tree": dry_tree_df,
    }

    return war


def _make_mock_legacy() -> MagicMock:
    """Build a mock LegacyProductionLoader with field data."""
    legacy = MagicMock()

    legacy.available_fields.return_value = ["julia"]

    legacy.field_total_rate.return_value = pd.DataFrame({
        "date": pd.to_datetime(["2020-01", "2020-02"]),
        "total_rate": [1000, 1200],
    })

    legacy.load_cumulative.return_value = pd.DataFrame({
        "date": pd.to_datetime(["2020-01", "2020-02"]),
        "value": [10.0, 12.0],
    })

    legacy.load_production_summary.return_value = pd.DataFrame({
        "API12": ["608114001201"],
        "O_CUMMULATIVE_PROD_MMBBL": [5.0],
    })

    return legacy


@pytest.fixture
def mock_config() -> MagicMock:
    return _make_mock_config()


@pytest.fixture
def mock_war() -> MagicMock:
    return _make_mock_war()


@pytest.fixture
def mock_legacy() -> MagicMock:
    return _make_mock_legacy()


@pytest.fixture
def analyzer(mock_config, mock_war, mock_legacy) -> LTAnalyzer:
    return LTAnalyzer(mock_config, mock_war, mock_legacy)


# -- WAR-based methods -------------------------------------------------------


def test_war_summary_table_columns(analyzer: LTAnalyzer) -> None:
    """war_summary_table returns DataFrame with expected columns."""
    df = analyzer.war_summary_table()
    expected = {"field", "area", "records", "category", "operator", "first_oil"}
    assert set(df.columns) == expected


def test_war_summary_table_categories(analyzer: LTAnalyzer) -> None:
    """war_summary_table assigns subsea and dry_tree categories."""
    df = analyzer.war_summary_table()
    categories = set(df["category"])
    assert "subsea" in categories
    assert "dry_tree" in categories


def test_war_summary_table_records_count(analyzer: LTAnalyzer) -> None:
    """war_summary_table reflects record counts from the extractor."""
    df = analyzer.war_summary_table()
    jack_row = df[df["field"] == "Jack"]
    assert jack_row["records"].iloc[0] == 10
    julia_row = df[df["field"] == "Julia"]
    assert julia_row["records"].iloc[0] == 5
    mars_row = df[df["field"] == "Mars"]
    assert mars_row["records"].iloc[0] == 8


def test_drilling_activity_delegates_to_war(
    analyzer: LTAnalyzer, mock_war: MagicMock
) -> None:
    """drilling_activity_by_year delegates to the WAR extractor."""
    result = analyzer.drilling_activity_by_year()
    mock_war.drilling_activity_by_year.assert_called_once()
    assert "field" in result.columns
    assert "year" in result.columns
    assert "records" in result.columns


def test_rig_utilization_delegates_to_war(
    analyzer: LTAnalyzer, mock_war: MagicMock
) -> None:
    """rig_utilization delegates to the WAR extractor."""
    result = analyzer.rig_utilization()
    mock_war.rig_utilization.assert_called_once()
    assert "rig_name" in result.columns


def test_subsea_vs_drytree_comparison_keys(analyzer: LTAnalyzer) -> None:
    """subsea_vs_drytree_comparison returns expected keys."""
    comp = analyzer.subsea_vs_drytree_comparison()
    expected_keys = {
        "subsea_records",
        "dry_tree_records",
        "subsea_fields",
        "dry_tree_fields",
        "activity_data",
    }
    assert set(comp.keys()) == expected_keys
    assert comp["subsea_records"] == 10
    assert comp["dry_tree_records"] == 8
    assert comp["subsea_fields"] == ["Jack", "Julia"]
    assert comp["dry_tree_fields"] == ["Mars"]


# -- Legacy production methods -----------------------------------------------


def test_production_comparison_uses_legacy(
    analyzer: LTAnalyzer, mock_legacy: MagicMock
) -> None:
    """production_comparison loads rate curves for available legacy fields."""
    result = analyzer.production_comparison()
    mock_legacy.available_fields.assert_called_once()
    mock_legacy.field_total_rate.assert_called_once_with("julia")
    assert "julia" in result
    assert list(result["julia"].columns) == ["date", "total_rate"]


def test_cumulative_comparison_computes_totals(
    analyzer: LTAnalyzer, mock_legacy: MagicMock
) -> None:
    """cumulative_comparison groups by date and sums values."""
    result = analyzer.cumulative_comparison()
    mock_legacy.load_cumulative.assert_called_once_with("julia")
    assert "julia" in result
    df = result["julia"]
    assert "date" in df.columns
    assert "cumulative_mmbbl" in df.columns
    assert df["cumulative_mmbbl"].iloc[0] == 10.0
    assert df["cumulative_mmbbl"].iloc[1] == 12.0


def test_well_inventory_uses_legacy(
    analyzer: LTAnalyzer, mock_legacy: MagicMock
) -> None:
    """well_inventory loads production summaries for legacy fields."""
    result = analyzer.well_inventory()
    mock_legacy.load_production_summary.assert_called_once_with("julia")
    assert "julia" in result
    assert "API12" in result["julia"].columns


# -- Article-derived properties (pass-through from YAML) ---------------------


def test_aggregate_metrics_passthrough(analyzer: LTAnalyzer) -> None:
    """aggregate_metrics returns the 'aggregate' section from article_metrics."""
    assert analyzer.aggregate_metrics == {"total_investment_billion": 50}


def test_recovery_factors_passthrough(analyzer: LTAnalyzer) -> None:
    """recovery_factors returns the 'recovery_factors' section."""
    assert analyzer.recovery_factors == {"subsea": {"range_pct": [2, 10]}}


def test_economics_passthrough(analyzer: LTAnalyzer) -> None:
    """economics returns the 'economics' section."""
    assert analyzer.economics == {"mean_subsea_npv_billion": -1.2}


def test_julia_deep_dive_passthrough(analyzer: LTAnalyzer) -> None:
    """julia_deep_dive returns the 'julia_deep_dive' section."""
    assert analyzer.julia_deep_dive == {"oip_billion_bbl": 6}


def test_validation_table_passthrough(analyzer: LTAnalyzer) -> None:
    """validation_table returns the fields list from validation_table."""
    assert analyzer.validation_table == [{"name": "Julia"}]


def test_architecture_data_passthrough(analyzer: LTAnalyzer) -> None:
    """architecture_data returns the architecture section from config."""
    assert analyzer.architecture_data == {"systems": ["TLP"]}


def test_source_attribution_passthrough(analyzer: LTAnalyzer) -> None:
    """source_attribution returns the source_attribution string."""
    assert analyzer.source_attribution == "Test"


def test_report_title(analyzer: LTAnalyzer) -> None:
    """report_title returns the title for a given report key."""
    title = analyzer.report_title("part1")
    assert title == "Test"
