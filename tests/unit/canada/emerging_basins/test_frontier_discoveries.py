"""Tests for the curated frontier-basin discovery dataset + loader (issue #603)."""

from __future__ import annotations

import pytest

from worldenergydata.canada.emerging_basins import (
    DiscoverySchema,
    FrontierDiscoveryLoader,
)

EXPECTED_COUNTRIES = {"Guyana", "Suriname", "Namibia"}

# A few anchor discoveries that must always be present.
EXPECTED_DISCOVERIES = {
    "Liza",  # Guyana Stabroek
    "Yellowtail",
    "Maka Central-1",  # Suriname Block 58
    "Sapakara South",
    "Krabdagu-1",
    "Venus-1X",  # Namibia Orange Basin
    "Graff-1",
    "Mopane",
}


@pytest.fixture(scope="module")
def records() -> list[DiscoverySchema]:
    return FrontierDiscoveryLoader().all()


# --- Schema-level tests ---


def test_schema_requires_core_fields() -> None:
    with pytest.raises(ValueError):
        DiscoverySchema(
            DISCOVERY_NAME="", BLOCK="X", COUNTRY="Guyana", BASIN="b", OPERATOR="op"
        )


def test_schema_rejects_bad_country() -> None:
    with pytest.raises(ValueError):
        DiscoverySchema(
            DISCOVERY_NAME="X", BLOCK="X", COUNTRY="Brazil", BASIN="b", OPERATOR="op"
        )


def test_schema_rejects_bad_tier() -> None:
    with pytest.raises(ValueError):
        DiscoverySchema(
            DISCOVERY_NAME="X",
            BLOCK="X",
            COUNTRY="Guyana",
            BASIN="b",
            OPERATOR="op",
            CONFIDENCE_TIER="gold",
        )


def test_schema_rejects_bad_status() -> None:
    with pytest.raises(ValueError):
        DiscoverySchema(
            DISCOVERY_NAME="X",
            BLOCK="X",
            COUNTRY="Guyana",
            BASIN="b",
            OPERATOR="op",
            STATUS="flowing",
        )


def test_schema_rejects_bad_resource_basis() -> None:
    with pytest.raises(ValueError):
        DiscoverySchema(
            DISCOVERY_NAME="X",
            BLOCK="X",
            COUNTRY="Guyana",
            BASIN="b",
            OPERATOR="op",
            RESOURCE_BASIS="proven",
        )


def test_schema_blank_resource_basis_defaults() -> None:
    m = DiscoverySchema(
        DISCOVERY_NAME="X",
        BLOCK="X",
        COUNTRY="Guyana",
        BASIN="b",
        OPERATOR="op",
        RESOURCE_BASIS="",
    )
    assert m.RESOURCE_BASIS == "not_disclosed"


def test_schema_coerces_blank_depth_to_none() -> None:
    m = DiscoverySchema(
        DISCOVERY_NAME="X",
        BLOCK="X",
        COUNTRY="Guyana",
        BASIN="b",
        OPERATOR="op",
        WATER_DEPTH_M="",
    )
    assert m.WATER_DEPTH_M is None


def test_schema_rejects_implausible_depth() -> None:
    with pytest.raises(ValueError):
        DiscoverySchema(
            DISCOVERY_NAME="X",
            BLOCK="X",
            COUNTRY="Guyana",
            BASIN="b",
            OPERATOR="op",
            WATER_DEPTH_M=9999,
        )


# --- Curated-data tests ---


def test_dataset_is_non_trivial(records) -> None:
    assert len(records) >= 40


def test_dataset_covers_all_three_countries(records) -> None:
    countries = {r.COUNTRY for r in records}
    assert countries == EXPECTED_COUNTRIES


def test_dataset_has_anchor_discoveries(records) -> None:
    names = {r.DISCOVERY_NAME for r in records}
    missing = EXPECTED_DISCOVERIES - names
    assert not missing, f"missing anchor discoveries: {missing}"


def test_every_record_has_a_source_url(records) -> None:
    for r in records:
        assert r.DATA_SOURCE_URL, f"{r.DISCOVERY_NAME} has no DATA_SOURCE_URL"
        assert r.DATA_SOURCE_URL.startswith("http")


def test_every_record_is_graded(records) -> None:
    for r in records:
        assert r.CONFIDENCE_TIER in {"high", "medium", "low"}


def test_depths_within_bounds(records) -> None:
    for r in records:
        if r.WATER_DEPTH_M is not None:
            assert 0 < r.WATER_DEPTH_M <= 4000


def test_disclosed_volumes_have_a_basis(records) -> None:
    # If a numeric/qualitative estimate is present, basis must not be "not_disclosed".
    for r in records:
        if r.RESOURCE_ESTIMATE:
            assert r.RESOURCE_BASIS != "not_disclosed", (
                f"{r.DISCOVERY_NAME} has an estimate but no resource basis"
            )


# --- Loader query tests ---


def test_query_by_country() -> None:
    loader = FrontierDiscoveryLoader()
    guyana = loader.query(country="Guyana")
    assert guyana
    assert all(r.COUNTRY == "Guyana" for r in guyana)


def test_query_by_operator_and_tier() -> None:
    loader = FrontierDiscoveryLoader()
    exxon_high = loader.query(operator="ExxonMobil", tier="high")
    assert exxon_high
    assert all(r.CONFIDENCE_TIER == "high" for r in exxon_high)


def test_query_min_water_depth() -> None:
    loader = FrontierDiscoveryLoader()
    deep = loader.query(min_water_depth_m=2000)
    assert deep
    assert all(r.WATER_DEPTH_M >= 2000 for r in deep)


def test_get_by_partial_name() -> None:
    loader = FrontierDiscoveryLoader()
    r = loader.get("venus")
    assert r is not None
    assert "Venus" in r.DISCOVERY_NAME
