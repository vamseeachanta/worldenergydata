"""Parsing rules of scripts/bsee/build_riser_segments.py (no network, no raw files)."""

import importlib.util
from pathlib import Path

import pytest

_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "bsee" / "build_riser_segments.py"
)
_spec = importlib.util.spec_from_file_location("build_riser_segments", _PATH)
brs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(brs)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("06", (6.0, 6.625)),
        ("10", (10.0, 10.75)),
        ("16", (16.0, 16.0)),
        ("10 3/4", (10.75, 10.75)),
        ("04-10", (None, None)),
        ("", (None, None)),
    ],
)
def test_size_code(code, expected):
    assert brs.parse_size_code(code) == expected


def test_riser_types_follow_road_map_terms():
    text = "install a 10-inch steel catenary riser (SCR) in a lazy-wave configuration"
    assert brs.riser_types(text) == ["riser_any", "scr", "lazy_wave"]
    assert brs.riser_types("flexible riser to the FPSO") == ["riser_any", "flexible"]
    assert brs.riser_types("pipeline to platform") == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ('16" x 0.875" WT steel catenary riser', [0.875]),
        ("riser wall thickness of 0.938 inches", [0.938]),
        ("0.750-inch wall riser", [0.75]),
        ("riser with 1-1/8 in. W.T.", [1.125]),
        ("riser at 0.05 wt percent", []),
        ("no wall stated", []),
    ],
)
def test_wall_thickness_extraction(text, expected):
    assert brs.wall_thicknesses(text) == expected


def test_plausible_wall_needs_reasonable_d_over_t():
    assert brs.plausible_wts(8.625, [1.45, 0.5]) == [0.5]
    assert brs.plausible_wts("", [0.5]) == []


def _row(**kw):
    base = {
        "riser_types": "scr",
        "od_in": 10.75,
        "max_water_depth_ft": 4000,
        "wt_in_plausible": "0.875",
        "product_code": "OIL",
    }
    base.update(kw)
    return base


def test_readiness_tiers():
    assert brs.readiness(_row()) == "A_ready_od_wt_depth"
    assert brs.readiness(_row(wt_in_plausible="")) == "B_needs_assumed_wt"
    assert (
        brs.readiness(_row(riser_types="flexible"))
        == "C_flexible_needs_vendor_properties"
    )
    assert brs.readiness(_row(od_in="")) == "D_insufficient_od_or_depth"
    assert brs.readiness(_row(max_water_depth_ft="")) == "D_insufficient_od_or_depth"
    assert brs.readiness(_row(product_code="UMBH")) == "E_umbilical_or_cable"


def test_depth_band():
    assert brs.depth_band(None) == "unknown"
    assert brs.depth_band(4500) == "3000-5000"
    assert brs.depth_band(9000) == ">=7500"
