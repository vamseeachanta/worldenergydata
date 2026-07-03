"""CLI tests for Kansas KGS pressure observations."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

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
