"""Tests for wellbore trajectory calculations (Minimum Curvature Method)."""

import math

import pytest

from worldenergydata.common.legacy.wellpath_trajectory import (
    SurveyPoint,
    TrajectoryResult,
    calculate_dogleg,
    calculate_dogleg_severity,
    calculate_minimum_curvature,
    calculate_ratio_factor,
    interpolate_survey_point,
)

# ---------------------------------------------------------------------------
# SurveyPoint
# ---------------------------------------------------------------------------


class TestSurveyPoint:
    def test_named_tuple(self):
        sp = SurveyPoint(
            depth=100.0,
            inc=5.0,
            azi=180.0,
            tvd=99.9,
            north=0.5,
            east=0.0,
            closure=0.5,
            dls=2.0,
        )
        assert sp.depth == 100.0
        assert sp.inc == 5.0


# ---------------------------------------------------------------------------
# calculate_dogleg
# ---------------------------------------------------------------------------


class TestCalculateDogleg:
    def test_same_direction_zero_dogleg(self):
        result = calculate_dogleg(0, 0, 0, 0)
        assert result == 0.0

    def test_vertical_to_inclined(self):
        result = calculate_dogleg(0, 0, 10, 0)
        assert result == pytest.approx(10.0, abs=0.01)

    def test_symmetric(self):
        result1 = calculate_dogleg(10, 0, 20, 0)
        result2 = calculate_dogleg(20, 0, 10, 0)
        assert result1 == pytest.approx(result2, abs=0.001)

    def test_azimuth_change_only(self):
        result = calculate_dogleg(45, 0, 45, 90)
        # With 45 deg inclination, 90 deg azi change -> non-trivial dogleg
        assert result > 0

    def test_180_degree_turn(self):
        result = calculate_dogleg(90, 0, 90, 180)
        assert result == pytest.approx(180.0, abs=0.1)


# ---------------------------------------------------------------------------
# calculate_dogleg_severity
# ---------------------------------------------------------------------------


class TestCalculateDoglegSeverity:
    def test_zero_course_length(self):
        assert calculate_dogleg_severity(5.0, 0) == 0.0

    def test_normalized_to_30m(self):
        # 3 degrees over 30m -> 3 deg/30m
        assert calculate_dogleg_severity(3.0, 30.0) == pytest.approx(3.0)

    def test_longer_course(self):
        # 3 degrees over 60m -> 1.5 deg/30m
        assert calculate_dogleg_severity(3.0, 60.0) == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# calculate_ratio_factor
# ---------------------------------------------------------------------------


class TestCalculateRatioFactor:
    def test_zero_dls(self):
        assert calculate_ratio_factor(0) == 1.0

    def test_small_dls_near_one(self):
        rf = calculate_ratio_factor(0.1)
        assert rf == pytest.approx(1.0, abs=0.01)

    def test_moderate_dls(self):
        rf = calculate_ratio_factor(5.0)
        assert rf > 0.9
        assert rf < 1.1


# ---------------------------------------------------------------------------
# calculate_minimum_curvature
# ---------------------------------------------------------------------------


