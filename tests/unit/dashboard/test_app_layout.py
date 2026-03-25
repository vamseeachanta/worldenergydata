"""
Tests for dashboard Dash app layout and callback logic.

Tests the layout structure and verifies that callback functions return the
correct Plotly figure types.  Dash server is NOT started — callbacks are
invoked as plain Python functions.
"""

import pytest
import plotly.graph_objects as go
import pandas as pd


class TestAppLayout:
    """Structural tests for the Dash app layout."""

    def test_app_has_title(self):
        """App title must be set."""
        from worldenergydata.dashboard.app import app

        assert app.title == "WorldEnergyData Dashboard"

    def test_layout_is_not_none(self):
        """App layout must be defined."""
        from worldenergydata.dashboard.app import app

        assert app.layout is not None

    def test_layout_contains_main_tabs(self):
        """Layout must have an element with id='main-tabs'."""
        from worldenergydata.dashboard.app import app
        from dash import html, dcc

        # Walk component tree looking for main-tabs
        def find_id(component, target_id: str) -> bool:
            if hasattr(component, "id") and component.id == target_id:
                return True
            children = getattr(component, "children", None)
            if children is None:
                return False
            if isinstance(children, (list, tuple)):
                return any(find_id(c, target_id) for c in children)
            return find_id(children, target_id)

        assert find_id(app.layout, "main-tabs"), "main-tabs component not found"

    def test_layout_has_production_tab_id(self):
        """A component with value='tab-production' must exist."""
        from worldenergydata.dashboard.app import app

        def find_value(component, target: str) -> bool:
            if getattr(component, "value", None) == target:
                return True
            children = getattr(component, "children", None)
            if children is None:
                return False
            if isinstance(children, (list, tuple)):
                return any(find_value(c, target) for c in children)
            return find_value(children, target)

        assert find_value(app.layout, "tab-production"), (
            "tab-production value not found in layout"
        )


class TestProductionCallbacks:
    """Tests for update_production_charts callback function."""

    def test_callback_returns_two_figures(self):
        """update_production_charts must return a tuple of two figures."""
        from worldenergydata.dashboard.app import update_production_charts

        result = update_production_charts("ALL")
        assert isinstance(result, tuple) and len(result) == 2

    def test_callback_returns_plotly_figures(self):
        """Both returned values must be Plotly figure objects."""
        from worldenergydata.dashboard.app import update_production_charts

        fig1, fig2 = update_production_charts("ALL")
        assert isinstance(fig1, go.Figure)
        assert isinstance(fig2, go.Figure)

    def test_callback_filters_by_field(self):
        """Selecting a specific field should not raise and should return figures."""
        from worldenergydata.dashboard.app import update_production_charts

        fig1, fig2 = update_production_charts("Mars")
        assert isinstance(fig1, go.Figure)
        assert isinstance(fig2, go.Figure)

    def test_callback_unknown_field_graceful(self):
        """An unknown field name should not raise — returns empty figure gracefully."""
        from worldenergydata.dashboard.app import update_production_charts

        # Should not raise even if no data matches
        fig1, fig2 = update_production_charts("NONEXISTENT_FIELD_XYZ")
        assert isinstance(fig1, go.Figure)
        assert isinstance(fig2, go.Figure)


class TestPlatformMapCallback:
    """Tests for update_platform_map callback function."""

    def test_callback_returns_figure(self):
        """update_platform_map must return a single Plotly Figure."""
        from worldenergydata.dashboard.app import update_platform_map

        fig = update_platform_map("WELL_STATUS")
        assert isinstance(fig, go.Figure)

    def test_callback_water_depth_colouring(self):
        """Colour by WATER_DEPTH should also return a valid figure."""
        from worldenergydata.dashboard.app import update_platform_map

        fig = update_platform_map("WATER_DEPTH")
        assert isinstance(fig, go.Figure)


class TestIncidentHeatmapCallback:
    """Tests for update_incident_heatmap callback function."""

    def test_callback_all_filters_returns_figure(self):
        """Default ALL filters must return a Plotly figure."""
        from worldenergydata.dashboard.app import update_incident_heatmap

        fig = update_incident_heatmap("ALL", "ALL")
        assert isinstance(fig, go.Figure)

    def test_callback_area_filter(self):
        """Filtering by a specific area must return a figure."""
        from worldenergydata.dashboard.app import update_incident_heatmap

        fig = update_incident_heatmap("Mississippi Canyon", "ALL")
        assert isinstance(fig, go.Figure)

    def test_callback_empty_result_graceful(self):
        """Combination that yields no rows must return a figure, not raise."""
        from worldenergydata.dashboard.app import update_incident_heatmap

        fig = update_incident_heatmap("NONEXISTENT_AREA", "NONEXISTENT_OPERATOR")
        assert isinstance(fig, go.Figure)
