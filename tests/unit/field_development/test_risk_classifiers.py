"""Unit tests for the underwriting-lens risk classifiers (issue #949)."""

from __future__ import annotations

from worldenergydata.field_development.decommission_risk import (
    classify_decommissioning,
)
from worldenergydata.field_development.hpht_risk import classify_hpht


def test_hpht_over_rating_anchor():
    r = classify_hpht(
        {"hpht_class": "ultra-HPHT", "pressure_psi": 25000, "equip_rating_psi": 20000}
    )
    assert r["exceedance_pct"] == 25
    assert r["severity"] == "over-rating"
    assert "25k vs 20k psi (+25%)" in r["label"]


def test_hpht_at_and_within():
    assert (
        classify_hpht(
            {
                "hpht_class": "ultra-HPHT",
                "pressure_psi": 20000,
                "equip_rating_psi": 20000,
            }
        )["severity"]
        == "at-rating"
    )
    assert (
        classify_hpht(
            {"hpht_class": "HPHT", "pressure_psi": 22000, "equip_rating_psi": 20000}
        )["exceedance_pct"]
        == 10
    )


def test_hpht_julia_system_basis_is_not_an_exceedance():
    # Julia's 13,500 psi is a subsea-system figure (15k-rated trees + HIPPS),
    # NOT reservoir pore pressure -> no reservoir-vs-equipment exceedance (#949 f4).
    r = classify_hpht(
        {
            "hpht_class": "HPHT",
            "pressure_psi": 13500,
            "equip_rating_psi": 15000,
            "pressure_basis": "subsea_system",
        }
    )
    assert r["exceedance_pct"] is None
    assert r["severity"] == "class-only"
    assert "subsea system" in r["label"]


def test_hpht_class_only_and_none():
    assert classify_hpht({"hpht_class": "HPHT"})["severity"] == "class-only"
    # rating-only (north_platte) is still class-only, not an exceedance.
    assert (
        classify_hpht({"hpht_class": "ultra-HPHT", "equip_rating_psi": 20000})[
            "exceedance_pct"
        ]
        is None
    )
    # No class and no pressure (big_foot) -> no signal.
    assert classify_hpht({"formation": "Wilcox"}) is None
    assert classify_hpht(None) is None


DECOM_ROWS = [
    {"facility_name": "Big Foot TLP", "cost_musd": "43.23", "host_type": "Mini-TLP"},
    {"facility_name": "Jack/St. Malo FPU", "cost_musd": "80.0", "host_type": "FPU/FPS"},
    {"facility_name": "Stones FPSO", "cost_musd": "80.0", "host_type": "FPSO"},
    {"facility_name": "Some Other", "cost_musd": "10.0", "host_type": "SPAR"},
]


def test_decommissioning_modeled_vs_low_confidence():
    bf = classify_decommissioning("Big Foot TLP", DECOM_ROWS)
    assert bf["cost_musd"] == 43.2 and bf["confidence"] == "modeled"
    jsm = classify_decommissioning("Jack/St. Malo FPU", DECOM_ROWS)
    assert jsm["cost_musd"] == 80.0 and jsm["confidence"] == "low"
    assert "FPSO base" in jsm["label"]
    st = classify_decommissioning("Stones FPSO", DECOM_ROWS)
    assert st["confidence"] == "low"


def test_decommissioning_no_match_or_no_name():
    assert classify_decommissioning("Anchor Semisub", DECOM_ROWS) is None
    assert classify_decommissioning(None, DECOM_ROWS) is None
