"""Tests for Kansas KGS well master parsing."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd
import pytest


def test_wells_parser_extracts_depth_api14_and_dates(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.wells import parse_wells_master

    zip_path = tmp_path / "ks_wells.zip"
    _write_wells_zip(zip_path)

    wells = parse_wells_master(zip_path)

    row = wells.loc[wells["api10"].eq("1506720048")].iloc[0]
    assert row["well_kid"] == "1001232609"
    assert row["api14"] == "15067200480000"
    assert row["quality_flags"] == ""
    assert wells.attrs["quality"]["wells_invalid_api14_count"] == 0
    assert row["field_name"] == "HUGOTON GAS AREA"
    assert row["reference_depth_ft"] == 4470.0
    assert row["formation"] == "CHASE GROUP"
    assert row["county_name"] == "Grant"
    assert str(row["spud_date"].date()) == "1996-01-02"
    assert str(row["completion_date"].date()) == "1996-02-03"
    assert wells.attrs["quality"]["well_row_count"] == 1
    assert wells.attrs["quality"]["wells_date_parse_failure_count"] == 0


def test_wells_parser_rejects_missing_required_columns(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.wells import parse_wells_master

    zip_path = tmp_path / "ks_wells.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("ks_wells.txt", "KID,API_NUMBER\n1,15-067-20048\n")

    with pytest.raises(ValueError, match="missing required columns"):
        parse_wells_master(zip_path)


def test_wells_parser_counts_date_parse_failures(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.wells import parse_wells_master

    zip_path = tmp_path / "ks_wells.zip"
    _write_wells_zip(zip_path, spud="not-a-date")

    wells = parse_wells_master(zip_path)

    assert wells.attrs["quality"]["wells_date_parse_failure_count"] == 1


def test_wells_parser_uses_producing_formation_when_total_depth_formation_blank(
    tmp_path: Path,
) -> None:
    from worldenergydata.kansas_kgs.wells import parse_wells_master

    zip_path = tmp_path / "ks_wells.zip"
    _write_wells_zip(zip_path, formation_at_total_depth="")

    wells = parse_wells_master(zip_path)

    assert wells.iloc[0]["formation"] == "CHASE"


@pytest.mark.parametrize(
    "api14",
    ["1506720048", "150672004800", "150672004800000", "1506720048000x", "", "   "],
)
def test_invalid_api14_is_flagged_and_not_emitted(tmp_path: Path, api14: str) -> None:
    """Issue #1352 (2026), defect 4: independently count string characters.

    Inputs have ten, twelve, fifteen, fourteen with a letter, or no digits.
    None meets the required fourteen-digit identity shape. One input well
    therefore gives one invalid flag and one counter, and a missing API14
    in both normalized wells and the joined observation.
    """
    from worldenergydata.kansas_kgs.observations import build_pressure_observations
    from worldenergydata.kansas_kgs.wells import parse_wells_master

    path = tmp_path / "ks_wells.zip"
    _write_wells_zip(path, api14=api14)
    wells = parse_wells_master(path)
    assert pd.isna(wells.iloc[0]["api14"])
    assert wells.iloc[0]["quality_flags"] == "invalid_api14"
    assert wells.attrs["quality"]["wells_invalid_api14_count"] == 1
    rows = pd.DataFrame(
        [
            {
                "api10": "1506720048",
                "well_kid": "1001232609",
                "pressure_psig_raw": 10,
                "test_year": 2000,
                "source_row_id": 1,
            }
        ]
    )
    observation = build_pressure_observations(rows, wells).observations.iloc[0]
    assert pd.isna(observation["api14"])
    assert "invalid_api14" in observation["quality_flags"].split("|")
    assert observation["is_earliest_observation_for_well"] is True


def _write_wells_zip(
    path: Path,
    spud: str = "02-JAN-1996",
    formation_at_total_depth: str = "CHASE GROUP",
    api14: str = "15067200480000",
) -> None:
    header = (
        "KID,API_NUMBER,API_NUM_NODASH,LEASE,WELL,FIELD,LATITUDE,LONGITUDE,"
        "DEPTH,FORMATION_AT_TOTAL_DEPTH,PRODUCE_FORM,SPUD,COMPLETION,"
        "PLUGGING,MODIFIED"
    )
    rows = [
        header,
        '"1001232609","15-067-20048","15067200480000","POWELL","2-31",'
        '"HUGOTON GAS AREA","37.4789143","-101.4114608","4470",'
        f'"{formation_at_total_depth}","CHASE","{spud}","03-FEB-1996",'
        ',"05-JUN-2026"',
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "ks_wells.txt", "\n".join(rows).replace("15067200480000", api14)
        )
