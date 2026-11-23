"""Tests for parsing Texas RRC pressure-observation packet rows."""

from __future__ import annotations

from worldenergydata.texas_rrc.pressure_observations.packets import (
    read_packet_pressure_candidates,
)


def _packet_line(values: dict[int, str], length: int = 61) -> str:
    columns = [""] * length
    columns[0] = "PACKET"
    for index, value in values.items():
        columns[index] = value
    return "{".join(columns)


def _record_line(record_type: str, values: dict[int, str], length: int = 90) -> str:
    columns = [""] * length
    columns[0] = record_type
    for index, value in values.items():
        columns[index] = value
    return "{".join(columns)


def _packet_context() -> str:
    return _packet_line(
        {
            1: "123456",
            2: "654321",
            5: "456789",
            6: "00100001",
            8: "98765",
            25: "12345678",
            27: "08",
            29: "SPRABERRY",
        }
    )


def test_packet_parser_links_g1_pressure_to_packet_context():
    text = "\n".join(
        [
            "123456{G-1{Packet Data(1)",
            _packet_context(),
            _record_line(
                "G-1",
                {
                    1: "123456",
                    2: "654321",
                    3: "999",
                    4: "03/01/2024",
                    13: "10000",
                    59: "2500",
                },
            ),
        ]
    )

    result = read_packet_pressure_candidates(text, source_file="packet.dat")

    assert result.malformed_row_count == 0
    assert result.unlinked_row_count == 0
    row = result.candidates.iloc[0].to_dict()
    assert row["api14"] == "42001000010000"
    assert row["api10"] == "4200100001"
    assert row["district"] == "08"
    assert row["field_no"] == "12345678"
    assert row["field_name"] == "SPRABERRY"
    assert row["test_date"] == "2024-03-01"
    assert row["source_record_type"] == "G-1"
    assert row["source_pressure_field"] == "BOTTOM_HOLE_PRESS"
    assert row["pressure_raw_psi"] == 2500.0
    assert row["source_tracking_no"] == "123456"
    assert row["source_packet_id"] == "654321"
    assert row["source_form_id"] == "999"
    assert row["source_file"] == "packet.dat"


def test_packet_parser_links_g1_interval_depth_to_pressure_candidate():
    text = "\n".join(
        [
            _packet_context(),
            _record_line(
                "G-1",
                {
                    1: "123456",
                    2: "654321",
                    3: "999",
                    4: "03/01/2024",
                    13: "10000",
                    59: "2500",
                },
            ),
            _record_line(
                "G-1 Production Interval Data",
                {
                    1: "123456",
                    2: "654321",
                    3: "999",
                    4: "1",
                    5: "1000",
                    6: "1200",
                },
                length=10,
            ),
        ]
    )

    result = read_packet_pressure_candidates(text, source_file="packet.dat")

    row = result.candidates.iloc[0].to_dict()
    assert row["production_interval_from_ft"] == 1000.0
    assert row["production_interval_to_ft"] == 1200.0
    assert row["reference_formation"] == ""


def test_packet_parser_links_g1_field_shut_in_wellhead_pressure():
    text = "\n".join(
        [
            _packet_context(),
            _record_line(
                "G-1",
                {1: "123456", 2: "654321", 3: "999", 4: "03/01/2024"},
            ),
            _record_line(
                "G-1 Field Data",
                {
                    1: "123456",
                    2: "654321",
                    3: "999",
                    4: "SHUT-IN",
                    7: "1032",
                },
                length=9,
            ),
        ]
    )

    result = read_packet_pressure_candidates(text, source_file="packet.dat")

    row = result.candidates.iloc[0].to_dict()
    assert row["source_record_type"] == "G-1 Field Data"
    assert row["source_pressure_field"] == "WELLHEAD_PRESS"
    assert row["pressure_raw_psi"] == 1032.0
    assert row["source_row_no"] == "SHUT-IN"
    assert row["test_date"] == "2024-03-01"


def test_packet_parser_links_g10_pressure_rows_to_packet_context():
    text = "\n".join(
        [
            _packet_context(),
            _record_line(
                "G-10",
                {
                    1: "123456",
                    2: "654321",
                    3: "777",
                    4: "2",
                    10: "2500",
                    12: "04/15/2024",
                    17: "1200",
                    18: "950",
                },
                length=20,
            ),
        ]
    )

    result = read_packet_pressure_candidates(text, source_file="packet.dat")

    assert list(result.candidates["source_pressure_field"]) == [
        "XBHOLE_PRESSURE",
        "SIWH_PRESSURE",
        "FLOWING_PRESSURE",
    ]
    assert set(result.candidates["source_form_id"]) == {"777"}
    assert set(result.candidates["test_date"]) == {"2024-04-15"}


def test_packet_parser_counts_unlinked_and_malformed_rows():
    text = "\n".join(
        [
            "G-1{123456",
            _record_line(
                "G-1 Field Data",
                {1: "999999", 2: "888888", 3: "777", 4: "SHUT-IN", 7: "1000"},
                length=9,
            ),
        ]
    )

    result = read_packet_pressure_candidates(text, source_file="bad.dat")

    assert result.candidates.empty
    assert result.malformed_row_count == 1
    assert result.unlinked_row_count == 1
