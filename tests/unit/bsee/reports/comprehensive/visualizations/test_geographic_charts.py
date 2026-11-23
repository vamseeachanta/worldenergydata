"""Tests for geographic_charts visualization module."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from worldenergydata.bsee.reports.comprehensive.visualizations.geographic_charts import (
    FieldBoundary,
    GeographicChart,
    WellLocation,
)

# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestWellLocation:
    def test_required_fields(self):
        wl = WellLocation(
            well_name="Well-A",
            latitude=28.5,
            longitude=-88.5,
            field="Field-1",
            status="Active",
        )
        assert wl.well_name == "Well-A"
        assert wl.production is None
        assert wl.depth is None

    def test_optional_fields(self):
        wl = WellLocation(
            well_name="Well-B",
            latitude=29.0,
            longitude=-89.0,
            field="Field-2",
            status="Producing",
            production=500.0,
            depth=10000.0,
        )
        assert wl.production == 500.0
        assert wl.depth == 10000.0


class TestFieldBoundary:
    def test_init(self):
        fb = FieldBoundary(
            field_name="Field-1",
            coordinates=[(28.0, -88.0), (28.5, -88.5), (28.0, -88.5)],
            area=50.0,
            block_number="BLK-001",
        )
        assert fb.field_name == "Field-1"
        assert len(fb.coordinates) == 3
        assert fb.area == 50.0


# ---------------------------------------------------------------------------
# GeographicChart init
# ---------------------------------------------------------------------------


class TestGeographicChartInit:
    def test_no_token(self):
        chart = GeographicChart()
        assert chart.mapbox_token is None

    def test_with_token(self):
        chart = GeographicChart(mapbox_token="test-token")
        assert chart.mapbox_token == "test-token"


# ---------------------------------------------------------------------------
# create_well_location_map
# ---------------------------------------------------------------------------


class TestCreateWellLocationMap:
    def _make_wells(self):
        return [
            WellLocation("Well-A", 28.5, -88.5, "Field-1", "Active", production=500),
            WellLocation("Well-B", 28.6, -88.6, "Field-1", "Idle"),
            WellLocation("Well-C", 28.7, -88.7, "Field-2", "Abandoned", depth=8000),
        ]

    def test_basic_map(self):
        chart = GeographicChart()
        fig = chart.create_well_location_map(self._make_wells())
        assert isinstance(fig, go.Figure)

    def test_with_center(self):
        chart = GeographicChart()
        fig = chart.create_well_location_map(
            self._make_wells(), center_lat=28.5, center_lon=-88.5
        )
        assert isinstance(fig, go.Figure)

    def test_with_title(self):
        chart = GeographicChart()
        fig = chart.create_well_location_map(self._make_wells(), title="My Map")
        assert isinstance(fig, go.Figure)

    def test_with_boundaries(self):
        chart = GeographicChart()
        boundaries = [
            FieldBoundary(
                "Field-1",
                [(28.4, -88.4), (28.6, -88.4), (28.6, -88.6), (28.4, -88.6)],
                100.0,
                "BLK-001",
            ),
        ]
        fig = chart.create_well_location_map(self._make_wells(), boundaries=boundaries)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_production_density_map
# ---------------------------------------------------------------------------


class TestCreateProductionDensityMap:
    @pytest.mark.skip(
        reason="Source uses deprecated 'titleside' colorbar param in newer plotly"
    )
    def test_basic(self):
        chart = GeographicChart()
        data = pd.DataFrame(
            {
                "latitude": [28.5, 28.6, 28.7, 28.8],
                "longitude": [-88.5, -88.6, -88.7, -88.8],
                "production": [500, 800, 300, 600],
            }
        )
        fig = chart.create_production_density_map(data)
        assert isinstance(fig, go.Figure)

    @pytest.mark.skip(
        reason="Source uses deprecated 'titleside' colorbar param in newer plotly"
    )
    def test_custom_columns(self):
        chart = GeographicChart()
        data = pd.DataFrame(
            {
                "lat": [28.5, 28.6],
                "lon": [-88.5, -88.6],
                "output": [500, 800],
            }
        )
        fig = chart.create_production_density_map(
            data, lat_col="lat", lon_col="lon", value_col="output"
        )
        assert isinstance(fig, go.Figure)

    @pytest.mark.skip(
        reason="Source uses deprecated 'titleside' colorbar param in newer plotly"
    )
    def test_custom_title(self):
        chart = GeographicChart()
        data = pd.DataFrame(
            {
                "latitude": [28.5],
                "longitude": [-88.5],
                "production": [500],
            }
        )
        fig = chart.create_production_density_map(data, title="Density Map")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_field_comparison_map
# ---------------------------------------------------------------------------


class TestCreateFieldComparisonMap:
    def test_basic(self):
        chart = GeographicChart()
        fields = {
            "Field-A": [
                WellLocation("W1", 28.5, -88.5, "Field-A", "Active", production=500),
                WellLocation("W2", 28.6, -88.6, "Field-A", "Producing", production=300),
            ],
            "Field-B": [
                WellLocation("W3", 29.0, -89.0, "Field-B", "Active", production=700),
            ],
        }
        fig = chart.create_field_comparison_map(fields)
        assert isinstance(fig, go.Figure)

    def test_with_boundaries(self):
        chart = GeographicChart()
        fields = {
            "Field-A": [
                WellLocation("W1", 28.5, -88.5, "Field-A", "Active"),
            ],
        }
        boundaries = {
            "Field-A": FieldBoundary(
                "Field-A",
                [(28.4, -88.4), (28.6, -88.4), (28.6, -88.6)],
                80.0,
                "BLK-1",
            ),
        }
        fig = chart.create_field_comparison_map(fields, boundaries=boundaries)
        assert isinstance(fig, go.Figure)

    def test_custom_title(self):
        chart = GeographicChart()
        fields = {
            "F1": [WellLocation("W1", 28.5, -88.5, "F1", "Active")],
        }
        fig = chart.create_field_comparison_map(fields, title="Comparison")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_3d_subsurface_view
# ---------------------------------------------------------------------------


class TestCreate3dSubsurfaceView:
    def test_basic(self):
        chart = GeographicChart()
        wells = [
            {"name": "W1", "x": 100, "y": 200, "depth": 5000},
            {"name": "W2", "x": 300, "y": 400, "depth": 8000},
        ]
        fig = chart.create_3d_subsurface_view(wells)
        assert isinstance(fig, go.Figure)

    def test_with_trajectory(self):
        chart = GeographicChart()
        wells = [
            {
                "name": "W1",
                "x": 100,
                "y": 200,
                "depth": 5000,
                "trajectory": {
                    "x": [100, 110, 120],
                    "y": [200, 210, 220],
                    "z": [0, 2500, 5000],
                },
            },
        ]
        fig = chart.create_3d_subsurface_view(wells)
        assert isinstance(fig, go.Figure)

    def test_custom_title(self):
        chart = GeographicChart()
        wells = [{"name": "W1", "x": 100, "y": 200, "depth": 5000}]
        fig = chart.create_3d_subsurface_view(wells, title="Subsurface")
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_trajectory_comparison
# ---------------------------------------------------------------------------


class TestCreateTrajectoryComparison:
    def test_basic(self):
        chart = GeographicChart()
        wells = [
            {
                "name": "W1",
                "trajectory": {
                    "x": [0, 100, 200],
                    "y": [0, 50, 100],
                    "z": [0, 3000, 6000],
                    "departure": [0, 100, 200],
                    "tvd": [0, 3000, 6000],
                },
            },
            {
                "name": "W2",
                "trajectory": {
                    "x": [0, 150, 300],
                    "y": [0, 75, 150],
                    "z": [0, 4000, 8000],
                    "departure": [0, 150, 300],
                    "tvd": [0, 4000, 8000],
                },
            },
        ]
        fig = chart.create_trajectory_comparison(wells)
        assert isinstance(fig, go.Figure)

    def test_no_trajectory(self):
        chart = GeographicChart()
        wells = [{"name": "W1"}]
        fig = chart.create_trajectory_comparison(wells)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# create_field_infrastructure_map
# ---------------------------------------------------------------------------


class TestCreateFieldInfrastructureMap:
    def test_basic(self):
        chart = GeographicChart()
        infra = {
            "platforms": [
                {"name": "Platform A", "latitude": 28.5, "longitude": -88.5},
            ],
            "pipelines": [
                {
                    "name": "Pipeline 1",
                    "coordinates": {"lat": [28.5, 28.6], "lon": [-88.5, -88.6]},
                    "diameter": "12 inch",
                },
            ],
            "wells": [
                {"name": "Well 1", "latitude": 28.55, "longitude": -88.55},
            ],
        }
        fig = chart.create_field_infrastructure_map(infra)
        assert isinstance(fig, go.Figure)

    def test_platforms_only(self):
        chart = GeographicChart()
        infra = {
            "platforms": [
                {"name": "Platform A", "latitude": 28.5, "longitude": -88.5},
            ],
        }
        fig = chart.create_field_infrastructure_map(infra)
        assert isinstance(fig, go.Figure)

    def test_empty_infrastructure(self):
        chart = GeographicChart()
        fig = chart.create_field_infrastructure_map({})
        assert isinstance(fig, go.Figure)

    def test_custom_title(self):
        chart = GeographicChart()
        infra = {
            "wells": [
                {"name": "W1", "latitude": 28.5, "longitude": -88.5},
            ],
        }
        fig = chart.create_field_infrastructure_map(infra, title="Infrastructure")
        assert isinstance(fig, go.Figure)
