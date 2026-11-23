"""Tests for field-level geological era lifting (field_era module).

Uses only synthetic data written to ``tmp_path`` — no real BSEE files.
"""

import pickle

import pandas as pd
import pytest

from worldenergydata.bsee.paleowells.field_era import (
    LOWER_TERTIARY_ERAS,
    apply_field_era,
    build_field_era_map,
    is_lower_tertiary,
)


def _write_synthetic_data(data_dir):
    """Create a tiny Paleowells.csv + apiraw pickle under ``data_dir``.

    Layout mirrors the real module:
      <data_dir>/paleowells/Paleowells.csv
      <data_dir>/bin/apiraw/mv_api_list_all.bin
    """
    paleo_dir = data_dir / "paleowells"
    apiraw_dir = data_dir / "bin" / "apiraw"
    paleo_dir.mkdir(parents=True, exist_ok=True)
    apiraw_dir.mkdir(parents=True, exist_ok=True)

    # Field FX1: two wells, both Eocene -> dominant Eocene.
    # Field FX2: well A2 Oligocene, well A3 Miocene -> dominant Oligocene
    #            (2 Oligocene records vs 1 Miocene).
    paleo = pd.DataFrame(
        {
            "API Well Number": [
                "100000000001",
                "100000000001",
                "100000000002",
                "100000000003",
                "100000000003",
                "100000000004",  # well not present in apiraw -> dropped
            ],
            "Paleo Age": [
                "Upper Eocene (Priabonian) Discoaster",
                "Lower Eocene (Ypresian) Tribrachiatus",
                "Lower Oligocene (Rupelian) Helicosphaera",
                "Upper Oligocene (Chattian) Sphenolithus",
                "Middle Miocene Globigerina",
                "Upper Pliocene Foo",
            ],
        }
    )
    paleo.to_csv(paleo_dir / "Paleowells.csv", index=False)

    apiraw = pd.DataFrame(
        {
            "API_WELL_NUMBER": [
                "100000000001",
                "100000000002",
                "100000000003",
                "999999999999",  # unrelated well
            ],
            "BOTM_FLD_NAME_CD": ["FX1", "FX2", "FX2", "FX9"],
        }
    )
    with open(apiraw_dir / "mv_api_list_all.bin", "wb") as f:
        pickle.dump(apiraw, f)

    return data_dir


def test_lower_tertiary_eras_membership():
    assert LOWER_TERTIARY_ERAS == frozenset({"Paleocene", "Eocene", "Oligocene"})
    assert "Paleocene" in LOWER_TERTIARY_ERAS
    assert "Eocene" in LOWER_TERTIARY_ERAS
    assert "Oligocene" in LOWER_TERTIARY_ERAS
    assert "Miocene" not in LOWER_TERTIARY_ERAS


def test_is_lower_tertiary():
    assert is_lower_tertiary("Paleocene") is True
    assert is_lower_tertiary("Eocene") is True
    assert is_lower_tertiary("Oligocene") is True
    assert is_lower_tertiary("Miocene") is False
    assert is_lower_tertiary("Pliocene") is False
    assert is_lower_tertiary("Unknown") is False
    assert is_lower_tertiary(None) is False


def test_build_field_era_map_dominant_era(tmp_path):
    data_dir = _write_synthetic_data(tmp_path)
    field_era = build_field_era_map(data_dir=data_dir)

    assert field_era["FX1"] == "Eocene"
    # FX2: two Oligocene records (one well Oligocene, second well has one
    # Oligocene + one Miocene record) -> Oligocene dominates.
    assert field_era["FX2"] == "Oligocene"
    # The well not present in apiraw must not introduce a field.
    assert all(fc in {"FX1", "FX2"} for fc in field_era)


def test_build_field_era_map_missing_apiraw(tmp_path):
    # Paleo CSV present but no apiraw bin -> graceful empty map, no raise.
    paleo_dir = tmp_path / "paleowells"
    paleo_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "API Well Number": ["100000000001"],
            "Paleo Age": ["Upper Eocene Discoaster"],
        }
    ).to_csv(paleo_dir / "Paleowells.csv", index=False)

    assert build_field_era_map(data_dir=tmp_path) == {}


def test_build_field_era_map_lfs_stub(tmp_path):
    # apiraw is an LFS pointer stub -> graceful empty map.
    paleo_dir = tmp_path / "paleowells"
    apiraw_dir = tmp_path / "bin" / "apiraw"
    paleo_dir.mkdir(parents=True)
    apiraw_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "API Well Number": ["100000000001"],
            "Paleo Age": ["Upper Eocene Discoaster"],
        }
    ).to_csv(paleo_dir / "Paleowells.csv", index=False)
    (apiraw_dir / "mv_api_list_all.bin").write_bytes(
        b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\n"
    )

    assert build_field_era_map(data_dir=tmp_path) == {}


def test_apply_field_era_overrides_and_sets_flag():
    result = pd.DataFrame(
        {
            "FIELD_CODE": ["FX1", "FX2", "FX3"],
            "GEOLOGICAL_ERA": ["Unknown", "Miocene", "Pliocene"],
        }
    )
    field_era = {"FX1": "Eocene", "FX2": "Oligocene"}

    out = apply_field_era(result, field_era)

    # Original frame untouched (copy semantics).
    assert result.loc[0, "GEOLOGICAL_ERA"] == "Unknown"

    # FX1, FX2 overridden by the authoritative field-level map.
    assert out.loc[0, "GEOLOGICAL_ERA"] == "Eocene"
    assert out.loc[1, "GEOLOGICAL_ERA"] == "Oligocene"
    # FX3 not in map -> keeps existing era.
    assert out.loc[2, "GEOLOGICAL_ERA"] == "Pliocene"

    # Lower-Tertiary flag derived from the (possibly overridden) era.
    assert out.loc[0, "IS_LOWER_TERTIARY"] is True or bool(
        out.loc[0, "IS_LOWER_TERTIARY"]
    )
    assert bool(out.loc[1, "IS_LOWER_TERTIARY"]) is True
    assert bool(out.loc[2, "IS_LOWER_TERTIARY"]) is False


def test_apply_field_era_empty_df():
    empty = pd.DataFrame(columns=["FIELD_CODE", "GEOLOGICAL_ERA"])
    out = apply_field_era(empty, {"FX1": "Eocene"})
    assert out.empty
    assert "IS_LOWER_TERTIARY" in out.columns
