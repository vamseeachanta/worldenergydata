"""Tests for wellpath coordinate transformation utilities."""

import math

import pytest

from worldenergydata.common.legacy.wellpath_coordinates import (
    calculate_geographic_position,
    east2lon,
    north2lat,
)


# ---------------------------------------------------------------------------
# north2lat
# ---------------------------------------------------------------------------

class TestNorth2Lat:
    def test_zero_offset(self):
        assert north2lat(0, 29.0) == 29.0

    def test_positive_north(self):
        result = north2lat(1000, 29.0)
        assert result > 29.0

    def test_negative_north(self):
        result = north2lat(-1000, 29.0)
        assert result < 29.0

    def test_large_offset_wraps(self):
        # Northing so large it crosses 90 degrees
        result = north2lat(10000000, 89.0)
        # Should wrap: new_lat = 89 + large number > 90
        # For lat >= 0, if new_lat >= 90: return 180 - new_lat
        assert result < 90

    def test_southern_hemisphere(self):
        result = north2lat(-10000000, -89.0)
        # Should wrap for southern hemisphere
        assert result > -90

    def test_equator(self):
        result = north2lat(111000, 0.0)
        # ~1 degree of latitude ~ 111km
        assert result == pytest.approx(1.0, abs=0.1)


# ---------------------------------------------------------------------------
# east2lon
# ---------------------------------------------------------------------------

class TestEast2Lon:
    def test_zero_offset(self):
        assert east2lon(0, 29.0, -90.0) == -90.0

    def test_positive_east(self):
        result = east2lon(1000, 29.0, -90.0)
        assert result > -90.0

    def test_negative_east(self):
        result = east2lon(-1000, 29.0, -90.0)
        assert result < -90.0

    def test_wraps_past_180(self):
        result = east2lon(10000000, 0.0, 179.0)
        # Should wrap past 180
        assert result < 180

    def test_wraps_past_negative_180(self):
        result = east2lon(-10000000, 0.0, -179.0)
        # Should wrap past -180
        assert result > -180

    def test_at_equator_vs_poles(self):
        # Formula: (east * cos(lat)) / 111120
        # At equator cos(0)=1.0, at 60 deg cos(60)=0.5
        # So at higher latitude the longitude change is SMALLER
        lon_equator = east2lon(1000, 0.0, 0.0)
        lon_high_lat = east2lon(1000, 60.0, 0.0)
        assert lon_equator > lon_high_lat


# ---------------------------------------------------------------------------
# calculate_geographic_position
# ---------------------------------------------------------------------------

class TestCalculateGeographicPosition:
    def test_zero_offsets(self):
        lat, lon, alt = calculate_geographic_position(
            north=0, east=0, tvd=0,
            surface_lat=29.0, surface_lon=-90.0, surface_alt=10.0,
        )
        assert lat == 29.0
        assert lon == -90.0
        assert alt == 10.0

    def test_altitude_decreases_with_tvd(self):
        _, _, alt = calculate_geographic_position(
            north=0, east=0, tvd=1000,
            surface_lat=29.0, surface_lon=-90.0, surface_alt=10.0,
        )
        assert alt == -990.0

    def test_combined_offsets(self):
        lat, lon, alt = calculate_geographic_position(
            north=1000, east=500, tvd=500,
            surface_lat=29.0, surface_lon=-90.0, surface_alt=50.0,
        )
        assert lat > 29.0
        assert lon > -90.0
        assert alt == -450.0

    def test_returns_tuple(self):
        result = calculate_geographic_position(
            north=0, east=0, tvd=0,
            surface_lat=0.0, surface_lon=0.0, surface_alt=0.0,
        )
        assert len(result) == 3
