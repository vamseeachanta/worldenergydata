"""Tests for metocean geospatial utilities."""

import math

from worldenergydata.metocean.utils.coordinates import (
    EARTH_RADIUS_KM,
    BoundingBox,
    bbox_contains,
    bbox_expand,
    bearing_between,
    create_grid_points,
    destination_point,
    find_nearest_station,
    haversine_distance,
    normalize_longitude,
)


class TestHaversineDistance:
    def test_same_point(self):
        assert haversine_distance(0, 0, 0, 0) == 0.0

    def test_known_distance(self):
        # New York to London: approximately 5570 km
        dist = haversine_distance(40.7128, -74.0060, 51.5074, -0.1278)
        assert 5550 < dist < 5600

    def test_equator_90_degrees(self):
        # 90 degrees along equator ~ pi/2 * R ~ 10018 km
        dist = haversine_distance(0, 0, 0, 90)
        expected = math.pi / 2 * EARTH_RADIUS_KM
        assert abs(dist - expected) < 1.0

    def test_pole_to_pole(self):
        # North pole to south pole ~ pi * R ~ 20015 km
        dist = haversine_distance(90, 0, -90, 0)
        expected = math.pi * EARTH_RADIUS_KM
        assert abs(dist - expected) < 1.0

    def test_symmetric(self):
        d1 = haversine_distance(10, 20, 30, 40)
        d2 = haversine_distance(30, 40, 10, 20)
        assert abs(d1 - d2) < 0.001


class TestBoundingBox:
    def test_from_tuple(self):
        bb = BoundingBox.from_tuple((-10, 10, -5, 5))
        assert bb.lon_min == -10
        assert bb.lon_max == 10
        assert bb.lat_min == -5
        assert bb.lat_max == 5

    def test_to_tuple(self):
        bb = BoundingBox(lon_min=-10, lon_max=10, lat_min=-5, lat_max=5)
        assert bb.to_tuple() == (-10, 10, -5, 5)

    def test_contains_inside(self):
        bb = BoundingBox(lon_min=-10, lon_max=10, lat_min=-5, lat_max=5)
        assert bb.contains(0, 0) is True

    def test_contains_on_boundary(self):
        bb = BoundingBox(lon_min=-10, lon_max=10, lat_min=-5, lat_max=5)
        assert bb.contains(5, 10) is True

    def test_contains_outside(self):
        bb = BoundingBox(lon_min=-10, lon_max=10, lat_min=-5, lat_max=5)
        assert bb.contains(10, 0) is False

    def test_expand(self):
        bb = BoundingBox(lon_min=0, lon_max=1, lat_min=0, lat_max=1)
        expanded = bb.expand(111.0)  # ~1 degree
        assert expanded.lat_min < bb.lat_min
        assert expanded.lat_max > bb.lat_max
        assert expanded.lon_min < bb.lon_min
        assert expanded.lon_max > bb.lon_max

    def test_center(self):
        bb = BoundingBox(lon_min=-10, lon_max=10, lat_min=-5, lat_max=5)
        lat, lon = bb.center
        assert lat == 0.0
        assert lon == 0.0

    def test_area_km2(self):
        # 1 degree x 1 degree near equator ~ 111 * 111 ~ 12321 km2
        bb = BoundingBox(lon_min=0, lon_max=1, lat_min=0, lat_max=1)
        area = bb.area_km2
        assert 10000 < area < 13000


class TestBboxContains:
    def test_inside(self):
        assert bbox_contains((-10, 10, -5, 5), 0, 0) is True

    def test_outside(self):
        assert bbox_contains((-10, 10, -5, 5), 10, 0) is False


class TestBboxExpand:
    def test_returns_tuple(self):
        result = bbox_expand((-10, 10, -5, 5), 10)
        assert isinstance(result, tuple)
        assert len(result) == 4


class TestFindNearestStation:
    def test_finds_nearest(self):
        class Station:
            def __init__(self, lat, lon, name):
                self.latitude = lat
                self.longitude = lon
                self.name = name

        stations = [
            Station(10, 20, "A"),
            Station(0.1, 0.1, "B"),
            Station(50, 50, "C"),
        ]
        nearest, dist = find_nearest_station(0, 0, stations)
        assert nearest.name == "B"
        assert dist < 20

    def test_empty_stations(self):
        nearest, dist = find_nearest_station(0, 0, [])
        assert nearest is None
        assert dist == float("inf")

    def test_max_distance_exceeded(self):
        class Station:
            def __init__(self, lat, lon):
                self.latitude = lat
                self.longitude = lon

        stations = [Station(50, 50)]
        nearest, dist = find_nearest_station(0, 0, stations, max_distance_km=100)
        assert nearest is None


class TestCreateGridPoints:
    def test_creates_grid(self):
        bbox = (0, 1, 0, 1)
        points = create_grid_points(bbox, 50)
        assert len(points) > 0
        for lat, lon in points:
            assert 0 <= lat <= 1
            assert 0 <= lon <= 1

    def test_single_point(self):
        bbox = (0, 0, 0, 0)
        points = create_grid_points(bbox, 100)
        assert len(points) == 1


class TestNormalizeLongitude:
    def test_within_range(self):
        assert normalize_longitude(90) == 90

    def test_positive_overflow(self):
        assert normalize_longitude(270) == -90

    def test_negative_overflow(self):
        assert normalize_longitude(-270) == 90

    def test_boundary_180(self):
        assert normalize_longitude(180) == 180


class TestBearingBetween:
    def test_north(self):
        # Due north: 0 degrees
        b = bearing_between(0, 0, 10, 0)
        assert abs(b - 0) < 1

    def test_east(self):
        # Due east: 90 degrees
        b = bearing_between(0, 0, 0, 10)
        assert abs(b - 90) < 1

    def test_south(self):
        b = bearing_between(0, 0, -10, 0)
        assert abs(b - 180) < 1

    def test_west(self):
        b = bearing_between(0, 0, 0, -10)
        assert abs(b - 270) < 1


class TestDestinationPoint:
    def test_north_100km(self):
        lat, lon = destination_point(0, 0, 0, 100)
        # 100km north from equator ~ 0.9 degrees
        assert 0.8 < lat < 1.0
        assert abs(lon) < 0.01

    def test_east_equator(self):
        lat, lon = destination_point(0, 0, 90, 111)
        # ~1 degree east
        assert abs(lat) < 0.01
        assert 0.9 < lon < 1.1
