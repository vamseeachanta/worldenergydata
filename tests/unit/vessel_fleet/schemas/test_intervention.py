# ABOUTME: Tests for the well-intervention vessel schema and new enum members.
# ABOUTME: Covers real units (Helix Q4000/Q5000/Q7000, Island Performer) round-trip.

"""Tests for the intervention vessel schema."""

from __future__ import annotations

import pytest

from worldenergydata.vessel_fleet.constants import VesselCategory, VesselType
from worldenergydata.vessel_fleet.schemas.intervention_vessel import (
    InterventionVesselSchema,
)


class TestNewEnumMembers:
    def test_intervention_vessel_category_exists(self):
        assert VesselCategory.INTERVENTION_VESSEL.value == "intervention_vessel"

    def test_new_vessel_types_exist(self):
        assert VesselType.RLWI_MONOHULL.value == "rlwi_monohull"
        assert VesselType.HEAVY_INTERVENTION_SEMI.value == "heavy_intervention_semi"
        assert VesselType.MPSV.value == "mpsv"


class TestInterventionVesselSchemaInheritance:
    def test_inherits_base_fields(self):
        schema = InterventionVesselSchema(VESSEL_NAME="Q4000")
        assert schema.VESSEL_NAME == "Q4000"
        assert schema.OWNER is None

    def test_base_field_validation_still_applies(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="Q4000",
            YEAR_BUILT="2002",
            LOA_M="156.0",
        )
        assert schema.YEAR_BUILT == 2002
        assert schema.LOA_M == 156.0

    def test_base_validation_rejects_bad_year(self):
        with pytest.raises(Exception):
            InterventionVesselSchema(VESSEL_NAME="Q4000", YEAR_BUILT=1800)


class TestRealUnits:
    def test_helix_q4000(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="Q4000",
            VESSEL_CATEGORY=VesselCategory.INTERVENTION_VESSEL.value,
            VESSEL_TYPE=VesselType.HEAVY_INTERVENTION_SEMI.value,
            WATER_DEPTH_RATING_M=3048.0,
            RISER_CAPABLE=True,
            INTERVENTION_CLASS="heavy",
            CT_CAPABLE=True,
            GOM_RESIDENT=True,
        )
        assert schema.VESSEL_NAME == "Q4000"
        assert schema.WATER_DEPTH_RATING_M == 3048.0
        assert schema.RISER_CAPABLE is True
        assert schema.INTERVENTION_CLASS == "heavy"
        assert schema.CT_CAPABLE is True
        assert schema.GOM_RESIDENT is True
        assert schema.VESSEL_TYPE == "heavy_intervention_semi"

    def test_helix_q5000(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="Q5000",
            WATER_DEPTH_RATING_M=3048.0,
            RISER_CAPABLE=True,
            INTERVENTION_CLASS="heavy",
            WELL_CONTROL_PACKAGE="15K IRS",
        )
        assert schema.WATER_DEPTH_RATING_M == 3048.0
        assert schema.INTERVENTION_CLASS == "heavy"
        assert schema.WELL_CONTROL_PACKAGE == "15K IRS"

    def test_helix_q7000(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="Q7000",
            WATER_DEPTH_RATING_M=3000.0,
            RISER_CAPABLE=True,
            INTERVENTION_CLASS="heavy",
            IRS_SYSTEM="Helix IRS-3",
        )
        assert schema.WATER_DEPTH_RATING_M == 3000.0
        assert schema.RISER_CAPABLE is True
        assert schema.IRS_SYSTEM == "Helix IRS-3"

    def test_island_performer_rlwi(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="Island Performer",
            VESSEL_TYPE=VesselType.RLWI_MONOHULL.value,
            WATER_DEPTH_RATING_M=2000.0,
            RISER_CAPABLE=False,
            INTERVENTION_CLASS="light",
            SUBSEA_LUBRICATOR=True,
        )
        assert schema.WATER_DEPTH_RATING_M == 2000.0
        assert schema.RISER_CAPABLE is False
        assert schema.INTERVENTION_CLASS == "light"
        assert schema.SUBSEA_LUBRICATOR is True
        assert schema.VESSEL_TYPE == "rlwi_monohull"


class TestInterventionVesselSchemaCoercion:
    def test_float_from_string(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="T",
            WATER_DEPTH_RATING_M="3048",
        )
        assert schema.WATER_DEPTH_RATING_M == 3048.0

    def test_float_empty_to_none(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="T",
            WATER_DEPTH_RATING_M="",
        )
        assert schema.WATER_DEPTH_RATING_M is None

    def test_string_empty_to_none(self):
        schema = InterventionVesselSchema(
            VESSEL_NAME="T",
            INTERVENTION_CLASS="",
            IRS_SYSTEM="",
        )
        assert schema.INTERVENTION_CLASS is None
        assert schema.IRS_SYSTEM is None


class TestInterventionVesselSchemaValidation:
    def test_negative_water_depth_raises(self):
        with pytest.raises(Exception):
            InterventionVesselSchema(
                VESSEL_NAME="T",
                WATER_DEPTH_RATING_M=-1,
            )

    def test_invalid_intervention_class_raises(self):
        with pytest.raises(Exception):
            InterventionVesselSchema(
                VESSEL_NAME="T",
                INTERVENTION_CLASS="medium",
            )
