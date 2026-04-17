"""Tests for VesselGIS — GIS integration for heavy vessel dataset."""

import math

import pandas as pd
import pytest

from worldenergydata.marine.vessel_gis import VesselGIS, haversine_nm

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_VESSELS = pd.DataFrame(
    [
        {
            "vessel_id": "V001",
            "name": "Balder",
            "lat": 27.97,
            "lon": -90.55,
            "type": "crane_vessel",
        },
        {
            "vessel_id": "V002",
            "name": "Saipem 7000",
            "lat": 52.0,
            "lon": 4.0,
            "type": "crane_vessel",
        },
    ]
)

MOCK_BSEE_FIELDS = pd.DataFrame(
    [
        {"field_name": "MARS", "lat": 27.97, "lon": -90.55},
        {"field_name": "THUNDER HORSE", "lat": 28.18, "lon": -88.47},
    ]
)


# ---------------------------------------------------------------------------
# haversine_nm unit tests
# ---------------------------------------------------------------------------


class TestHaversineNm:
    def test_haversine_zero_distance(self):
        """Same point should return exactly 0 nm."""
        result = haversine_nm(27.97, -90.55, 27.97, -90.55)
        assert result == 0.0

    def test_haversine_known_distance(self):
        """MARS to THUNDER HORSE: expected approx 107 nm."""
        # MARS: (27.97, -90.55)  THUNDER HORSE: (28.18, -88.47)
        result = haversine_nm(27.97, -90.55, 28.18, -88.47)
        # Allow +/- 2 nm tolerance on known GOM distance
        assert 100.0 < result < 115.0

    def test_haversine_symmetry(self):
        """Distance A->B equals distance B->A."""
        d_ab = haversine_nm(27.97, -90.55, 28.18, -88.47)
        d_ba = haversine_nm(28.18, -88.47, 27.97, -90.55)
        assert abs(d_ab - d_ba) < 1e-6

    def test_haversine_positive(self):
        """Distance is always non-negative."""
        result = haversine_nm(0.0, 0.0, 90.0, 180.0)
        assert result >= 0.0


# ---------------------------------------------------------------------------
# VesselGIS unit tests
# ---------------------------------------------------------------------------


class TestVesselGISQueryByFieldArea:
    def test_query_by_field_area_returns_df(self):
        """query_vessels_by_field_area must return a DataFrame."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.query_vessels_by_field_area("MARS")
        assert isinstance(result, pd.DataFrame)

    def test_query_by_field_area_gom_builtin(self):
        """MARS is in built-in GoM coords; V001 is near MARS center."""
        gis = VesselGIS(MOCK_VESSELS)
        # V001 is at MARS coords, V002 is in North Sea — 50 nm radius
        result = gis.query_vessels_by_field_area("MARS", radius_nm=50.0)
        assert "V001" in result["vessel_id"].values
        assert "V002" not in result["vessel_id"].values

    def test_query_by_field_area_unknown_field_returns_empty(self):
        """Unknown field with no bsee_fields_df returns empty DataFrame."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.query_vessels_by_field_area("NONEXISTENT_FIELD_XYZ")
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_query_with_bsee_fields_integration(self):
        """When bsee_fields_df provided, use its coordinates."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.query_vessels_by_field_area(
            "MARS",
            bsee_fields_df=MOCK_BSEE_FIELDS,
            radius_nm=50.0,
        )
        assert isinstance(result, pd.DataFrame)
        assert "V001" in result["vessel_id"].values

    def test_query_with_bsee_fields_thunder_horse(self):
        """THUNDER HORSE from bsee_fields_df: V001 is ~107 nm away, outside 50 nm."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.query_vessels_by_field_area(
            "THUNDER HORSE",
            bsee_fields_df=MOCK_BSEE_FIELDS,
            radius_nm=50.0,
        )
        # Neither vessel is within 50 nm of THUNDER HORSE coords
        assert isinstance(result, pd.DataFrame)
        assert "V002" not in result["vessel_id"].values


class TestVesselGISQueryByCoords:
    def test_query_by_coords_radius_filter(self):
        """Vessel within radius is returned; vessel outside is excluded."""
        gis = VesselGIS(MOCK_VESSELS)
        # Query near MARS (27.97, -90.55) with 50 nm radius
        result = gis.query_vessels_by_coords(27.97, -90.55, radius_nm=50.0)
        assert "V001" in result["vessel_id"].values
        assert "V002" not in result["vessel_id"].values

    def test_query_by_coords_returns_df(self):
        """Must always return a DataFrame."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.query_vessels_by_coords(0.0, 0.0, radius_nm=1.0)
        assert isinstance(result, pd.DataFrame)

    def test_query_by_coords_distance_column(self):
        """Result includes a distance_nm column."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.query_vessels_by_coords(27.97, -90.55, radius_nm=50.0)
        assert "distance_nm" in result.columns

    def test_query_by_coords_empty_when_no_matches(self):
        """Empty DataFrame returned when no vessels in radius."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.query_vessels_by_coords(0.0, 0.0, radius_nm=1.0)
        assert result.empty


class TestVesselGISVesselsInPolygon:
    def test_vessels_in_polygon_returns_df(self):
        """Must return a DataFrame."""
        gis = VesselGIS(MOCK_VESSELS)
        polygon = [(-91.0, 27.5), (-90.0, 27.5), (-90.0, 28.5), (-91.0, 28.5)]
        result = gis.vessels_in_polygon(polygon)
        assert isinstance(result, pd.DataFrame)

    def test_vessels_in_polygon_filters_correctly(self):
        """V001 (27.97, -90.55) should be inside the GoM bounding box."""
        gis = VesselGIS(MOCK_VESSELS)
        # Box around MARS (lon, lat) order
        polygon = [(-91.0, 27.5), (-90.0, 27.5), (-90.0, 28.5), (-91.0, 28.5)]
        result = gis.vessels_in_polygon(polygon)
        assert "V001" in result["vessel_id"].values
        assert "V002" not in result["vessel_id"].values


class TestVesselGISGetMapData:
    def test_get_vessel_map_data_structure(self):
        """Returns dict with 'type': 'FeatureCollection'."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.get_vessel_map_data()
        assert isinstance(result, dict)
        assert result.get("type") == "FeatureCollection"
        assert "features" in result

    def test_get_vessel_map_data_features_list(self):
        """features key holds a list."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.get_vessel_map_data()
        assert isinstance(result["features"], list)

    def test_get_vessel_map_data_feature_geometry(self):
        """Each feature has geometry with Point type and coordinates."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.get_vessel_map_data()
        for feature in result["features"]:
            assert feature["type"] == "Feature"
            geom = feature["geometry"]
            assert geom["type"] == "Point"
            assert len(geom["coordinates"]) == 2  # [lon, lat]

    def test_get_vessel_map_data_filter_by_ids(self):
        """Passing vessel_ids filters the output."""
        gis = VesselGIS(MOCK_VESSELS)
        result = gis.get_vessel_map_data(vessel_ids=["V001"])
        ids_in_result = [f["properties"]["vessel_id"] for f in result["features"]]
        assert "V001" in ids_in_result
        assert "V002" not in ids_in_result

    def test_get_vessel_map_data_empty_vessels(self):
        """Empty vessel DataFrame still returns valid FeatureCollection."""
        gis = VesselGIS(pd.DataFrame())
        result = gis.get_vessel_map_data()
        assert result["type"] == "FeatureCollection"
        assert result["features"] == []
