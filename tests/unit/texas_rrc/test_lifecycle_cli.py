"""CLI tests for Texas RRC lifecycle normalization."""

from __future__ import annotations

import json
from pathlib import Path
import zipfile

from typer.testing import CliRunner

from worldenergydata.cli.commands.texas_rrc import app


def test_normalize_lifecycle_cli_writes_curated_outputs(tmp_path):
    raw_root = tmp_path / "rrc"
    output_root = tmp_path / "out"
    _write_lifecycle_fixture(raw_root)

    result = CliRunner().invoke(
        app,
        [
            "normalize-lifecycle",
            "--raw-root",
            str(raw_root),
            "--output-root",
            str(output_root),
            "--allow-non-ace-output",
        ],
    )

    assert result.exit_code == 0, result.output
    spine_path = (
        output_root
        / "curated"
        / "well_lifecycle"
        / "spine"
        / "well_lifecycle_spine.csv"
    )
    quality_path = spine_path.with_name("well_lifecycle_quality.json")
    manifest_path = spine_path.with_name("manifest.json")
    assert spine_path.exists()
    assert quality_path.exists()
    assert manifest_path.exists()
    assert "Wrote lifecycle spine" in result.output
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["row_count"] == 1
    assert manifest["input_paths"]


def _write_lifecycle_fixture(root: Path) -> None:
    _write_zip(
        root / "raw/wellbore/query/wellbore.zip",
        "OG_WELLBORE_EWA_Report.csv",
        "\n".join(
            [
                "API_NO,DISTRICT_NO,FIELD_NO,LEASE_NO,OPERATOR_NO,WELL_STATUS",
                "4200100001,08,12345,98765,456789,A",
            ]
        ),
    )
    _write_text(
        root / "raw/permits/drilling/daf420.dat",
        "\n".join(
            [
                "API_NO|PERMIT_NO|APPROVED_DATE|SPUD_DATE|LATITUDE|LONGITUDE",
                "4200100001|999001|2024-01-15|2024-02-01|31.5|-97.2",
            ]
        ),
    )
    _write_zip(
        root / "raw/completions/06-30-2026.zip",
        "completion.csv",
        "\n".join(
            [
                "API_NO,COMPL_DATE,FORM_TYPE,FIELD_NO,LEASE_NO,OPERATOR_NO",
                "4200100001,2024-03-01,W-2,12345,98765,456789",
            ]
        ),
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_zip(path: Path, member_name: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member_name, content)
