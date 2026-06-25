# ABOUTME: Tests for the SubseaIQ loader + BSEE block-keyed crosswalk (issue #569).
# ABOUTME: Block parsing, concept loading, and join behaviour (synthetic codes).
"""Tests for ``worldenergydata.field_development.subseaiq``."""

from __future__ import annotations

from worldenergydata.field_development import (
    FieldConcept,
    FluidType,
    bsee_block_key,
    build_bsee_crosswalk,
    crosswalk_summary,
    load_subseaiq_fields,
)
from worldenergydata.field_development.subseaiq import key_to_code


# --------------------------------------------------------------------------- #
# Block-key parsing — the join key
# --------------------------------------------------------------------------- #
def test_full_area_name_parses():
    assert bsee_block_key("Green Canyon 254") == ("GC", 254)
    assert bsee_block_key("Mississippi Canyon 807") == ("MC", 807)


def test_abbreviated_code_parses():
    assert bsee_block_key("MC26") == ("MC", 26)
    assert bsee_block_key("GC 254") == ("GC", 254)


def test_multiblock_takes_first_block():
    assert bsee_block_key("Mississippi Canyon 108, 109, 110") == ("MC", 108)


def test_zero_padding_normalized_via_int():
    assert bsee_block_key("West Delta 30") == ("WD", 30)
    # 'WD030' and 'West Delta 30' must collapse to the same key.
    assert bsee_block_key("WD030") == ("WD", 30)


def test_non_gom_block_returns_none():
    assert bsee_block_key("PL 218 - 6706/12") is None  # North Sea licence
    assert bsee_block_key("") is None


def test_key_to_code_roundtrip():
    assert key_to_code(("GC", 254)) == "GC254"


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #
def test_load_subseaiq_fields_returns_concepts():
    fields = load_subseaiq_fields()
    assert len(fields) > 1000
    assert all(isinstance(f, FieldConcept) for f in fields)
    aasta = next(f for f in fields if f.name.startswith("Aasta Hansteen"))
    assert aasta.water_depth_m == 1300.0
    assert aasta.fluid_type == FluidType.GAS
    assert aasta.data_source.startswith("SubseaIQ")


# --------------------------------------------------------------------------- #
# Crosswalk — joins on block, not name
# --------------------------------------------------------------------------- #
def test_crosswalk_matches_on_block_code():
    # Synthetic BSEE field-code set; Allegheny is Green Canyon 254.
    rows = build_bsee_crosswalk(["GC254", "MC807", "WD030"])
    alleg = next(r for r in rows if r.field_name == "Allegheny")
    assert alleg.bsee_block_key == "GC254"
    assert alleg.matched is True and alleg.match_type == "block"


def test_crosswalk_handles_zero_padded_bsee_codes():
    # A zero-padded BSEE code must still match the integer-normalized key.
    rows = build_bsee_crosswalk(["GC0254"])
    alleg = next(r for r in rows if r.field_name == "Allegheny")
    assert alleg.matched is True


def test_crosswalk_unmatched_when_code_absent():
    rows = build_bsee_crosswalk(["ZZ999"])
    assert all(not r.matched for r in rows)


def test_crosswalk_gom_only_by_default():
    rows = build_bsee_crosswalk(["GC254"])
    # Aasta Hansteen (Norway) is not US_GOM → excluded from the GoM crosswalk.
    assert not any(r.field_name.startswith("Aasta Hansteen") for r in rows)


def test_crosswalk_summary_counts():
    rows = build_bsee_crosswalk(["GC254", "MC807"])
    s = crosswalk_summary(rows)
    assert s["total"] == len(rows)
    assert s["matched"] >= 1
    assert s["total"] >= s["matched"] + s["unparsed"]
