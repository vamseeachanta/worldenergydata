# ABOUTME: Tests for SpatialAssessor — fetch estimation, sheltering, depth proxy.
# ABOUTME: Verifies SpatialContext fields and correction triggers.

"""
Tests for worldenergydata.metocean.extrapolation.spatial
"""

import pytest

from worldenergydata.metocean.extrapolation.source_catalog import (
    MetoceanSource,
    NearestSourceFinder,
)
from worldenergydata.metocean.extrapolation.spatial import (
    CORRECTION_DISTANCE_KM,
    SpatialAssessor,
    SpatialContext,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def assessor():
    return SpatialAssessor()


@pytest.fixture
def finder():
    return NearestSourceFinder()


@pytest.fixture
def nearby_source():
    """A source very close to the GoM target."""
    return MetoceanSource(
        name="ndbc_42001",
        source_type="buoy",
        lat=25.90,
        lon=-89.68,
        coverage_radius_km=200.0,
        parameters=["Hs", "Tp", "wind_speed"],
        priority=1,
        region="gom",
    )


@pytest.fixture
def distant_source():
    """A source far from the GoM target — should trigger correction."""
    return MetoceanSource(
        name="era5_global_0",
        source_type="reanalysis",
        lat=0.0,
        lon=0.0,
        coverage_radius_km=20000.0,
        parameters=["Hs", "Tp", "wind_speed"],
        priority=3,
        region="global",
    )


# ---------------------------------------------------------------------------
# assess() return type tests
# ---------------------------------------------------------------------------


def test_assess_returns_spatial_context(assessor, nearby_source):
    ctx = assessor.assess(28.5, -88.5, nearby_source)
    assert isinstance(ctx, SpatialContext)


def test_assess_target_lat_lon_preserved(assessor, nearby_source):
    ctx = assessor.assess(28.5, -88.5, nearby_source)
    assert ctx.target_lat == 28.5
    assert ctx.target_lon == -88.5


def test_assess_source_preserved(assessor, nearby_source):
    ctx = assessor.assess(28.5, -88.5, nearby_source)
    assert ctx.nearest_source is nearby_source


# ---------------------------------------------------------------------------
# distance_km consistency
# ---------------------------------------------------------------------------


def test_assess_distance_matches_finder(assessor, finder, nearby_source):
    ctx = assessor.assess(28.5, -88.5, nearby_source)
    expected = finder.distance_km(28.5, -88.5, nearby_source.lat, nearby_source.lon)
    assert ctx.distance_km == pytest.approx(expected, rel=1e-6)


def test_assess_distance_positive(assessor, nearby_source):
    ctx = assessor.assess(28.5, -88.5, nearby_source)
    assert ctx.distance_km > 0.0


# ---------------------------------------------------------------------------
# correction_needed flag
# ---------------------------------------------------------------------------


def test_correction_needed_false_for_very_close_same_depth(assessor):
    # Source at same lat/lon with no depth change
    src = MetoceanSource(
        name="test_close",
        source_type="buoy",
        lat=28.5,
        lon=-88.5,
        coverage_radius_km=100.0,
        parameters=["Hs"],
        priority=1,
        region="gom",
    )
    ctx = assessor.assess(28.5, -88.5, src)
    # Zero distance, same water -> no correction needed
    assert ctx.correction_needed is False


def test_correction_needed_true_when_distance_exceeds_threshold(
    assessor, distant_source
):
    ctx = assessor.assess(28.5, -88.5, distant_source)
    assert ctx.distance_km > CORRECTION_DISTANCE_KM
    assert ctx.correction_needed is True


def test_correction_needed_true_for_cross_gom_to_pacific(assessor):
    # Pacific target, GoM source
    src = MetoceanSource(
        name="ndbc_42001",
        source_type="buoy",
        lat=25.9,
        lon=-89.7,
        coverage_radius_km=200.0,
        parameters=["Hs"],
        priority=1,
        region="gom",
    )
    ctx = assessor.assess(20.0, -150.0, src)
    assert ctx.correction_needed is True


# ---------------------------------------------------------------------------
# sheltering_factor tests
# ---------------------------------------------------------------------------


def test_sheltering_factor_returns_value_in_range(assessor):
    sf = assessor.sheltering_factor(28.5, -88.5)
    assert 0.0 <= sf <= 1.0


def test_sheltering_factor_open_ocean_is_1(assessor):
    # Mid-Pacific — open ocean
    sf = assessor.sheltering_factor(20.0, -150.0)
    assert sf == pytest.approx(1.0)


def test_sheltering_factor_gom_less_than_open_ocean(assessor):
    sf_gom = assessor.sheltering_factor(28.5, -88.5)
    sf_open = assessor.sheltering_factor(20.0, -150.0)
    assert sf_gom < sf_open


def test_sheltering_factor_north_sea_less_than_open_ocean(assessor):
    sf_ns = assessor.sheltering_factor(57.0, 2.0)
    sf_open = assessor.sheltering_factor(20.0, -150.0)
    assert sf_ns < sf_open


# ---------------------------------------------------------------------------
# fetch_km tests
# ---------------------------------------------------------------------------


def test_fetch_km_positive(assessor, nearby_source):
    ctx = assessor.assess(28.5, -88.5, nearby_source)
    assert ctx.fetch_km > 0.0


def test_estimate_fetch_positive(assessor):
    fetch = assessor.estimate_fetch(28.5, -88.5)
    assert fetch > 0.0


def test_estimate_fetch_open_ocean_larger_than_gom(assessor):
    fetch_open = assessor.estimate_fetch(20.0, -150.0)
    fetch_gom = assessor.estimate_fetch(28.5, -88.5)
    assert fetch_open > fetch_gom


# ---------------------------------------------------------------------------
# depth_ratio tests
# ---------------------------------------------------------------------------


def test_depth_ratio_positive(assessor, nearby_source):
    ctx = assessor.assess(28.5, -88.5, nearby_source)
    assert ctx.depth_ratio > 0.0


def test_depth_ratio_same_region_near_one(assessor):
    # Both target and source in GoM shallow shelf -> ratio near 1
    src = MetoceanSource(
        name="ndbc_42035",
        source_type="buoy",
        lat=29.23,
        lon=-94.41,
        coverage_radius_km=200.0,
        parameters=["Hs"],
        priority=1,
        region="gom",
    )
    ctx = assessor.assess(28.5, -90.0, src)
    # Both are shelf-GoM — expect ratio ~1.0 (shallow-shallow)
    assert ctx.depth_ratio == pytest.approx(1.0, abs=0.6)