class TestCalculateMinimumCurvature:
    def test_zero_course_length(self):
        result = calculate_minimum_curvature(
            depth1=100,
            inc1=0,
            azi1=0,
            tvd1=100,
            north1=0,
            east1=0,
            depth2=100,
            inc2=0,
            azi2=0,
        )
        assert result.tvd == 100
        assert result.north == 0
        assert result.east == 0

    def test_negative_course_length(self):
        result = calculate_minimum_curvature(
            depth1=200,
            inc1=0,
            azi1=0,
            tvd1=200,
            north1=0,
            east1=0,
            depth2=100,
            inc2=0,
            azi2=0,
        )
        assert result.tvd == 200

    def test_vertical_well(self):
        result = calculate_minimum_curvature(
            depth1=0,
            inc1=0,
            azi1=0,
            tvd1=0,
            north1=0,
            east1=0,
            depth2=100,
            inc2=0,
            azi2=0,
        )
        # Vertical well: TVD should be close to MD
        assert result.tvd == pytest.approx(100.0, abs=1.0)
        assert abs(result.north) < 1.0
        assert abs(result.east) < 1.0

    def test_inclined_well(self):
        result = calculate_minimum_curvature(
            depth1=0,
            inc1=30,
            azi1=0,
            tvd1=0,
            north1=0,
            east1=0,
            depth2=100,
            inc2=30,
            azi2=0,
        )
        # At 30 deg inclination: TVD ~ MD * cos(30) ~ 86.6
        assert result.tvd == pytest.approx(86.6, abs=2.0)
        # North displacement > 0 (heading north at inc=30)
        assert result.north > 30.0

    def test_returns_trajectory_result(self):
        result = calculate_minimum_curvature(
            depth1=0,
            inc1=0,
            azi1=0,
            tvd1=0,
            north1=0,
            east1=0,
            depth2=100,
            inc2=5,
            azi2=45,
        )
        assert isinstance(result, TrajectoryResult)
        assert hasattr(result, "dls")
        assert hasattr(result, "dogleg")
        assert hasattr(result, "closure")

    def test_closure_distance(self):
        result = calculate_minimum_curvature(
            depth1=0,
            inc1=45,
            azi1=45,
            tvd1=0,
            north1=0,
            east1=0,
            depth2=100,
            inc2=45,
            azi2=45,
        )
        # Closure = sqrt(north^2 + east^2)
        expected_closure = math.sqrt(result.north**2 + result.east**2)
        assert result.closure == pytest.approx(expected_closure, abs=0.1)


# ---------------------------------------------------------------------------
# interpolate_survey_point
# ---------------------------------------------------------------------------


class TestInterpolateSurveyPoint:
    def test_at_upper_point(self):
        inc, azi, tvd, north, east, depth_from = interpolate_survey_point(
            upper_depth=0,
            upper_inc=0,
            upper_azi=0,
            upper_tvd=0,
            upper_north=0,
            upper_east=0,
            lower_depth=100,
            lower_inc=10,
            lower_azi=90,
            target_depth=0,
        )
        assert tvd == 0
        assert north == 0
        assert east == 0
        assert depth_from == 0

    def test_at_midpoint(self):
        inc, azi, tvd, north, east, depth_from = interpolate_survey_point(
            upper_depth=0,
            upper_inc=0,
            upper_azi=0,
            upper_tvd=0,
            upper_north=0,
            upper_east=0,
            lower_depth=100,
            lower_inc=10,
            lower_azi=90,
            target_depth=50,
        )
        assert depth_from == 50
        # Inclination should be between 0 and 10
        assert 0 <= inc <= 10
        # TVD should be less than MD for inclined well
        assert tvd <= 50

    def test_building_inclination(self):
        inc, _, _, _, _, _ = interpolate_survey_point(
            upper_depth=0,
            upper_inc=0,
            upper_azi=0,
            upper_tvd=0,
            upper_north=0,
            upper_east=0,
            lower_depth=100,
            lower_inc=30,
            lower_azi=0,
            target_depth=50,
        )
        # Midpoint inclination ~15 degrees
        assert inc == pytest.approx(15.0, abs=1.0)

    def test_dropping_inclination(self):
        inc, _, _, _, _, _ = interpolate_survey_point(
            upper_depth=0,
            upper_inc=30,
            upper_azi=0,
            upper_tvd=0,
            upper_north=0,
            upper_east=0,
            lower_depth=100,
            lower_inc=0,
            lower_azi=0,
            target_depth=50,
        )
        # Dropping from 30 to 0, at midpoint ~15
        assert inc == pytest.approx(15.0, abs=1.0)

    def test_same_depth_stations(self):
        # Edge case: same depth for upper and lower
        inc, azi, tvd, north, east, depth_from = interpolate_survey_point(
            upper_depth=100,
            upper_inc=0,
            upper_azi=0,
            upper_tvd=100,
            upper_north=0,
            upper_east=0,
            lower_depth=100,
            lower_inc=10,
            lower_azi=90,
            target_depth=100,
        )
        # Should handle zero delta_md without errors
        assert tvd == 100.0
