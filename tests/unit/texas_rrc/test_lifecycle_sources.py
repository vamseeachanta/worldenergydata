"""Tests for loading Texas RRC lifecycle source snapshots."""

from __future__ import annotations

import zipfile
from pathlib import Path

from worldenergydata.texas_rrc.lifecycle.sources import load_lifecycle_inputs


def _fixed_record(
    *, record_type: str, length: int = 512, values: dict[int, str]
) -> str:
    chars = [" "] * length
    chars[2:4] = record_type
    for start, value in values.items():
        index = start - 1
        chars[index : index + len(value)] = value
    return "".join(chars)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_zip(path: Path, member_name: str, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(member_name, content)


def test_load_lifecycle_inputs_reads_local_raw_snapshots(tmp_path):
    _write_zip(
        tmp_path / "raw/wellbore/query/wellbore.zip",
        "OG_WELLBORE_EWA_Report.csv",
        "\n".join(
            [
                "API_NO,DISTRICT_NO,FIELD_NO,LEASE_NO,OPERATOR_NO,WELL_STATUS",
                "4200100001,08,12345,98765,456789,A",
            ]
        ),
    )
    _write_text(
        tmp_path / "raw/permits/drilling/daf420.dat",
        "\n".join(
            [
                "API_NO|PERMIT_NO|APPROVED_DATE|SPUD_DATE|LATITUDE|LONGITUDE",
                "4200100001|999001|2024-01-15|2024-02-01|31.5|-97.2",
            ]
        ),
    )
    _write_zip(
        tmp_path / "raw/completions/06-30-2026.zip",
        "completion.csv",
        "\n".join(
            [
                "API_NO,COMPL_DATE,FORM_TYPE,FIELD_NO,LEASE_NO,OPERATOR_NO",
                "4200100001,2024-03-01,W-2,12345,98765,456789",
            ]
        ),
    )

    inputs = load_lifecycle_inputs(tmp_path)

    assert inputs.source_gaps == ()
    assert inputs.wellbores.iloc[0].to_dict() == {
        "api_number": "4200100001",
        "district": "08",
        "field_number": "12345",
        "lease_number": "98765",
        "operator_number": "456789",
        "well_status": "A",
    }
    assert inputs.permits.iloc[0]["permit_number"] == "999001"
    assert inputs.permits.iloc[0]["spud_date"] == "2024-02-01"
    assert inputs.completions.iloc[0]["completion_date"] == "2024-03-01"
    assert inputs.completions.iloc[0]["form_type"] == "W-2"


def test_load_lifecycle_inputs_reads_official_daf420_fixed_records(tmp_path):
    master_record = _fixed_record(
        record_type="02",
        values={
            5: "0999001",
            14: "001",
            17: "SPRABERRY UNIT                  ",
            49: "08",
            57: "12000",
            62: "456789",
            68: "12",
            132: "20240115",
            140: "20240201",
            148: "20250115",
            156: "20240220",
            505: "00100001",
        },
    )
    surface_location_record = _fixed_record(
        record_type="14",
        length=28,
        values={
            5: "000972000000",
            17: "000315000000",
        },
    )
    _write_text(
        tmp_path / "raw/permits/drilling/daf420.dat",
        "\n".join([master_record, surface_location_record]),
    )

    inputs = load_lifecycle_inputs(tmp_path)

    assert inputs.source_gaps == ("wellbore_query", "completion_data")
    assert inputs.permits.iloc[0].to_dict() == {
        "api_number": "00100001",
        "permit_number": "0999001",
        "permit_type": "12",
        "district": "08",
        "lease_name": "SPRABERRY UNIT",
        "operator_number": "456789",
        "permit_issued_date": "2024-01-15",
        "permit_amended_date": "2024-02-01",
        "permit_extended_date": "2025-01-15",
        "spud_date": "2024-02-20",
        "latitude": "31.5",
        "longitude": "-97.2",
        "total_depth": "12000",
    }


def test_load_lifecycle_inputs_maps_official_completion_date_alias(tmp_path):
    _write_zip(
        tmp_path / "raw/completions/06-30-2026.zip",
        "completion.csv",
        "\n".join(
            [
                "API_NO,CMPL_OR_RECMPL_DATE,FORM_TYPE",
                "00100001,2024-03-01,W-2",
            ]
        ),
    )

    inputs = load_lifecycle_inputs(tmp_path)

    assert inputs.source_gaps == ("wellbore_query", "drilling_permits")
    assert inputs.completions.iloc[0]["api_number"] == "00100001"
    assert inputs.completions.iloc[0]["completion_date"] == "2024-03-01"
