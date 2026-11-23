"""Tests for Texas RRC infrastructure spatial screening helpers."""

from __future__ import annotations

import math


def test_haversine_distance_uses_miles_for_texas_scale():
    from worldenergydata.texas_rrc.infrastructure.spatial import haversine_miles

    distance = haversine_miles(31.0, -102.0, 31.1, -102.0)

    assert distance == pytest_approx(6.91, abs=0.08)


def test_point_to_pipeline_distance_uses_polyline_segments():
    from worldenergydata.texas_rrc.infrastructure.spatial import (
        point_to_polyline_distance_miles,
    )

    distance = point_to_polyline_distance_miles(
        latitude=31.05,
        longitude=-102.05,
        coordinates=((-102.0, 31.0), (-102.0, 31.1)),
    )

    assert distance == pytest_approx(2.96, abs=0.10)


def test_field_bounds_and_extent_are_deterministic():
    from worldenergydata.texas_rrc.infrastructure.spatial import field_geometry

    geometry = field_geometry(((31.0, -102.0), (31.1, -102.1), (30.9, -101.9)))

    assert geometry.well_count == 3
    assert geometry.centroid_latitude == pytest_approx(31.0, abs=0.000001)
    assert geometry.centroid_longitude == pytest_approx(-102.0, abs=0.000001)
    assert geometry.latitude_min == 30.9
    assert geometry.latitude_max == 31.1
    assert geometry.longitude_min == -102.1
    assert geometry.longitude_max == -101.9
    assert geometry.extent_miles > 18.0


def test_field_extent_uses_bounds_instead_of_pairwise_distances(monkeypatch):
    import worldenergydata.texas_rrc.infrastructure.spatial as spatial

    calls = {"total": 0}

    def fake_haversine(latitude_a, longitude_a, latitude_b, longitude_b):
        calls["total"] += 1
        return 10.0

    monkeypatch.setattr(spatial, "haversine_miles", fake_haversine)

    points = tuple(
        (31.0 + index * 0.001, -102.0 - index * 0.001) for index in range(20)
    )
    geometry = spatial.field_geometry(points)

    assert geometry.extent_miles == 10.0
    assert calls["total"] == 1


def test_candidate_pipeline_prefilter_prefers_county_then_bbox():
    from worldenergydata.texas_rrc.infrastructure.gis_sources import PipelineGisRecord
    from worldenergydata.texas_rrc.infrastructure.spatial import (
        field_geometry,
        filter_candidate_pipelines,
    )

    local = PipelineGisRecord(
        pipeline_identifier="near",
        county_fips="001",
        coordinates=((-102.0, 31.0), (-102.0, 31.1)),
        source_file="pipeline001.zip",
    )
    wrong_county = PipelineGisRecord(
        pipeline_identifier="wrong-county",
        county_fips="003",
        coordinates=((-102.01, 31.0), (-102.01, 31.1)),
        source_file="pipeline003.zip",
    )
    no_county_far = PipelineGisRecord(
        pipeline_identifier="far",
        county_fips=None,
        coordinates=((-100.0, 31.0), (-100.0, 31.1)),
        source_file="pipeline000.zip",
    )

    candidates = filter_candidate_pipelines(
        geometry=field_geometry(((31.02, -102.02),)),
        field_counties={"001"},
        pipelines=(local, wrong_county, no_county_far),
        padding_miles=10.0,
    )

    assert tuple(item.pipeline_identifier for item in candidates) == ("near",)


def test_nearest_pipeline_handles_no_candidates():
    from worldenergydata.texas_rrc.infrastructure.spatial import nearest_pipeline

    nearest = nearest_pipeline(field_points=((31.0, -102.0),), pipelines=())

    assert nearest is None


def pytest_approx(value: float, abs: float):  # noqa: A002 - mirrors pytest API
    import pytest

    if not math.isfinite(value):
        raise AssertionError("expected finite comparison value")
    return pytest.approx(value, abs=abs)
