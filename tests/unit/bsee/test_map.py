"""
Unit tests for the BSEE GoM field production interactive map module.

Tests cover GomFieldMap, FieldMapConfig, FieldRecord, and FoliumGomMap.
Run with:
    PYTHONPATH="src:../assetutilities/src" python3 -m pytest tests/unit/bsee/test_map.py -v --tb=short -o "addopts="
"""

import os

import pytest

plotly = pytest.importorskip("plotly", reason="plotly not installed")
pd = pytest.importorskip("pandas", reason="pandas not installed")

import pandas as pd
import plotly.graph_objects as go

from worldenergydata.bsee.visualization import FieldMapConfig as FieldMapConfigViaInit
from worldenergydata.bsee.visualization import FoliumGomMap as FoliumGomMapViaInit
from worldenergydata.bsee.visualization import GomFieldMap as GomFieldMapViaInit
from worldenergydata.bsee.visualization.field_map import (
    FieldMapConfig,
    FieldRecord,
    GomFieldMap,
)
from worldenergydata.bsee.visualization.folium_map import FoliumGomMap

# ---------------------------------------------------------------------------
# Constants and valid sets
# ---------------------------------------------------------------------------

VALID_ERAS = frozenset(
    ["oligocene", "eocene", "paleocene", "miocene", "pliocene", "unknown"]
)
VALID_STATUSES = frozenset(["producing", "inactive", "decommissioned"])

# GoM bounding box (approximate)
LAT_MIN, LAT_MAX = 25.0, 31.0
LON_MIN, LON_MAX = -96.0, -84.0


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def map_instance():
    return GomFieldMap()


@pytest.fixture(scope="module")
def fields(map_instance):
    return map_instance.load_fields()


@pytest.fixture(scope="module")
def default_fig(map_instance, fields):
    return map_instance.plot(fields=fields)


# ---------------------------------------------------------------------------
# 1. load_fields — catalog integrity
# ---------------------------------------------------------------------------


class TestLoadFields:
    def test_load_fields_returns_list(self, map_instance):
        result = map_instance.load_fields()
        assert isinstance(result, list)

    def test_catalog_has_at_least_40_fields(self, fields):
        assert len(fields) >= 40, f"Expected ≥40 fields, got {len(fields)}"

    def test_all_items_are_field_records(self, fields):
        for f in fields:
            assert isinstance(f, FieldRecord), f"{f} is not a FieldRecord"

    def test_lat_in_gom_bounds(self, fields):
        for f in fields:
            assert (
                LAT_MIN <= f.lat <= LAT_MAX
            ), f"{f.field_name}: lat {f.lat} outside [{LAT_MIN}, {LAT_MAX}]"

    def test_lon_in_gom_bounds(self, fields):
        for f in fields:
            assert (
                LON_MIN <= f.lon <= LON_MAX
            ), f"{f.field_name}: lon {f.lon} outside [{LON_MIN}, {LON_MAX}]"

    def test_geological_era_valid_values(self, fields):
        for f in fields:
            assert (
                f.geological_era in VALID_ERAS
            ), f"{f.field_name}: invalid era '{f.geological_era}'"

    def test_cumulative_oil_nonnegative(self, fields):
        for f in fields:
            assert (
                f.cumulative_oil_bbl >= 0
            ), f"{f.field_name}: negative cum_oil_bbl {f.cumulative_oil_bbl}"

    def test_cumulative_gas_nonnegative(self, fields):
        for f in fields:
            assert f.cumulative_gas_mcf >= 0

    def test_water_depth_positive(self, fields):
        for f in fields:
            assert (
                f.water_depth_m > 0
            ), f"{f.field_name}: non-positive water_depth_m {f.water_depth_m}"

    def test_status_valid_values(self, fields):
        for f in fields:
            assert (
                f.status in VALID_STATUSES
            ), f"{f.field_name}: invalid status '{f.status}'"

    def test_peak_rate_nonnegative(self, fields):
        for f in fields:
            assert f.peak_rate_bopd >= 0

    def test_field_names_unique(self, fields):
        names = [f.field_name for f in fields]
        assert len(names) == len(set(names)), "Duplicate field names found"

    def test_operator_nonempty(self, fields):
        for f in fields:
            assert f.operator and isinstance(f.operator, str)

    def test_first_production_year_plausible(self, fields):
        producing = [
            f
            for f in fields
            if f.status == "producing" and f.first_production_year < 2050
        ]
        for f in producing:
            assert (
                1950 <= f.first_production_year <= 2030
            ), f"{f.field_name}: year {f.first_production_year} out of range"


# ---------------------------------------------------------------------------
# 2. Named fields present
# ---------------------------------------------------------------------------


