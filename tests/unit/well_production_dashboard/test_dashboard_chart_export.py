"""Exercise dashboard chart snapshots through real JSON batch exports."""

import ast
import json

import pytest

from worldenergydata.bsee.data.cache import ChunkManager
from worldenergydata.bsee.reports.comprehensive.visualizations.dashboard_builder import (
    ChartConfig,
)
from worldenergydata.well_production_dashboard.well_production import (
    WellDashboardConfig,
    WellProductionDashboard,
)


@pytest.fixture
def dashboard(monkeypatch, tmp_path):
    """Keep the real data-loader caches inside the test's temporary directory."""

    def create_chunk_manager(cache_dir=None):
        return ChunkManager(cache_dir if cache_dir is not None else tmp_path / "chunks")

    for module in ("enhanced.data_refresh_chunked", "refresh.data_refresh_enhanced"):
        monkeypatch.setattr(
            f"worldenergydata.bsee.data.{module}.ChunkManager", create_chunk_manager
        )
    return WellProductionDashboard(
        WellDashboardConfig(
            title="Chart export", enable_verification=False, export_formats=["json"]
        )
    )


@pytest.mark.parametrize("include_charts", [False, True], ids=["empty", "populated"])
def test_default_export_preserves_chart_mapping(dashboard, tmp_path, include_charts):
    """Empty and populated chart snapshots must reach the JSON artifact by ID."""
    if include_charts:
        dashboard.add_chart(
            ChartConfig(
                chart_id="oil_trend",
                chart_type="line",
                title="Oil production",
                data_source="well_data",
                filters=["date_range"],
            )
        )
        dashboard.add_chart(
            ChartConfig(
                chart_id="gas_trend",
                chart_type="bar",
                title="Gas production",
                data_source="well_data",
            )
        )

    results = dashboard.export_dashboard((tmp_path / "dashboard").as_posix())

    assert len(results) == 1
    assert results[0].success, results[0].error_message
    assert results[0].format == "json"
    output = tmp_path / "dashboard.json"
    assert output.is_file()
    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["configuration"]["include_charts"] is True
    if include_charts:
        assert set(exported["charts"]) == {"oil_trend", "gas_trend"}
        assert ast.literal_eval(exported["charts"]["oil_trend"]) == {
            "chart_id": "oil_trend",
            "chart_type": "line",
            "title": "Oil production",
            "data_source": "well_data",
            "update_callback": None,
            "filters": ["date_range"],
        }
        assert ast.literal_eval(exported["charts"]["gas_trend"]) == {
            "chart_id": "gas_trend",
            "chart_type": "bar",
            "title": "Gas production",
            "data_source": "well_data",
            "update_callback": None,
            "filters": None,
        }
    else:
        assert exported["charts"] == {}
