"""Tests for geometry math solvers."""

import math

import pytest

from worldenergydata.common.legacy.math_solvers import Geometry


class TestEuclideanDistance:
    def test_same_point(self):
        g = Geometry()
        assert g._euclidean_distance([0, 0], [0, 0]) == 0.0

    def test_unit_distance(self):
        g = Geometry()
        assert g._euclidean_distance([0, 0], [1, 0]) == 1.0

    def test_diagonal(self):
        g = Geometry()
        d = g._euclidean_distance([0, 0], [3, 4])
        assert d == pytest.approx(5.0)

    def test_3d_distance(self):
        g = Geometry()
        d = g._euclidean_distance([1, 2, 3], [4, 6, 3])
        assert d == pytest.approx(5.0)

    def test_negative_coords(self):
        g = Geometry()
        d = g._euclidean_distance([-1, -1], [2, 3])
        assert d == pytest.approx(5.0)

    def test_dimension_mismatch_raises(self):
        g = Geometry()
        with pytest.raises(ValueError, match="same dimensions"):
            g._euclidean_distance([0, 0], [0, 0, 0])


class TestMaxDistanceForSpatialSets:
    def test_empty_list(self):
        g = Geometry()
        result = g.max_distance_for_spatial_sets([])
        assert result["distance_max"] == 0.0
        assert result["max_pair"] is None

    def test_single_point(self):
        g = Geometry()
        result = g.max_distance_for_spatial_sets([[1, 2]])
        assert result["distance_max"] == 0.0

    def test_two_points(self):
        g = Geometry()
        result = g.max_distance_for_spatial_sets([[0, 0], [3, 4]])
        assert result["distance_max"] == pytest.approx(5.0)
        assert result["distance_min"] == pytest.approx(5.0)
        assert result["max_pair"] == (0, 1)
        assert result["min_pair"] == (0, 1)

    def test_three_points(self):
        g = Geometry()
        points = [[0, 0], [1, 0], [0, 3]]
        result = g.max_distance_for_spatial_sets(points)
        # Max distance: (1,0) to (0,3) = sqrt(1+9) = sqrt(10)
        assert result["distance_max"] == pytest.approx(math.sqrt(10))
        # Min distance: (0,0) to (1,0) = 1
        assert result["distance_min"] == pytest.approx(1.0)

    def test_collinear_points(self):
        g = Geometry()
        points = [[0, 0], [5, 0], [10, 0]]
        result = g.max_distance_for_spatial_sets(points)
        assert result["distance_max"] == pytest.approx(10.0)
        assert result["distance_min"] == pytest.approx(5.0)
