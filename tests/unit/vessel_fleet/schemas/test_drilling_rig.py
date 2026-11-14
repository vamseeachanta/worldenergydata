"""Tests for the drilling rig schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from worldenergydata.vessel_fleet.schemas.drilling_rig import DrillingRigSchema


class TestDrillingRigSchemaInheritance:
    def test_inherits_base_fields(self):
        schema = DrillingRigSchema(VESSEL_NAME="DEEPWATER TITAN")
        assert schema.VESSEL_NAME == "DEEPWATER TITAN"
        assert schema.OWNER is None

    def test_rig_specific_fields(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER TITAN",
            WATER_DEPTH_RATING_FT=12000.0,
            DRILLING_DEPTH_RATING_FT=40000.0,
            BOP_PRESSURE_PSI=15000.0,
        )
        assert schema.WATER_DEPTH_RATING_FT == 12000.0
        assert schema.DRILLING_DEPTH_RATING_FT == 40000.0
        assert schema.BOP_PRESSURE_PSI == 15000.0


class TestDrillingRigSchemaCoercion:
    def test_float_from_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", WATER_DEPTH_RATING_FT="12000")
        assert schema.WATER_DEPTH_RATING_FT == 12000.0

    def test_float_empty_to_none(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", WATER_DEPTH_RATING_FT="")
        assert schema.WATER_DEPTH_RATING_FT is None

    def test_string_empty_to_none(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", RIG_TYPE="")
        assert schema.RIG_TYPE is None

    def test_int_from_float_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", MUD_PUMP_COUNT="4.0")
        assert schema.MUD_PUMP_COUNT == 4

    def test_jackup_fields(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="VALARIS 105",
            LEG_LENGTH_FT="500",
            CANTILEVER_REACH_FT="75",
            PRELOAD_CAPACITY_ST="16000",
        )
        assert schema.LEG_LENGTH_FT == 500.0
        assert schema.CANTILEVER_REACH_FT == 75.0


class TestDrillingRigSchemaHullGeometry:
    """Hull geometry fields for RAO / diffraction analysis mapping."""

    def test_hull_form_type(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            HULL_FORM_TYPE="semi_sub",
        )
        assert schema.HULL_FORM_TYPE == "semi_sub"

    def test_hull_form_type_empty_to_none(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", HULL_FORM_TYPE="")
        assert schema.HULL_FORM_TYPE is None

    def test_semisub_pontoon_column_fields(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            HULL_FORM_TYPE="semi_sub",
            PONTOON_LENGTH_M=114.0,
            PONTOON_WIDTH_M=17.7,
            PONTOON_HEIGHT_M=10.4,
            COLUMN_DIAMETER_M=17.7,
            COLUMN_SPACING_M=58.6,
            COLUMN_COUNT=4,
        )
        assert schema.PONTOON_LENGTH_M == 114.0
        assert schema.PONTOON_WIDTH_M == 17.7
        assert schema.PONTOON_HEIGHT_M == 10.4
        assert schema.COLUMN_DIAMETER_M == 17.7
        assert schema.COLUMN_SPACING_M == 58.6
        assert schema.COLUMN_COUNT == 4

    def test_stability_parameters(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            GM_M=3.5,
            VCG_M=18.2,
        )
        assert schema.GM_M == 3.5
        assert schema.VCG_M == 18.2

    def test_hull_library_ref(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER ATLAS",
            HULL_LIBRARY_REF="semi_sub_gvA7500",
        )
        assert schema.HULL_LIBRARY_REF == "semi_sub_gvA7500"

    def test_pontoon_float_from_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", PONTOON_LENGTH_M="114.0")
        assert schema.PONTOON_LENGTH_M == 114.0

    def test_column_count_from_float_string(self):
        schema = DrillingRigSchema(VESSEL_NAME="T", COLUMN_COUNT="4.0")
        assert schema.COLUMN_COUNT == 4

    def test_negative_pontoon_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", PONTOON_LENGTH_M=-10)

    def test_negative_gm_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", GM_M=-1)

    def test_drillship_hull_form(self):
        schema = DrillingRigSchema(
            VESSEL_NAME="DEEPWATER PROTEUS",
            HULL_FORM_TYPE="drillship",
            LOA_M=238.0,
            BEAM_M=42.0,
            DRAFT_M=12.0,
            DISPLACEMENT_TONNES=96000.0,
        )
        assert schema.HULL_FORM_TYPE == "drillship"
        assert schema.LOA_M == 238.0


class TestDrillingRigSchemaValidation:
    def test_negative_water_depth_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", WATER_DEPTH_RATING_FT=-100)

    def test_negative_hookload_raises(self):
        with pytest.raises(Exception):
            DrillingRigSchema(VESSEL_NAME="T", HOOKLOAD_RATING_KIPS=-1)


# Independent inventory of the existing rig-specific float validator's fields.
# Unit suffixes are retained: each synthetic value is expressed in that field's
# declared unit, with no unit conversion expected during validation.
RIG_FLOAT_FIELDS = (
    "WATER_DEPTH_RATING_FT",
    "DRILLING_DEPTH_RATING_FT",
    "MAX_WATER_DEPTH_FT",
    "DERRICK_HEIGHT_FT",
    "HOOKLOAD_RATING_KIPS",
    "DRAWWORKS_HP",
    "ROTARY_TABLE_SIZE_IN",
    "TOP_DRIVE_CAPACITY_ST",
    "MUD_PUMP_HP",
    "BOP_PRESSURE_PSI",
    "BOP_SIZE_IN",
    "RISER_SIZE_IN",
    "RISER_LENGTH_FT",
    "MOONPOOL_LENGTH_M",
    "MOONPOOL_WIDTH_M",
    "MOONPOOL_DIAMETER_M",
    "VARIABLE_DECK_LOAD_ST",
    "DECK_AREA_SQ_FT",
    "LEG_LENGTH_FT",
    "CANTILEVER_REACH_FT",
    "CANTILEVER_CAPACITY_KIPS",
    "PRELOAD_CAPACITY_ST",
    "SPUD_CAN_DIAMETER_FT",
    "PONTOON_LENGTH_M",
    "PONTOON_WIDTH_M",
    "PONTOON_HEIGHT_M",
    "COLUMN_DIAMETER_M",
    "COLUMN_SPACING_M",
    "GM_M",
    "VCG_M",
    "MAST_HEIGHT_FT",
    "SETBACK_CAPACITY_KIPS",
    "CRANE_MAIN_CAPACITY_T",
)


@pytest.mark.parametrize("field", RIG_FLOAT_FIELDS)
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(float("inf"), id="numeric-infinity"),
        pytest.param(" Infinity ", id="text-infinity"),
        pytest.param(float("nan"), id="numeric-nan"),
        pytest.param(" NaN ", id="text-nan"),
        pytest.param(float("-inf"), id="numeric-negative-infinity"),
        pytest.param(" -inf ", id="text-negative-infinity"),
    ],
)
def test_nonfinite_rig_ratings_rejected(field, value):
    """By definition, neither signed infinity nor NaN is a finite real value."""
    with pytest.raises(ValidationError) as error:
        DrillingRigSchema(VESSEL_NAME="synthetic", **{field: value})

    assert {item["loc"] for item in error.value.errors()} == {(field,)}


@pytest.mark.parametrize("field", RIG_FLOAT_FIELDS)
@pytest.mark.parametrize("value", [None, "", " \t "], ids=["none", "empty", "blank"])
def test_nullable_rig_ratings_preserved(field, value):
    schema = DrillingRigSchema(VESSEL_NAME="synthetic", **{field: value})
    assert schema.model_dump()[field] is None


# Synthetic mathematical inputs, not engineering limits: zero is the additive
# identity; 1.25 = 5/4 is exactly representable in binary, as is its negative.
@pytest.mark.parametrize("field", RIG_FLOAT_FIELDS)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(0.0, 0.0, id="numeric-zero"),
        pytest.param("0", 0.0, id="text-zero"),
        pytest.param(1.25, 1.25, id="numeric-positive"),
        pytest.param(" 1.25 ", 1.25, id="text-positive"),
    ],
)
def test_finite_rig_ratings_round_trip_in_declared_units(field, value, expected):
    schema = DrillingRigSchema(VESSEL_NAME="synthetic", **{field: value})
    dumped = schema.model_dump()

    assert dumped[field] == expected
    assert type(dumped[field]) is float
    restored = DrillingRigSchema.model_validate(dumped)
    assert restored.model_dump() == dumped


@pytest.mark.parametrize("field", RIG_FLOAT_FIELDS)
@pytest.mark.parametrize("value", [-1.25, " -1.25 "], ids=["numeric", "text"])
def test_negative_rig_ratings_rejected(field, value):
    with pytest.raises(ValidationError) as error:
        DrillingRigSchema(VESSEL_NAME="synthetic", **{field: value})

    assert {item["loc"] for item in error.value.errors()} == {(field,)}
