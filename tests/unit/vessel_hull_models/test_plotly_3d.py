"""Tests for vessel_hull_models.visualization.plotly_3d visualization functions."""

import numpy as np
import plotly.graph_objects as go
import pytest

from worldenergydata.vessel_hull_models.exceptions import VisualizationError
from worldenergydata.vessel_hull_models.geometry.obj_parser import OBJMesh
from worldenergydata.vessel_hull_models.visualization.plotly_3d import (
    create_fleet_comparison,
    create_hull_figure,
)


def _make_mock_mesh():
    """Create a simple box mesh for testing."""
    vertices = np.array([
        [0, 0, 0], [10, 0, 0], [10, 5, 0], [0, 5, 0],
        [0, 0, -3], [10, 0, -3], [10, 5, -3], [0, 5, -3],
    ], dtype=float)
    faces = np.array([
        [0, 1, 2], [0, 2, 3],  # top
        [4, 5, 6], [4, 6, 7],  # bottom
        [0, 1, 5], [0, 5, 4],  # front
        [2, 3, 7], [2, 7, 6],  # back
    ], dtype=int)
    return OBJMesh(vertices=vertices, faces=faces)


# ---------------------------------------------------------------------------
# create_hull_figure
# ---------------------------------------------------------------------------

class TestCreateHullFigure:
    def test_basic(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh)
        assert isinstance(fig, go.Figure)

    def test_color_by_depth(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, color_by="depth")
        assert isinstance(fig, go.Figure)

    def test_color_by_x(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, color_by="x")
        assert isinstance(fig, go.Figure)

    def test_color_by_y(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, color_by="y")
        assert isinstance(fig, go.Figure)

    def test_color_uniform(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, color_by="uniform")
        assert isinstance(fig, go.Figure)

    def test_no_waterline(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, show_waterline=False)
        assert isinstance(fig, go.Figure)

    def test_custom_title(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, title="My Hull")
        assert isinstance(fig, go.Figure)

    def test_custom_dimensions(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, width=800, height=600)
        assert isinstance(fig, go.Figure)

    def test_custom_waterline_z(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, waterline_z=-1.5)
        assert isinstance(fig, go.Figure)

    def test_custom_colorscale(self):
        mesh = _make_mock_mesh()
        fig = create_hull_figure(mesh, colorscale="Plasma")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_fleet_comparison
# ---------------------------------------------------------------------------

class TestCreateFleetComparison:
    def test_empty_raises(self):
        with pytest.raises(VisualizationError, match="No hulls"):
            create_fleet_comparison({})

    def test_single_vessel_with_invalid_path(self):
        # Path doesn't exist, so it should add error annotation
        fig = create_fleet_comparison({"Vessel A": "/nonexistent/hull.obj"})
        assert isinstance(fig, go.Figure)

    def test_custom_title(self):
        fig = create_fleet_comparison(
            {"V1": "/nonexistent/a.obj"},
            title="Custom Fleet",
        )
        assert isinstance(fig, go.Figure)
