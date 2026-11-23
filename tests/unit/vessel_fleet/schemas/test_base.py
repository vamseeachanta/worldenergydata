"""Tests for the base vessel schema."""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.schemas.base import BaseVesselSchema


class TestBaseVesselSchemaRequired:
    def test_vessel_name_required(self):
        schema = BaseVesselSchema(VESSEL_NAME="Test Vessel")
        assert schema.VESSEL_NAME == "Test Vessel"

    def test_missing_vessel_name_raises(self):
        with pytest.raises(Exception):
            BaseVesselSchema()

    def test_vessel_name_strips_quotes(self):
        schema = BaseVesselSchema(VESSEL_NAME='"DEEPWATER TITAN"')
        assert schema.VESSEL_NAME == "DEEPWATER TITAN"

    def test_vessel_name_strips_whitespace(self):
        schema = BaseVesselSchema(VESSEL_NAME="  TEST  ")
        assert schema.VESSEL_NAME == "TEST"


class TestBaseVesselSchemaCoercion:
    def test_empty_string_to_none(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", OWNER="")
        assert schema.OWNER is None

    def test_whitespace_string_to_none(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", OWNER="   ")
        assert schema.OWNER is None

    def test_float_from_string(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", LOA_M="228.5")
        assert schema.LOA_M == 228.5

    def test_float_empty_to_none(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", LOA_M="")
        assert schema.LOA_M is None

    def test_int_from_string(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT="2014")
        assert schema.YEAR_BUILT == 2014

    def test_int_from_float_string(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT="2014.0")
        assert schema.YEAR_BUILT == 2014

    def test_int_from_float(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", DP_CLASS=2.0)
        assert schema.DP_CLASS == 2

    def test_int_empty_to_none(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT="")
        assert schema.YEAR_BUILT is None


class TestBaseVesselSchemaValidation:
    def test_negative_loa_raises(self):
        with pytest.raises(Exception):
            BaseVesselSchema(VESSEL_NAME="T", LOA_M=-1.0)

    def test_zero_loa_ok(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", LOA_M=0.0)
        assert schema.LOA_M == 0.0

    def test_year_built_too_old_raises(self):
        with pytest.raises(Exception):
            BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT=1800)

    def test_year_built_too_new_raises(self):
        with pytest.raises(Exception):
            BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT=2050)

    def test_year_built_valid(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", YEAR_BUILT=2020)
        assert schema.YEAR_BUILT == 2020

    def test_imo_number_valid(self):
        schema = BaseVesselSchema(VESSEL_NAME="T", IMO_NUMBER="1234567")
        assert schema.IMO_NUMBER == "1234567"

    def test_imo_number_wrong_length_raises(self):
        with pytest.raises(Exception):
            BaseVesselSchema(VESSEL_NAME="T", IMO_NUMBER="123456")

    def test_imo_number_non_digit_raises(self):
        with pytest.raises(Exception):
            BaseVesselSchema(VESSEL_NAME="T", IMO_NUMBER="123456A")
