"""Tests for the curated subsea-manifold supplier database + loader."""

from __future__ import annotations

import pytest

from worldenergydata.subsea import ManifoldSupplierLoader, ManifoldSupplierSchema
from worldenergydata.subsea.schemas.manifold_supplier import LIST_DELIMITER

EXPECTED_KEY_PLAYERS = {
    "ABB",
    "Aker Solutions",
    "Baker Hughes",
    "Dril-Quip",
    "Halliburton",
    "McDermott",
    "SLB OneSubsea",
    "Subsea 7",
    "TechnipFMC",
    "Trendsetter",
}


@pytest.fixture(scope="module")
def records() -> list[ManifoldSupplierSchema]:
    return ManifoldSupplierLoader().all()


# --- Schema-level tests ---


def test_schema_splits_delimited_lists() -> None:
    row = {
        "COMPANY": "Test Co",
        "PRODUCT_LINES": f"Manifolds{LIST_DELIMITER}PLET{LIST_DELIMITER}PLEM",
    }
    model = ManifoldSupplierSchema(**row)
    assert model.PRODUCT_LINES == ["Manifolds", "PLET", "PLEM"]


def test_schema_accepts_native_lists() -> None:
    model = ManifoldSupplierSchema(
        COMPANY="Test Co", DATA_SOURCE_URLS=["https://a", "https://b"]
    )
    assert model.DATA_SOURCE_URLS == ["https://a", "https://b"]


def test_schema_requires_company() -> None:
    with pytest.raises(ValueError):
        ManifoldSupplierSchema(COMPANY="")


def test_schema_rejects_bad_role() -> None:
    with pytest.raises(ValueError):
        ManifoldSupplierSchema(COMPANY="X", MANIFOLD_ROLE="distributor")


def test_schema_rejects_bad_tier() -> None:
    with pytest.raises(ValueError):
        ManifoldSupplierSchema(COMPANY="X", ROLE_TIER="tier_5")


def test_schema_coerces_unknown_depth_to_none() -> None:
    model = ManifoldSupplierSchema(COMPANY="X", MAX_WATER_DEPTH_M="unknown")
    assert model.MAX_WATER_DEPTH_M is None


def test_schema_rejects_implausible_depth() -> None:
    with pytest.raises(ValueError):
        ManifoldSupplierSchema(COMPANY="X", MAX_WATER_DEPTH_M=99999)


# --- Curated-data tests ---


def test_database_has_all_key_players(records) -> None:
    assert len(records) >= 10
    names = " | ".join(r.COMPANY for r in records)
    for player in EXPECTED_KEY_PLAYERS:
        assert player in names, f"missing key player: {player}"


def test_every_record_has_a_source_url(records) -> None:
    for r in records:
        assert r.DATA_SOURCE_URL, f"{r.COMPANY} has no DATA_SOURCE_URL"
        assert r.DATA_SOURCE_URL.startswith("http")
        assert r.DATA_SOURCE_URLS, f"{r.COMPANY} has no source list"


def test_every_record_is_classified(records) -> None:
    for r in records:
        assert r.MANIFOLD_ROLE is not None
        assert r.ROLE_TIER is not None


def test_depths_within_bounds(records) -> None:
    for r in records:
        if r.MAX_WATER_DEPTH_M is not None:
            assert 0 < r.MAX_WATER_DEPTH_M <= 6000


# --- Loader query tests ---


def test_query_by_role_and_tier() -> None:
    loader = ManifoldSupplierLoader()
    tier1_oems = loader.query(role="OEM", tier="tier_1")
    companies = {r.COMPANY for r in tier1_oems}
    assert "TechnipFMC plc" in companies
    assert "Baker Hughes Company" in companies
    assert all(r.MANIFOLD_ROLE == "OEM" for r in tier1_oems)


def test_query_min_water_depth() -> None:
    loader = ManifoldSupplierLoader()
    deep = loader.query(min_water_depth_m=3000)
    assert deep
    assert all(r.MAX_WATER_DEPTH_M >= 3000 for r in deep)


def test_get_by_partial_name() -> None:
    loader = ManifoldSupplierLoader()
    r = loader.get("technip")
    assert r is not None
    assert "TechnipFMC" in r.COMPANY