class TestNamedFieldsPresent:
    def _field_names(self, fields):
        return {f.field_name for f in fields}

    def test_deep_water_atlantis_present(self, fields):
        assert "Atlantis" in self._field_names(fields)

    def test_deep_water_thunder_horse_present(self, fields):
        assert "Thunder Horse" in self._field_names(fields)

    def test_deep_water_mars_present(self, fields):
        assert "Mars" in self._field_names(fields)

    def test_lower_tertiary_tiber_present(self, fields):
        assert "Tiber" in self._field_names(fields)

    def test_lower_tertiary_anchor_present(self, fields):
        assert "Anchor" in self._field_names(fields)

    def test_lower_tertiary_jack_present(self, fields):
        assert "Jack" in self._field_names(fields)

    def test_lower_tertiary_st_malo_present(self, fields):
        assert "St. Malo" in self._field_names(fields)

    def test_deep_water_gt_300m_includes_atlantis(self, fields):
        deep = [f for f in fields if f.water_depth_m > 300]
        names = {f.field_name for f in deep}
        assert "Atlantis" in names

    def test_deep_water_gt_300m_includes_thunder_horse(self, fields):
        deep = [f for f in fields if f.water_depth_m > 300]
        names = {f.field_name for f in deep}
        assert "Thunder Horse" in names


# ---------------------------------------------------------------------------
# 3. plot() — Plotly figure output
# ---------------------------------------------------------------------------


class TestPlot:
    def test_plot_returns_figure(self, default_fig):
        assert isinstance(default_fig, go.Figure)

    def test_figure_has_at_least_one_trace(self, default_fig):
        assert len(default_fig.data) >= 1

    def test_plot_with_color_by_operator(self, map_instance, fields):
        cfg = FieldMapConfig(color_by="operator")
        fig = map_instance.plot(fields=fields, config=cfg)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1

    def test_plot_with_color_by_water_depth(self, map_instance, fields):
        cfg = FieldMapConfig(color_by="water_depth")
        fig = map_instance.plot(fields=fields, config=cfg)
        assert isinstance(fig, go.Figure)

    def test_plot_with_color_by_production(self, map_instance, fields):
        cfg = FieldMapConfig(color_by="production")
        fig = map_instance.plot(fields=fields, config=cfg)
        assert isinstance(fig, go.Figure)

    def test_plot_with_size_by_uniform(self, map_instance, fields):
        cfg = FieldMapConfig(size_by="uniform")
        fig = map_instance.plot(fields=fields, config=cfg)
        assert isinstance(fig, go.Figure)

    def test_plot_no_args_uses_catalog(self, map_instance):
        fig = map_instance.plot()
        assert isinstance(fig, go.Figure)

    def test_figure_layout_has_title(self, default_fig):
        assert default_fig.layout.title.text is not None

    def test_figure_trace_has_lat_data(self, default_fig):
        trace = default_fig.data[0]
        assert hasattr(trace, "lat") and trace.lat is not None

    def test_figure_trace_has_lon_data(self, default_fig):
        trace = default_fig.data[0]
        assert hasattr(trace, "lon") and trace.lon is not None


# ---------------------------------------------------------------------------
# 4. plot_production_timeline()
# ---------------------------------------------------------------------------


class TestPlotProductionTimeline:
    def test_returns_figure(self, map_instance):
        fig = map_instance.plot_production_timeline("Atlantis")
        assert isinstance(fig, go.Figure)

    def test_timeline_has_trace(self, map_instance):
        fig = map_instance.plot_production_timeline("Atlantis")
        assert len(fig.data) >= 1

    def test_timeline_with_custom_df(self, map_instance):
        df = pd.DataFrame({"year": [2010, 2015, 2020], "oil_bbl": [1e6, 8e5, 6e5]})
        fig = map_instance.plot_production_timeline("Mars", production_df=df)
        assert isinstance(fig, go.Figure)

    def test_timeline_xaxis_title_set(self, map_instance):
        fig = map_instance.plot_production_timeline("Thunder Horse")
        assert fig.layout.xaxis.title.text is not None

    def test_timeline_unknown_field_returns_figure(self, map_instance):
        fig = map_instance.plot_production_timeline("NonExistentField")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# 5. export_html()
# ---------------------------------------------------------------------------


class TestExportHtml:
    def test_export_creates_file(self, map_instance, default_fig, tmp_path):
        out = str(tmp_path / "test_map.html")
        returned = map_instance.export_html(default_fig, out)
        assert os.path.exists(returned)

    def test_export_returns_html_path(self, map_instance, default_fig, tmp_path):
        out = str(tmp_path / "output.html")
        returned = map_instance.export_html(default_fig, out)
        assert returned.endswith(".html")

    def test_export_appends_html_extension(self, map_instance, default_fig, tmp_path):
        out = str(tmp_path / "no_ext")
        returned = map_instance.export_html(default_fig, out)
        assert returned.endswith(".html")
        assert os.path.exists(returned)

    def test_exported_file_nonempty(self, map_instance, default_fig, tmp_path):
        out = str(tmp_path / "map.html")
        returned = map_instance.export_html(default_fig, out)
        assert os.path.getsize(returned) > 0


