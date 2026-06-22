"""Unit tests for the field-level water depth source module.

Uses SYNTHETIC platstruc/deepqual pickles in ``tmp_path`` (never the real
multi-GB BSEE data) so the tests are deterministic and CI-portable.
"""

import pickle
from pathlib import Path

import pandas as pd

from tests.test_markers import unit
from worldenergydata.bsee.data.sources.bin.field_water_depth import (
    load_field_water_depth,
)


def _write_platstruc(data_dir: Path, df: pd.DataFrame) -> None:
    d = data_dir / "platstruc"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "mv_platstruc_structures.bin", "wb") as f:
        pickle.dump(df, f)


def _write_deepqual(data_dir: Path, df: pd.DataFrame) -> None:
    d = data_dir / "deepqual"
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "mv_deep_water_field_leases.bin", "wb") as f:
        pickle.dump(df, f)


@unit
def test_platstruc_primary_averaged_by_field(tmp_path):
    _write_platstruc(
        tmp_path,
        pd.DataFrame(
            {
                "FIELD_NAME_CODE": ["MC778", "MC778", "EI089"],
                "WATER_DEPTH": [6000.0, 6400.0, 21.0],
            }
        ),
    )
    out = load_field_water_depth(data_dir=tmp_path)
    assert out["MC778"] == 6200.0  # mean of 6000/6400
    assert out["EI089"] == 21.0


@unit
def test_deepqual_fills_gaps_only(tmp_path):
    """platstruc wins for shared codes; deepqual only fills codes it lacks."""
    _write_platstruc(
        tmp_path,
        pd.DataFrame({"FIELD_NAME_CODE": ["MC807"], "WATER_DEPTH": [2980.0]}),
    )
    _write_deepqual(
        tmp_path,
        pd.DataFrame(
            {
                # MC807 also present in deepqual at a different value — must
                # NOT override platstruc.
                "FIELD_NAME_CODE": ["MC807", "KC292"],
                "FLD_AVG_WTR_DPTH": [3341.0, 5879.0],
            }
        ),
    )
    out = load_field_water_depth(data_dir=tmp_path)
    assert out["MC807"] == 2980.0  # platstruc wins
    assert out["KC292"] == 5879.0  # deepqual fills gap


@unit
def test_water_depth_positive_filter(tmp_path):
    _write_platstruc(
        tmp_path,
        pd.DataFrame(
            {
                "FIELD_NAME_CODE": ["AA001", "AA001", "BB002"],
                "WATER_DEPTH": [0.0, -5.0, 100.0],
            }
        ),
    )
    out = load_field_water_depth(data_dir=tmp_path)
    assert "AA001" not in out  # all rows non-positive -> dropped
    assert out["BB002"] == 100.0


@unit
def test_blank_field_code_dropped(tmp_path):
    _write_platstruc(
        tmp_path,
        pd.DataFrame(
            {
                "FIELD_NAME_CODE": ["", "   ", "CC003"],
                "WATER_DEPTH": [500.0, 600.0, 700.0],
            }
        ),
    )
    out = load_field_water_depth(data_dir=tmp_path)
    assert "" not in out
    assert out == {"CC003": 700.0}


@unit
def test_missing_files_return_empty(tmp_path):
    out = load_field_water_depth(data_dir=tmp_path)
    assert out == {}


@unit
def test_lfs_stub_handled(tmp_path):
    d = tmp_path / "platstruc"
    d.mkdir(parents=True)
    (d / "mv_platstruc_structures.bin").write_bytes(
        b"version https://git-lfs.github.com/spec/v1\noid sha256:deadbeef\n"
    )
    out = load_field_water_depth(data_dir=tmp_path)
    assert out == {}
