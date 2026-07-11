"""Unit tests for the landman lease-panel builder (issue #951)."""

from __future__ import annotations

from worldenergydata.field_development.landman import PENDING_ATTRS, build_landman

FACTS = {
    "operator": "Chevron",
    "working_interest": [
        {"name": "Chevron", "wi": 51, "operator": True},
        {"name": "Equinor", "wi": 24.5, "operator": False},
        {"name": "Suncor", "wi": 24.5, "operator": False},
    ],
}
LEASE_ROWS = {
    "G17015": {"lease_name": "Jack", "water_depth_ft": 7000, "dev_system": "subsea20"},
}


def test_build_landman_rows_and_fieldlevel():
    lm = build_landman(
        FACTS,
        ["G17015", "G17016", "G18745"],
        ["WR678", "WR758", "WR759"],
        LEASE_ROWS,
        959,
        "Walker Ridge 678",
    )
    assert lm["n_leases"] == 3
    # Field-level blocks list (NOT per-lease), operator + partner WI are real.
    assert lm["blocks"] == ["WR678", "WR758", "WR759"]
    assert lm["operator"] == "Chevron"
    assert lm["working_interest"][0]["name"] == "Chevron"
    assert lm["ingest_issue"] == 959


def test_no_per_lease_block_key():
    # False-precision guard (#951 r1 f4): leases and blocks are unpaired parallel
    # lists — a lease row must NEVER carry a specific block.
    lm = build_landman(
        FACTS, ["G17015", "G17016"], ["WR678", "WR758", "WR759"], {}, 959
    )
    for row in lm["leases"]:
        assert "block" not in row
    assert PENDING_ATTRS and "per_lease_block" in lm["pending"]


def test_join_and_placeholders():
    lm = build_landman(FACTS, ["G17015", "G17016"], ["WR678"], LEASE_ROWS, 959)
    matched = lm["leases"][0]
    assert matched["lease_num"] == "G17015"
    assert matched["water_depth_ft"] == 7000 and matched["dev_system"] == "subsea20"
    # Unmatched lease: real fields null, still listed (never dropped).
    unmatched = lm["leases"][1]
    assert unmatched["lease_num"] == "G17016"
    assert unmatched["water_depth_ft"] is None
    # The rich landman attributes are all deferred placeholders.
    for attr in (
        "status",
        "effective_date",
        "expiration_date",
        "per_lease_working_interest",
    ):
        assert attr in lm["pending"]


def test_lease_normalization():
    rows = {
        "G25806": {"lease_name": "Buckskin", "water_depth_ft": 6800, "dev_system": "x"}
    }
    lm = build_landman(FACTS, ["OCS-G 25806"], ["KC872"], rows, 959)
    assert lm["leases"][0]["water_depth_ft"] == 6800
