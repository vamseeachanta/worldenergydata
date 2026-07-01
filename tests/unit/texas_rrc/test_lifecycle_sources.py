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


def _fixed_record_with_leading_type(
    *, record_type: str, length: int = 510, values: dict[int, str]
) -> str:
    chars = [" "] * length
    chars[0:2] = record_type
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


def _official_wellbore_query_row() -> str:
    columns = [""] * 59
    columns[0] = "06"
    columns[1] = "001"
    columns[2] = "00100001"
    columns[3] = "ANDERSON"
    columns[4] = "O"
    columns[5] = "7-11 RANCH -B-"
    columns[6] = "16481001"
    columns[7] = "CAYUGA"
    columns[8] = "04411"
    columns[9] = "1"
    columns[11] = "SUPREME ENERGY COMPANY  INC."
    columns[12] = "830589"
    columns[13] = "Land Well"
    columns[15] = "4023"
    columns[18] = "SHUT IN"
    columns[20] = "20250201"
    columns[27] = "4644117776"
    columns[28] = "19840112"
    columns[29] = "19631205"
    columns[30] = "19631027"
    columns[58] = "0"
    return ",".join(f'"{value}"' for value in columns)


def _completion_packet_line(values: dict[int, str], length: int) -> str:
    columns = [""] * length
    for index, value in values.items():
        columns[index] = value
    return "{".join(columns)


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


def test_load_lifecycle_inputs_reads_official_headerless_wellbore_query(
    tmp_path,
):
    _write_text(
        tmp_path / "raw/wellbore/query/OG_WELLBORE_EWA_Report.csv",
        _official_wellbore_query_row(),
    )

    inputs = load_lifecycle_inputs(tmp_path)

    assert inputs.source_gaps == ("drilling_permits", "completion_data")
    assert inputs.wellbores.iloc[0].to_dict() == {
        "district": "06",
        "api_number": "00100001",
        "well_type": "O",
        "lease_name": "7-11 RANCH -B-",
        "field_number": "16481001",
        "field_name": "CAYUGA",
        "lease_number": "04411",
        "operator_name": "SUPREME ENERGY COMPANY  INC.",
        "operator_number": "830589",
        "total_depth": "4023",
        "well_status": "SHUT IN",
        "plug_date": "2025-02-01",
        "completion_date": "1963-10-27",
    }


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


def test_load_lifecycle_inputs_prefers_leading_daf420_record_type(tmp_path):
    master_record = _fixed_record_with_leading_type(
        record_type="02",
        values={
            3: "1400001",
            12: "001",
            15: "MIDLAND UNIT                    ",
            47: "08",
            55: "10500",
            60: "456789",
            66: "01",
            130: "20240115",
            154: "20240220",
            503: "00100002",
        },
    )
    _write_text(tmp_path / "raw/permits/drilling/daf420.dat", master_record)

    inputs = load_lifecycle_inputs(tmp_path)

    assert inputs.source_gaps == ("wellbore_query", "completion_data")
    assert inputs.permits.iloc[0]["api_number"] == "00100002"
    assert inputs.permits.iloc[0]["permit_number"] == "1400001"
    assert inputs.permits.iloc[0]["spud_date"] == "2024-02-20"


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


def test_load_lifecycle_inputs_reads_official_completion_packet_data(tmp_path):
    packet = _completion_packet_line(
        {
            0: "PACKET",
            1: "123456",
            2: "654321",
            3: "06/29/2026",
            6: "00100001",
            25: "12345678",
            27: "08",
            29: "SPRABERRY",
        },
        61,
    )
    form = _completion_packet_line(
        {
            0: "W-2",
            1: "123456",
            2: "654321",
            3: "999999",
            27: "03/01/2024",
        },
        83,
    )
    _write_zip(
        tmp_path / "raw/completions/06-30-2026.zip",
        "08/trackingNo_123456/packetData_123456_Approved.dat",
        "\n".join(
            [
                "123456{W-2{Plat(1)",
                "",
                packet,
                form,
                "W-2 Casing Data{123456{654321{999999{1{8 5/8",
            ]
        ),
    )

    inputs = load_lifecycle_inputs(tmp_path)

    assert inputs.source_gaps == ("wellbore_query", "drilling_permits")
    assert inputs.completions.iloc[0]["api_number"] == "00100001"
    assert inputs.completions.iloc[0]["completion_date"] == "2024-03-01"
    assert inputs.completions.iloc[0]["form_type"] == "W-2"
    assert inputs.completions.iloc[0]["district"] == "08"
    assert inputs.completions.iloc[0]["field_number"] == "12345678"
