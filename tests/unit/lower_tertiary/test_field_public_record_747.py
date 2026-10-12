"""Offline public-record corrections and scope preservation for issue 747."""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.lower_tertiary.npv import load_field_inputs

FIELDS = Path(__file__).resolve().parents[3] / "config/analysis/lower_tertiary/fields"
# Parsed origin/main literals at the dispatched base revision.
ORIGINAL = {
    "cascade_chinook": {
        "field_id": "cascade_chinook",
        "display_name": "Cascade/Chinook",
        "status": "producing",
        "leases_key": "cascade_chinook",
        "first_oil": "2021-08-01",
        "data_through": "2024-12-31",
        "operator": "TotalEnergies",
        "partners": [
            {"name": "TotalEnergies", "working_interest": 0.6},
            {"name": "Equinor", "working_interest": 0.4},
        ],
        "capex": {"total_mm_usd": 2900},
        "production_profile": {"plateau_rate_mbopd": 75, "gor_scf_per_bbl": 1400},
        "opex_per_boe": 18.0,
    },
    "julia": {
        "field_id": "julia",
        "display_name": "Julia",
        "status": "producing",
        "leases_key": "julia",
        "first_oil": "2016-03-01",
        "data_through": "2024-12-31",
        "operator": "Equinor",
        "partners": [
            {"name": "Equinor", "working_interest": 0.5},
            {"name": "ExxonMobil", "working_interest": 0.5},
        ],
        "capex": {
            "total_mm_usd": 4700,
            "host_mm_usd": 2500,
            "subsea_mm_usd": 1500,
            "wells_mm_usd": 700,
        },
        "production_profile": {"plateau_rate_mbopd": 34, "gor_scf_per_bbl": 1000},
        "opex_per_boe": 18.0,
    },
    "jack_st_malo": {
        "field_id": "jack_st_malo",
        "display_name": "Jack/St. Malo",
        "status": "producing",
        "leases_key": "jack_st_malo",
        "first_oil": "2014-02-01",
        "data_through": "2024-12-31",
        "operator": "Chevron",
        "partners": [
            {"name": "Chevron", "working_interest": 0.51},
            {"name": "Equinor", "working_interest": 0.245},
            {"name": "Suncor", "working_interest": 0.245},
        ],
        "capex": {
            "total_mm_usd": 7500,
            "wells_mm_usd": 4100,
            "facilities_mm_usd": 3400,
        },
        "opex_per_boe": 15.0,
        "production_profile": {"plateau_rate_mbopd": 94, "gor_scf_per_bbl": 1200},
    },
}
CORRECTIONS = {
    "cascade_chinook": {"first_oil": "2012-02-01", "operator": "Murphy"},
    "julia": {"operator": "ExxonMobil"},
    "jack_st_malo": {"first_oil": "2014-12-01"},
}


@pytest.mark.parametrize("field_id", ORIGINAL)
def test_public_record_and_unchanged_keys(field_id):
    expected = {**ORIGINAL[field_id], **CORRECTIONS[field_id]}
    parsed = yaml.safe_load((FIELDS / f"{field_id}.yml").read_text())["field"]
    # Whole-dictionary equality preserves partners and every unmodified key.
    assert parsed == expected
    loaded = load_field_inputs(FIELDS, {"fields": {}})[field_id]
    assert loaded["raw"] == expected
    assert loaded["first_oil"] == pd.Timestamp(expected["first_oil"])


@pytest.mark.parametrize("field_id", ["cascade_chinook", "jack_st_malo"])
def test_partner_fallback_is_explicit(field_id):
    text = (FIELDS / f"{field_id}.yml").read_text()
    assert "issue 747" in text
    assert "not verified" in text
    assert "Was" in text
    if field_id == "cascade_chinook":
        assert "Cascade: MP GOM 1.00" in text
        assert "Chinook: MP GOM 0.666 (operated)" in text
        assert "ownership of MP GOM" in text
    else:
        assert "Jack 0.50; St. Malo 0.51" in text
