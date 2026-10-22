"""CLI tests for Kansas KGS pressure observations."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from worldenergydata.cli.commands.kansas_kgs import app


def test_cli_build_writes_packet(tmp_path: Path) -> None:
    _write_raw_fixture(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "build-pressure-observations",
            "--root",
            str(tmp_path),
            "--allow-non-ace-root",
        ],
    )

    assert result.exit_code == 0, result.output
    target = tmp_path / "curated/pressure/well_pressure_observations"
    assert (target / "well_pressure_observations.csv").exists()
    assert (target / "well_pressure_observations.parquet").exists()
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["row_count"] == 1
    assert "Wrote Kansas KGS pressure observations" in result.output


def test_cli_dry_run_reports_counts_without_curated_writes(tmp_path: Path) -> None:
    _write_raw_fixture(tmp_path)
    raw_paths = [
        tmp_path / "raw/pressure/kansas_proration_pressures.txt",
        tmp_path / "raw/wells/ks_wells.zip",
    ]
    before = {path: path.read_bytes() for path in raw_paths}

    result = CliRunner().invoke(
        app,
        [
            "build-pressure-observations",
            "--root",
            str(tmp_path),
            "--dry-run",
            "--allow-non-ace-root",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Dry run" in result.output
    assert all(path.is_file() for path in raw_paths)
    assert {path: path.read_bytes() for path in raw_paths} == before
    assert not (tmp_path / "curated/pressure/well_pressure_observations").exists()


def test_cli_info_lists_kansas_kgs_module() -> None:
    from worldenergydata.cli.main import app as main_app

    result = CliRunner().invoke(main_app, ["info"])

    assert result.exit_code == 0, result.output
    assert "kansas-kgs" in result.output
    assert "Kansas Geological Survey" in result.output


def _write_raw_fixture(root: Path) -> None:
    pressure_path = root / "raw/pressure/kansas_proration_pressures.txt"
    pressure_path.parent.mkdir(parents=True, exist_ok=True)
    pressure_path.write_text(_pressure_fixture(), encoding="utf-8")

    wells_path = root / "raw/wells/ks_wells.zip"
    wells_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wells_path, "w") as archive:
        archive.writestr("ks_wells.txt", _wells_fixture())


def _pressure_fixture() -> str:
    return "\n".join(
        [
            "WELL_KID,LEASE,API_NUMBER,OPERATOR,TOWNSHIP,TWN_DIR,RANGE,"
            "RANGE_DIR,SECTION,LATITUDE,LONGITUDE,YEAR,ACREAGE,SHUT_IN_PRESS,"
            "WORKING_PRES,DAILY_RATE,OPEN_FLOW,ADJ_DELIVER,WATER_PROD,"
            "METER_PRES,DIFFERENT,COEFF",
            'RES","DIFFERENT","COEFF"',
            '"1001232609","POWELL 2-31","15-067-20048","MESA","29","S",'
            '"37","W","31","37.4789143","-101.4114608","1997","636",'
            '"47.3","38.8","337.26","1022","645","0","38.3","10.58","12.1"',
        ]
    )


def _wells_fixture() -> str:
    return "\n".join(
        [
            "KID,API_NUMBER,API_NUM_NODASH,LEASE,WELL,FIELD,LATITUDE,LONGITUDE,"
            "DEPTH,FORMATION_AT_TOTAL_DEPTH,PRODUCE_FORM,SPUD,COMPLETION,"
            "PLUGGING,MODIFIED",
            '"1001232609","15-067-20048","15067200480000","POWELL","2-31",'
            '"HUGOTON GAS AREA","37.4789143","-101.4114608","4470",'
            '"CHASE GROUP","CHASE","02-JAN-1996","03-FEB-1996","","05-JUN-2026"',
        ]
    )


def test_synthetic_build_matches_hand_count(tmp_path: Path) -> None:
    """Independent hand calculation, knowledge pack revision 3, section 11.

    Seven pressure records contain one zero: six observations. Two known
    rows have depth, two anonymous rows have no join, one row has two well
    candidates, and one uniquely joined row has invalid API14 and zero depth.
    Thus missing depth = two + one + one = four; missing well = two;
    ambiguous join/identity = one each; invalid well API14 = one.
    Anonymous rows alone lack counties: two. All six have years; four have
    mapped counties. Earliest flags are True, False, True, True, None, True.

    Arithmetic uses the existing implementation assumption documented in
    agent-pack.md revision 2 (2026), section 3, not a new physical constant:
    ten + 14.7 = 24.7; twenty + 14.7 = 34.7; divide each by the synthetic
    depth of one thousand feet to obtain 0.0247 and 0.0347 psi/ft exactly.
    This checks arithmetic only; physical qualification remains UNVERIFIED.
    """
    import csv
    import hashlib
    from io import StringIO

    from worldenergydata.kansas_kgs.cli_support import build_pressure_observation_packet
    from worldenergydata.kansas_kgs.io import load_pressure_observations

    pressure_path = tmp_path / "raw/pressure/kansas_proration_pressures.txt"
    pressure_path.parent.mkdir(parents=True)
    pressure_path.write_text(
        "WELL_KID,API_NUMBER,YEAR,SHUT_IN_PRESS\n"
        "known,15-067-20048,1997,10\n"
        "known,15-067-20048,1998,20\n"
        ",,1997,10\n"
        " , ,1998,20\n"
        "unmatched,15-189-20001,1997,30\n"
        "invalid,15-067-20049,1997,40\n"
        "known,15-067-20048,1999,0\n"
    )
    wells_path = tmp_path / "raw/wells/ks_wells.zip"
    wells_path.parent.mkdir(parents=True)
    # Synthetic identifiers and depths are inputs to the hand count above.
    well_rows = [
        ("known", "15-067-20048", "15067200480000", "1000"),
        ("candidate-a", "15-189-20001", "15189200010000", "1000"),
        ("candidate-b", "15-189-20001", "15189200010001", "1000"),
        ("invalid", "15-067-20049", "150672004900", "0"),
    ]
    contents = StringIO()
    writer = csv.writer(contents)
    writer.writerow(
        [
            "KID",
            "API_NUMBER",
            "API_NUM_NODASH",
            "DEPTH",
            "FIELD",
            "LATITUDE",
            "LONGITUDE",
            "FORMATION_AT_TOTAL_DEPTH",
            "PRODUCE_FORM",
            "SPUD",
            "COMPLETION",
            "PLUGGING",
            "MODIFIED",
        ]
    )
    for row in well_rows:
        writer.writerow([*row, *([""] * 9)])
    with zipfile.ZipFile(wells_path, "w") as archive:
        archive.writestr("ks_wells.txt", contents.getvalue())

    built = build_pressure_observation_packet(tmp_path, allow_non_ace_root=True)
    expected_quality = {
        "bad_field_count_rows": 0,
        "pressure_row_count": 7,
        "nonpositive_pressure_rows": 1,
        "blank_pressure_rows": 0,
        "missing_test_year_rows": 0,
        "missing_county_name_rows": 2,
        "well_row_count": 4,
        "wells_invalid_api14_count": 1,
        "wells_missing_api10_count": 0,
        "wells_missing_depth_count": 0,
        "wells_date_parse_failure_count": 0,
        "row_count": 6,
        "observation_year_min": 1997,
        "observation_year_max": 1998,
        "hugoton_panoma_county_observation_count": 4,
        "missing_well_join_count": 2,
        "ambiguous_api10_join_count": 1,
        "ambiguous_identity_for_virgin_proxy_count": 1,
        "missing_depth_count": 4,
        "missing_county_name_count": 2,
        "missing_test_year_count": 0,
    }
    assert built.row_count == 6
    assert built.quality == expected_quality
    assert built.manifest is not None
    observations = load_pressure_observations(built.manifest.csv_path)
    flags = observations["quality_flags"].fillna("").str.split("|").map(set)
    assert flags.tolist() == [
        {""},
        {""},
        {"missing_well_join", "missing_depth", "missing_county_name"},
        {"missing_well_join", "missing_depth", "missing_county_name"},
        {
            "ambiguous_api10_join",
            "ambiguous_identity_for_virgin_proxy",
            "missing_depth",
        },
        {"invalid_api14", "missing_depth"},
    ]
    assert observations["is_earliest_observation_for_well"].iloc[:4].tolist() == [
        True,
        False,
        True,
        True,
    ]
    assert pd.isna(observations.iloc[4]["is_earliest_observation_for_well"])
    assert bool(observations.iloc[5]["is_earliest_observation_for_well"]) is True
    assert observations["gradient_psi_ft"].iloc[:2].tolist() == [0.0247, 0.0347]
    assert observations["gradient_psi_ft"].iloc[2:].isna().all()
    assert pd.isna(observations.iloc[5]["api14"])
    payload = json.loads(built.manifest.manifest_path.read_text())
    assert payload["row_count"] == 6
    assert payload["quality"] == expected_quality
    assert payload["code_revision"]
    assert isinstance(payload["code_dirty"], bool)
    assert len(payload["output_hashes"]) == 7
    for name, snapshot in payload["output_hashes"].items():
        path = (
            tmp_path
            if name.startswith("normalized/")
            else built.manifest.csv_path.parent
        ) / name
        assert snapshot == {
            "size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
