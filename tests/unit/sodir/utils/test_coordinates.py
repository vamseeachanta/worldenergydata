"""Tests for SODIR coordinate transformation utilities."""

import math

from worldenergydata.sodir.utils.coordinates import CoordinateTransformer


class TestCoordinateTransformerInit:
    def test_initial_state(self):
        ct = CoordinateTransformer()
        assert ct.conversions_count == 0
        assert ct.error_count == 0

    def test_statistics_initial(self):
        ct = CoordinateTransformer()
        stats = ct.get_statistics()
        assert stats["conversions"] == 0
        assert stats["errors"] == 0


class TestUTMZoneCalculation:
    def test_zone_1(self):
        ct = CoordinateTransformer()
        assert ct._calculate_utm_zone(-177) == 1

    def test_zone_31_oslo(self):
        ct = CoordinateTransformer()
        # Oslo ~10.75E -> zone 32
        assert ct._calculate_utm_zone(10.75) == 32

    def test_zone_boundary(self):
        ct = CoordinateTransformer()
        # 0 degrees -> zone 31
        assert ct._calculate_utm_zone(0) == 31

    def test_zone_max(self):
        ct = CoordinateTransformer()
        assert ct._calculate_utm_zone(180) <= 60


class TestUTMtoWGS84Internal:
    def test_known_point_stavanger(self):
        ct = CoordinateTransformer()
        # Stavanger, Norway: approximately 58.97N, 5.73E
        # UTM zone 32: easting ~312000, northing ~6542000
        lat, lon = ct._utm_to_wgs84_internal(312000, 6542000, 32, True)
        assert 58.5 < lat < 59.5
        assert 5.0 < lon < 7.0

    def test_conversions_counted(self):
        ct = CoordinateTransformer()
        ct._utm_to_wgs84_internal(500000, 0, 31, True)
        assert ct.conversions_count == 1

    def test_equator_central_meridian(self):
        ct = CoordinateTransformer()
        # Zone 31 central meridian: 3 degrees E
        # Easting=500000, Northing=0 should be near 0N, 3E
        lat, lon = ct._utm_to_wgs84_internal(500000, 0, 31, True)
        assert abs(lat) < 0.1
        assert abs(lon - 3.0) < 0.1


class TestWGS84toUTMInternal:
    def test_equator(self):
        ct = CoordinateTransformer()
        easting, northing, zone = ct._wgs84_to_utm_internal(0, 3)
        # Zone 31 central meridian = 3E, easting should be ~500000
        assert abs(easting - 500000) < 100
        assert abs(northing) < 100
        assert zone == 31

    def test_norway_stavanger(self):
        ct = CoordinateTransformer()
        easting, northing, zone = ct._wgs84_to_utm_internal(58.97, 5.73)
        # 5.73E falls in zone 31 (0-6 degrees)
        assert zone == 31
        assert 6500000 < northing < 6600000

    def test_southern_hemisphere(self):
        ct = CoordinateTransformer()
        easting, northing, zone = ct._wgs84_to_utm_internal(-33.86, 151.21)
        # Sydney, Australia
        assert northing > 6000000  # False northing added


class TestRoundtrip:
    def test_roundtrip_oslo(self):
        ct = CoordinateTransformer()
        lat_orig, lon_orig = 59.91, 10.75
        easting, northing, zone = ct._wgs84_to_utm_internal(lat_orig, lon_orig)
        lat_back, lon_back = ct._utm_to_wgs84_internal(easting, northing, zone, True)
        assert abs(lat_back - lat_orig) < 0.01
        assert abs(lon_back - lon_orig) < 0.01

    def test_roundtrip_equator(self):
        ct = CoordinateTransformer()
        lat_orig, lon_orig = 0.0, 15.0
        easting, northing, zone = ct._wgs84_to_utm_internal(lat_orig, lon_orig)
        lat_back, lon_back = ct._utm_to_wgs84_internal(easting, northing, zone, True)
        assert abs(lat_back - lat_orig) < 0.01
        assert abs(lon_back - lon_orig) < 0.01


class TestNorwegianCoordinateValidation:
    def test_valid_stavanger(self):
        ct = CoordinateTransformer()
        assert ct.validate_norwegian_coordinates(58.97, 5.73) is True

    def test_valid_tromso(self):
        ct = CoordinateTransformer()
        assert ct.validate_norwegian_coordinates(69.65, 18.96) is True

    def test_invalid_south(self):
        ct = CoordinateTransformer()
        assert ct.validate_norwegian_coordinates(50.0, 10.0) is False

    def test_invalid_north(self):
        ct = CoordinateTransformer()
        assert ct.validate_norwegian_coordinates(75.0, 10.0) is False

    def test_invalid_west(self):
        ct = CoordinateTransformer()
        assert ct.validate_norwegian_coordinates(60.0, -10.0) is False

    def test_invalid_east(self):
        ct = CoordinateTransformer()
        assert ct.validate_norwegian_coordinates(60.0, 40.0) is False

    def test_boundary_values(self):
        ct = CoordinateTransformer()
        # On boundaries should be valid
        assert ct.validate_norwegian_coordinates(56, -5) is True
        assert ct.validate_norwegian_coordinates(72, 35) is True


class TestBatchConversion:
    def test_batch_utm_to_wgs84(self):
        ct = CoordinateTransformer()
        coords = [
            (500000, 0, 31),
            (312000, 6542000, 32),
        ]
        results = ct.batch_utm_to_wgs84(coords)
        assert len(results) == 2
        for lat, lon in results:
            assert lat is not None
            assert lon is not None

    def test_batch_empty(self):
        ct = CoordinateTransformer()
        results = ct.batch_utm_to_wgs84([])
        assert results == []
