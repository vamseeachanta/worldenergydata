"""Tests for Kansas KGS proration pressure parsing."""

from __future__ import annotations

from pathlib import Path


def test_proration_parser_repairs_malformed_second_line(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.pressure import parse_proration_pressure

    pressure_path = tmp_path / "kansas_proration_pressures.txt"
    pressure_path.write_text(_pressure_fixture(), encoding="utf-8")

    parsed = parse_proration_pressure(pressure_path)

    assert parsed.quality["bad_field_count_rows"] == 2
    assert parsed.normalized.shape[0] == 3
    assert "WORKING_PRES" in parsed.normalized.columns
    assert " WORKING_PRES" not in parsed.normalized.columns


def test_proration_parser_preserves_zero_and_normalizes_api(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.pressure import parse_proration_pressure

    pressure_path = tmp_path / "kansas_proration_pressures.txt"
    pressure_path.write_text(_pressure_fixture(), encoding="utf-8")

    normalized = parse_proration_pressure(pressure_path).normalized

    zero_row = normalized.loc[normalized["test_year"].eq(1996)].iloc[0]
    assert zero_row["pressure_psig_raw"] == 0.0
    assert zero_row["api10"] == "1506720048"
    assert zero_row["api_state_code"] == "15"
    assert zero_row["api_county_code"] == "067"
    assert zero_row["county_name"] == "Grant"
    assert zero_row["well_kid"] == "1001232609"


def test_proration_parser_sets_pressure_fields_and_test_policy(
    tmp_path: Path,
) -> None:
    from worldenergydata.kansas_kgs.pressure import parse_proration_pressure

    pressure_path = tmp_path / "kansas_proration_pressures.txt"
    pressure_path.write_text(_pressure_fixture(), encoding="utf-8")

    normalized = parse_proration_pressure(pressure_path).normalized
    positive = normalized.loc[normalized["test_year"].eq(1997)].iloc[0]

    assert positive["pressure_psig_raw"] == 47.3
    assert positive["working_pressure_psig"] == 38.8
    assert positive["open_flow"] == 1022.0
    assert positive["test_type"] == "KS_PRORATION"
    assert positive["test_date"] is None


def test_proration_parser_counts_non_observation_pressure_rows(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.pressure import parse_proration_pressure

    pressure_path = tmp_path / "kansas_proration_pressures.txt"
    pressure_path.write_text(_pressure_fixture(), encoding="utf-8")

    parsed = parse_proration_pressure(pressure_path)

    assert parsed.quality["nonpositive_pressure_rows"] == 1
    assert parsed.quality["blank_pressure_rows"] == 0
    assert parsed.quality["missing_test_year_rows"] == 0
    assert parsed.quality["missing_county_name_rows"] == 0


def test_proration_parser_tolerates_legacy_high_byte_text(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.pressure import parse_proration_pressure

    pressure_path = tmp_path / "kansas_proration_pressures.txt"
    pressure_path.write_bytes(
        _pressure_fixture().replace("POWELL", "PE\xd1A").encode("latin-1")
    )

    parsed = parse_proration_pressure(pressure_path)

    assert parsed.normalized.shape[0] == 3


def test_proration_parser_empty_valid_rows_returns_schema(tmp_path: Path) -> None:
    from worldenergydata.kansas_kgs.pressure import (
        NORMALIZED_PRESSURE_COLUMNS,
        parse_proration_pressure,
    )

    pressure_path = tmp_path / "kansas_proration_pressures.txt"
    pressure_path.write_text(
        "WELL_KID,API_NUMBER,YEAR,SHUT_IN_PRESS\nbad,too,short\n",
        encoding="utf-8",
    )

    parsed = parse_proration_pressure(pressure_path)

    assert parsed.normalized.empty
    assert list(parsed.normalized.columns) == NORMALIZED_PRESSURE_COLUMNS
    assert parsed.quality["bad_field_count_rows"] == 1


def _pressure_fixture() -> str:
    return "\n".join(
        [
            "WELL_KID, LEASE, API_NUMBER, OPERATOR, TOWNSHIP, TWN_DIR, RANGE, "
            "RANGE_DIR, SECTION, LATITUDE, LONGITUDE, YEAR, ACREAGE, "
            "SHUT_IN_PRESS, WORKING_PRES,DAILY_RATE, OPEN_FLOW, ADJ_DELIVER, "
            "WATER_PROD,METER_PRES, DIFFERENT, COEFF",
            'RES","DIFFERENT","COEFF"',
            '"1001232609","POWELL 2-31","15-067-20048","MESA","29","S",'
            '"37","W","31","37.4789143","-101.4114608","1996","636",'
            '"0","0","0","0","1297","0","0","0","0"',
            '"1001232609","POWELL 2-31","15-067-20048","MESA","29","S",'
            '"37","W","31","37.4789143","-101.4114608","1997","636",'
            '"47.3","38.8","337.26","1022","645","0","38.3","10.58","12.1"',
            '"1007777777","STEVENS 1","15-189-20001","KGS OP","30","S",'
            '"39","W","1","37.2","-101.0","1998","640",'
            '"90","70","10","100","100","0","20","1","2"',
            '"bad","too","short"',
            "",
        ]
    )