# ---------------------------------------------------------------------------
# 6. field_summary_table()
# ---------------------------------------------------------------------------


class TestFieldSummaryTable:
    def test_returns_dataframe(self, map_instance):
        df = map_instance.field_summary_table()
        assert isinstance(df, pd.DataFrame)

    def test_has_expected_columns(self, map_instance):
        df = map_instance.field_summary_table()
        for col in ["field", "operator", "era", "cum_oil_mmbbl", "status"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_one_row_per_field(self, map_instance, fields):
        df = map_instance.field_summary_table(fields=fields)
        assert len(df) == len(fields)

    def test_cum_oil_mmbbl_nonnegative(self, map_instance):
        df = map_instance.field_summary_table()
        assert (df["cum_oil_mmbbl"] >= 0).all()

    def test_filter_producing_fields(self, map_instance, fields):
        producing = [f for f in fields if f.status == "producing"]
        df = map_instance.field_summary_table(fields=producing)
        assert (df["status"] == "producing").all()

    def test_no_null_field_names(self, map_instance):
        df = map_instance.field_summary_table()
        assert df["field"].notna().all()


# ---------------------------------------------------------------------------
# 7. FieldMapConfig defaults
# ---------------------------------------------------------------------------


class TestFieldMapConfig:
    def test_default_color_by(self):
        cfg = FieldMapConfig()
        assert cfg.color_by == "geological_era"

    def test_default_size_by(self):
        cfg = FieldMapConfig()
        assert cfg.size_by == "cumulative_oil_bbl"

    def test_default_mapbox_style(self):
        cfg = FieldMapConfig()
        assert cfg.mapbox_style == "open-street-map"

    def test_default_show_contours_false(self):
        cfg = FieldMapConfig()
        assert cfg.show_water_depth_contours is False

    def test_title_is_string(self):
        cfg = FieldMapConfig()
        assert isinstance(cfg.title, str) and len(cfg.title) > 0

    def test_custom_config_overrides(self):
        cfg = FieldMapConfig(color_by="operator", size_by="uniform", title="Test")
        assert cfg.color_by == "operator"
        assert cfg.size_by == "uniform"
        assert cfg.title == "Test"


# ---------------------------------------------------------------------------
# 8. FieldRecord dataclass
# ---------------------------------------------------------------------------


class TestFieldRecord:
    def test_field_record_all_attributes_present(self):
        fr = FieldRecord(
            field_name="TestField",
            lat=27.0,
            lon=-90.0,
            water_depth_m=1000.0,
            geological_era="miocene",
            operator="TestOp",
            cumulative_oil_bbl=1e8,
            cumulative_gas_mcf=2e8,
            peak_rate_bopd=50_000,
            first_production_year=2005,
            status="producing",
        )
        assert fr.field_name == "TestField"
        assert fr.lat == 27.0
        assert fr.lon == -90.0
        assert fr.water_depth_m == 1000.0
        assert fr.geological_era == "miocene"
        assert fr.operator == "TestOp"
        assert fr.cumulative_oil_bbl == 1e8
        assert fr.cumulative_gas_mcf == 2e8
        assert fr.peak_rate_bopd == 50_000
        assert fr.first_production_year == 2005
        assert fr.status == "producing"


# ---------------------------------------------------------------------------
# 9. FoliumGomMap — graceful fallback
# ---------------------------------------------------------------------------


class TestFoliumGomMap:
    def test_plot_returns_nonnone_or_graceful(self):
        fmap = FoliumGomMap()
        result = fmap.plot()
        # Either a folium map object or None if folium not installed
        assert result is None or result is not None

    def test_plot_with_explicit_fields(self, fields):
        fmap = FoliumGomMap()
        result = fmap.plot(fields=fields)
        # Graceful: None when folium absent, folium.Map otherwise
        assert result is None or hasattr(result, "save")

    def test_export_html_works_when_folium_available(self, fields, tmp_path):
        try:
            import folium
        except ImportError:
            pytest.skip("folium not installed")
        fmap = FoliumGomMap()
        result = fmap.plot(fields=fields)
        out = str(tmp_path / "folium_map.html")
        returned = fmap.export_html(result, out)
        assert returned.endswith(".html") and os.path.exists(returned)


# ---------------------------------------------------------------------------
# 10. __init__ re-exports
# ---------------------------------------------------------------------------


class TestModuleExports:
    def test_gom_field_map_importable_from_init(self):
        assert GomFieldMapViaInit is GomFieldMap

    def test_field_map_config_importable_from_init(self):
        assert FieldMapConfigViaInit is FieldMapConfig

    def test_folium_gom_map_importable_from_init(self):
        assert FoliumGomMapViaInit is FoliumGomMap
