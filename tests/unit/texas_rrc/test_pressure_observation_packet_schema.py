"""Tests for Texas RRC pressure-observation packet schema maps."""

from __future__ import annotations

from worldenergydata.texas_rrc.pressure_observations.packet_schema import (
    PRESSURE_RECORD_SCHEMAS,
    field_index,
    pressure_fields_for,
)


def test_packet_schema_maps_g1_pressure_fields():
    assert "G-1" in PRESSURE_RECORD_SCHEMAS
    assert field_index("G-1", "BOTTOM_HOLE_PRESS") > 0
    assert field_index("G-1", "BOTTOM_HOLE_DEPTH") > 0
    assert field_index("G-1", "DATE_OF_TEST") > 0


def test_packet_schema_maps_g1_field_pressure_rows():
    assert pressure_fields_for("G-1 Field Data") == ("WELLHEAD_PRESS",)
    assert field_index("G-1 Field Data", "ROW_NO") > 0
    assert field_index("G-1 Field Data", "WELLHEAD_PRESS") > 0


def test_packet_schema_maps_g10_pressure_fields():
    assert pressure_fields_for("G-10") == (
        "XBHOLE_PRESSURE",
        "SIWH_PRESSURE",
        "FLOWING_PRESSURE",
    )
    assert field_index("G-10", "DATE_TESTED") > 0
    assert field_index("G-10", "REASON_CODE") > 0


def test_packet_schema_maps_interval_and_formation_rows():
    assert field_index("G-1 Production Interval Data", "FROM") > 0
    assert field_index("G-1 Production Interval Data", "TO") > 0
    assert field_index("W-2 Production Interval Data", "BOTTOM_HOLE_LABEL") > 0
    assert field_index("G-1 Formation Data", "FORMATION") > 0
    assert field_index("W-2 Formation Data", "DEPTH") > 0


def test_w2_pressure_like_fields_are_candidates_not_bhp_fields():
    assert "W-2" in PRESSURE_RECORD_SCHEMAS
    assert "CALC_CASING_PRESS" in pressure_fields_for("W-2")
    assert "BOTTOM_HOLE_PRESS" not in pressure_fields_for("W-2")
