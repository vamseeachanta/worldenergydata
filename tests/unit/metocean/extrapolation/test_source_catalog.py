# ABOUTME: Tests for MetoceanSource catalog and NearestSourceFinder.
# ABOUTME: Verifies catalog size, distance calculations, and parameter filtering.

"""
Tests for worldenergydata.metocean.extrapolation.source_catalog
"""

import math

import pytest

from worldenergydata.metocean.extrapolation.source_catalog import (
    MetoceanSource,
    NearestSourceFinder,
    _build_catalog,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def finder():
    return NearestSourceFinder()


@pytest.fixture
def catalog(finder):
    return finder.list_sources()


# ---------------------------------------------------------------------------
# Catalog content tests
# ---------------------------------------------------------------------------


def test_catalog_has_30_or_more_sources(catalog):
    assert len(catalog) >= 30, f"Expected >= 30 sources, got {len(catalog)}"


def test_catalog_all_sources_are_metocean_source(catalog):
    for src in catalog:
        assert isinstance(src, MetoceanSource)


def test_catalog_sources_have_valid_lat_lon(catalog):
    for src in catalog:
        assert -90.0 <= src.lat <= 90.0, f"{src.name} has invalid lat {src.lat}"
        assert -180.0 <= src.lon <= 180.0, f"{src.name} has invalid lon {src.lon}"


def test_catalog_sources_have_non_empty_parameters(catalog):
    for src in catalog:
        assert len(src.parameters) > 0, f"{src.name} has no parameters"


def test_catalog_contains_ndbc_buoys(catalog):
    ndbc = [s for s in catalog if s.name.startswith("ndbc_")]
    assert len(ndbc) >= 10, f"Expected >= 10 NDBC buoys, got {len(ndbc)}"


def test_catalog_contains_coops_stations(catalog):
    coops = [s for s in catalog if s.name.startswith("coops_")]
    assert len(coops) >= 3, f"Expected >= 3 CO-OPS stations, got {len(coops)}"


def test_catalog_contains_reanalysis_sources(catalog):
    rea = [s for s in catalog if s.source_type == "reanalysis"]
    assert len(rea) >= 2, f"Expected >= 2 reanalysis sources, got {len(rea)}"


def test_catalog_contains_model_sources(catalog):
    mdl = [s for s in catalog if s.source_type == "model"]
    assert len(mdl) >= 2, f"Expected >= 2 model sources, got {len(mdl)}"


def test_catalog_priorities_are_valid(catalog):
    for src in catalog:
        assert src.priority in (
            1,
            2,
            3,
        ), f"{src.name} has unexpected priority {src.priority}"


# ---------------------------------------------------------------------------
# find_nearest tests
# ---------------------------------------------------------------------------


def test_find_nearest_returns_non_empty_list(finder):
    results = finder.find_nearest(28.5, -88.5, n=3)
    assert len(results) > 0


def test_find_nearest_returns_at_most_n_results(finder):
    results = finder.find_nearest(28.5, -88.5, n=5)
    assert len(results) <= 5


def test_find_nearest_results_sorted_by_distance(finder):
    lat, lon = 28.5, -88.5
    results = finder.find_nearest(lat, lon, n=10)
    distances = [finder.distance_km(lat, lon, s.lat, s.lon) for s in results]
    assert distances == sorted(distances)


def test_find_nearest_gom_returns_ndbc_or_reanalysis(finder):
    # GoM location — expect NDBC buoys or reanalysis nearby
    results = finder.find_nearest(27.5, -90.0, n=5)
    source_types = {s.source_type for s in results}
    assert source_types & {
        "buoy",
        "reanalysis",
        "model",
    }, "Expected at least one buoy/reanalysis/model for GoM location"


def test_find_nearest_north_sea_returns_relevant_sources(finder):
    # North Sea location (57N, 2E)
    results = finder.find_nearest(57.0, 2.0, n=5)
    names = [s.name for s in results]
    # Should include met_norway or era5 north_sea or open_meteo
    relevant = [
        n for n in names if "north_sea" in n or "met_norway" in n or "era5" in n
    ]
    assert len(relevant) > 0, f"No relevant North Sea sources found in {names}"


def test_find_nearest_with_n_1(finder):
    results = finder.find_nearest(0.0, 0.0, n=1)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# find_by_parameter tests
# ---------------------------------------------------------------------------


def test_find_by_parameter_hs_returns_sources(finder):
    results = finder.find_by_parameter(28.5, -88.5, "Hs")
    assert len(results) > 0


def test_find_by_parameter_all_results_provide_parameter(finder):
    param = "wind_speed"
    results = finder.find_by_parameter(28.5, -88.5, param)
    for src in results:
        assert param in src.parameters, f"{src.name} does not provide {param}"


def test_find_by_parameter_sorted_by_distance(finder):
    lat, lon = 57.0, 2.0
    results = finder.find_by_parameter(lat, lon, "Hs")
    distances = [finder.distance_km(lat, lon, s.lat, s.lon) for s in results]
    assert distances == sorted(distances)


def test_find_by_parameter_unknown_returns_empty_or_reduced(finder):
    # A parameter that definitely does not exist in catalog
    results = finder.find_by_parameter(28.5, -88.5, "radioactive_foo_bar_xyz")
    assert results == []


def test_find_by_parameter_current_speed(finder):
    results = finder.find_by_parameter(28.5, -88.5, "current_speed")
    assert len(results) > 0


# ---------------------------------------------------------------------------
# distance_km (Haversine) tests
# ---------------------------------------------------------------------------


def test_distance_km_same_point_is_zero(finder):
    d = finder.distance_km(28.5, -88.5, 28.5, -88.5)
    assert d == pytest.approx(0.0, abs=1e-6)


def test_distance_km_known_pair_new_york_london():
    # New York (40.71, -74.01) to London (51.51, -0.13) ≈ 5570 km
    finder = NearestSourceFinder()
    d = finder.distance_km(40.71, -74.01, 51.51, -0.13)
    assert 5400 < d < 5700, f"NY–London distance unexpected: {d:.1f} km"


def test_distance_km_is_symmetric(finder):
    d1 = finder.distance_km(28.5, -88.5, 57.0, 2.0)
    d2 = finder.distance_km(57.0, 2.0, 28.5, -88.5)
    assert d1 == pytest.approx(d2, rel=1e-9)


def test_distance_km_equatorial_degree_is_about_111_km(finder):
    # 1 degree of longitude at equator ≈ 111.32 km
    d = finder.distance_km(0.0, 0.0, 0.0, 1.0)
    assert 110 < d < 113, f"Equatorial degree: {d:.2f} km"
