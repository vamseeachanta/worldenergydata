"""Offline, source-linked public-record assertions for issue 747."""

from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.lower_tertiary.npv import load_field_inputs

FIELDS = Path(__file__).resolve().parents[3] / "config/analysis/lower_tertiary/fields"
# Sources are the research note's keys; Julia's unchanged month retains its
# existing regulator provenance and is not independently verified by that note.
CORRECTIONS = {
    "cascade_chinook": {
        "first_oil": {"value": "2012-02-01", "sources": ("P1:", "P2:")},
        "operator": {"value": "Murphy", "sources": ("P2:", "P3:", "P5:")},
    },
    "julia": {
        "first_oil": {"value": "2016-03-01", "sources": ("BSEE OGOR-A",)},
        "operator": {"value": "ExxonMobil", "sources": ("P6:",)},
    },
    "jack_st_malo": {
        "first_oil": {"value": "2014-12-01", "sources": ("P7:", "P8:")},
        "operator": {"value": "Chevron", "sources": ("P7:",)},
    },
}


def assert_public_record(field_id, directory, reader):
    text = (directory / f"{field_id}.yml").read_text(encoding="utf-8")
    if reader == "yaml":
        parsed = yaml.safe_load(text)["field"]
    else:
        loaded = load_field_inputs(directory, {"fields": {}})[field_id]
        parsed = loaded["raw"]
        assert loaded["first_oil"] == pd.Timestamp(
            CORRECTIONS[field_id]["first_oil"]["value"]
        )
    comments = "\n".join(
        line for line in text.splitlines() if line.lstrip().startswith("#")
    )
    for key, correction in CORRECTIONS[field_id].items():
        assert parsed[key] == correction["value"], key
        assert correction["sources"]
        for source in correction["sources"]:
            assert source and source in comments


@pytest.mark.parametrize("field_id", CORRECTIONS)
def test_public_record_corrections(field_id):
    for reader in ("yaml", "loader"):
        assert_public_record(field_id, FIELDS, reader)


@pytest.mark.parametrize("reader", ["yaml", "loader"])
def test_reverted_first_oil_is_rejected(tmp_path, reader):
    field_id = "cascade_chinook"
    text = (FIELDS / f"{field_id}.yml").read_text(encoding="utf-8")
    reverted = text.replace('first_oil: "2012-02-01"', 'first_oil: "2021-08-01"')
    assert reverted != text
    (tmp_path / f"{field_id}.yml").write_text(reverted, encoding="utf-8")
    with pytest.raises(AssertionError):
        assert_public_record(field_id, tmp_path, reader)


@pytest.mark.parametrize("field_id", ["cascade_chinook", "jack_st_malo"])
def test_partner_fallback_is_explicit(field_id):
    text = (FIELDS / f"{field_id}.yml").read_text(encoding="utf-8")
    assert "issue 747" in text
    assert "not verified" in text
    if field_id == "cascade_chinook":
        assert "Cascade: MP GOM 1.00" in text
        assert "Chinook: MP GOM 0.666 (operated)" in text
        assert "ownership of MP GOM" in text
        assert "P4:" in text
        assert "Combined-field working interest for Murphy: not verified" in text
    else:
        assert "Jack 0.50; St. Malo 0.51" in text
        assert "P7:" in text
