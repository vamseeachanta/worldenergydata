"""Tests for FieldVisualizationModule (WRK-116 Phase 7).

TDD test suite verifying interactive field visualization outputs:
map generation, 3D subsurface view, and well schematics.
"""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.field_visualization import (
    FieldVisualizationModule,
)


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture()
def viz_enriched_df() -> pd.DataFrame:
    """Enriched DataFrame with columns for visualization tests."""
    return pd.DataFrame({
        "API_WELL_NUMBER": ["W001", "W002", "W003", "W004"],
        "RIG_NAME": ["DRILLSHIP A", "DRILLSHIP A", "WIRELINE B", "DRILLSHIP C"],
        "AREA_CODE": ["MC", "MC", "GC", "WR"],
        "BUS_ASC_NAME": ["SHELL", "SHELL", "BP", "CHEVRON"],
        "RIG_TYPE": ["drillship", "drillship", "wireline_unit", "drillship"],
        "ACTIVITY_CATEGORY": ["drilling", "drilling", "intervention", "drilling"],
        "YEAR": [2020, 2021, 2021, 2022],
        "WATER_DEPTH": [4500.0, 4500.0, 3200.0, 7000.0],
        "WATER_DEPTH_CLASS": ["Deep", "Deep", "Deep", "Ultra-deep"],
        "WELL_STATUS": ["COM", "COM", "TA", "DRL"],
    })


@pytest.fixture()
def viz_borehole_df() -> pd.DataFrame:
    """Borehole DataFrame with coordinates."""
    return pd.DataFrame({
        "API_WELL_NUMBER": ["W001", "W002", "W003", "W004"],
        "SURF_LATITUDE": [28.5, 28.6, 27.8, 26.5],
        "SURF_LONGITUDE": [-89.0, -89.1, -90.5, -91.0],
        "BOTM_LATITUDE": [28.48, 28.58, 27.78, 26.48],
        "BOTM_LONGITUDE": [-89.02, -89.12, -90.52, -91.02],
        "BH_TOTAL_MD": [18000.0, 22000.0, 9800.0, 30000.0],
        "WELL_BORE_TVD": [16000.0, 20000.0, 9500.0, 28000.0],
        "WATER_DEPTH": [4500.0, 4500.0, 3200.0, 7000.0],
    })


# -- 1. Map generation -------------------------------------------------------


class TestGenerateMap:
    """Verify Scattermapbox HTML map generation."""

    def test_generate_map_creates_html(
        self,
        viz_enriched_df: pd.DataFrame,
        viz_borehole_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "map.html")
        mod = FieldVisualizationModule(
            enriched_df=viz_enriched_df,
            borehole_df=viz_borehole_df,
        )
        result = mod.generate_map(output)
        assert result == output
        content = open(output).read()
        assert "plotly" in content.lower()

    def test_generate_map_no_coordinates_placeholder(
        self,
        viz_enriched_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "map.html")
        mod = FieldVisualizationModule(enriched_df=viz_enriched_df)
        result = mod.generate_map(output)
        assert result == output
        content = open(output).read()
        assert "no coordinate data" in content.lower()

    def test_map_contains_well_markers(
        self,
        viz_enriched_df: pd.DataFrame,
        viz_borehole_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "map.html")
        mod = FieldVisualizationModule(
            enriched_df=viz_enriched_df,
            borehole_df=viz_borehole_df,
        )
        mod.generate_map(output)
        content = open(output).read()
        assert "SHELL" in content or "W001" in content


# -- 2. 3D view --------------------------------------------------------------


class TestGenerate3dView:
    """Verify Scatter3d HTML generation."""

    def test_generate_3d_view_creates_html(
        self,
        viz_enriched_df: pd.DataFrame,
        viz_borehole_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "view3d.html")
        mod = FieldVisualizationModule(
            enriched_df=viz_enriched_df,
            borehole_df=viz_borehole_df,
        )
        result = mod.generate_3d_view(output)
        assert result == output
        content = open(output).read()
        assert "plotly" in content.lower()

    def test_generate_3d_view_no_data_placeholder(
        self,
        viz_enriched_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "view3d.html")
        mod = FieldVisualizationModule(enriched_df=viz_enriched_df)
        result = mod.generate_3d_view(output)
        assert result == output
        content = open(output).read()
        assert "no 3d data" in content.lower() or "no coordinate" in content.lower()

    def test_3d_view_has_depth_data(
        self,
        viz_enriched_df: pd.DataFrame,
        viz_borehole_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "view3d.html")
        mod = FieldVisualizationModule(
            enriched_df=viz_enriched_df,
            borehole_df=viz_borehole_df,
        )
        mod.generate_3d_view(output)
        content = open(output).read()
        # Depth values from fixture should appear in output
        assert "18000" in content or "22000" in content


# -- 3. Well schematic -------------------------------------------------------


class TestGenerateWellSchematic:
    """Verify SVG well schematic generation."""

    def test_generate_well_schematic_creates_svg(
        self,
        viz_enriched_df: pd.DataFrame,
        viz_borehole_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "well.svg")
        mod = FieldVisualizationModule(
            enriched_df=viz_enriched_df,
            borehole_df=viz_borehole_df,
        )
        result = mod.generate_well_schematic("W001", output)
        assert result == output
        content = open(output).read()
        assert "<svg" in content

    def test_generate_well_schematic_unknown_well(
        self,
        viz_enriched_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "well.svg")
        mod = FieldVisualizationModule(enriched_df=viz_enriched_df)
        result = mod.generate_well_schematic("NONEXISTENT", output)
        assert result == output
        content = open(output).read()
        assert "<svg" in content
        assert "no data" in content.lower()

    def test_schematic_shows_depth(
        self,
        viz_enriched_df: pd.DataFrame,
        viz_borehole_df: pd.DataFrame,
        tmp_path,
    ) -> None:
        output = str(tmp_path / "well.svg")
        mod = FieldVisualizationModule(
            enriched_df=viz_enriched_df,
            borehole_df=viz_borehole_df,
        )
        mod.generate_well_schematic("W001", output)
        content = open(output).read()
        # Should contain water depth or total depth labels
        assert "4500" in content or "18000" in content


# -- 4. Edge cases -----------------------------------------------------------


class TestEdgeCases:
    """Verify graceful handling of empty data."""

    def test_empty_enriched_df_graceful(self, tmp_path) -> None:
        empty_df = pd.DataFrame(columns=[
            "API_WELL_NUMBER", "RIG_NAME", "AREA_CODE", "BUS_ASC_NAME",
            "RIG_TYPE", "ACTIVITY_CATEGORY", "YEAR",
            "WATER_DEPTH", "WATER_DEPTH_CLASS", "WELL_STATUS",
        ])
        mod = FieldVisualizationModule(enriched_df=empty_df)

        map_out = str(tmp_path / "map.html")
        mod.generate_map(map_out)
        assert open(map_out).read()

        view_out = str(tmp_path / "view3d.html")
        mod.generate_3d_view(view_out)
        assert open(view_out).read()

        svg_out = str(tmp_path / "well.svg")
        mod.generate_well_schematic("W001", svg_out)
        assert open(svg_out).read()
