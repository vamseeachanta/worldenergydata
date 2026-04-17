"""Pydantic schema for drilling rig records."""

from __future__ import annotations

from typing import Optional

from pydantic import field_validator

from worldenergydata.vessel_fleet.schemas.base import BaseVesselSchema


class DrillingRigSchema(BaseVesselSchema):
    """Schema for a drilling rig record.

    Extends BaseVesselSchema with rig-specific fields for water depth,
    drilling equipment, BOP, derrick, and rig configuration.
    """

    # Rig identification
    RIG_NAME: Optional[str] = None  # Alias for historical compatibility
    RIG_TYPE: Optional[str] = None
    RIG_STATUS: Optional[str] = None
    RIG_DESIGN: Optional[str] = None

    # Depth ratings (float, feet)
    WATER_DEPTH_RATING_FT: Optional[float] = None
    DRILLING_DEPTH_RATING_FT: Optional[float] = None
    MAX_WATER_DEPTH_FT: Optional[float] = None

    # Drilling equipment
    DERRICK_HEIGHT_FT: Optional[float] = None
    HOOKLOAD_RATING_KIPS: Optional[float] = None
    DRAWWORKS_HP: Optional[float] = None
    ROTARY_TABLE_SIZE_IN: Optional[float] = None
    TOP_DRIVE_CAPACITY_ST: Optional[float] = None
    MUD_PUMP_COUNT: Optional[int] = None
    MUD_PUMP_HP: Optional[float] = None

    # BOP
    BOP_PRESSURE_PSI: Optional[float] = None
    BOP_SIZE_IN: Optional[float] = None
    BOP_MANUFACTURER: Optional[str] = None

    # Riser
    RISER_SIZE_IN: Optional[float] = None
    RISER_LENGTH_FT: Optional[float] = None

    # Moonpool
    MOONPOOL_LENGTH_M: Optional[float] = None
    MOONPOOL_WIDTH_M: Optional[float] = None
    MOONPOOL_DIAMETER_M: Optional[float] = None

    # Deck
    VARIABLE_DECK_LOAD_ST: Optional[float] = None
    DECK_AREA_SQ_FT: Optional[float] = None

    # Jackup-specific
    LEG_LENGTH_FT: Optional[float] = None
    LEG_TYPE: Optional[str] = None
    CANTILEVER_REACH_FT: Optional[float] = None
    CANTILEVER_CAPACITY_KIPS: Optional[float] = None
    PRELOAD_CAPACITY_ST: Optional[float] = None
    SPUD_CAN_DIAMETER_FT: Optional[float] = None
    JU_DESIGN: Optional[str] = None

    # Hull geometry — for RAO / diffraction analysis mapping
    HULL_FORM_TYPE: Optional[str] = None  # semi_sub, drillship, jackup, barge, spar
    PONTOON_LENGTH_M: Optional[float] = None
    PONTOON_WIDTH_M: Optional[float] = None
    PONTOON_HEIGHT_M: Optional[float] = None
    COLUMN_DIAMETER_M: Optional[float] = None
    COLUMN_SPACING_M: Optional[float] = None
    COLUMN_COUNT: Optional[int] = None
    GM_M: Optional[float] = None  # Metacentric height
    VCG_M: Optional[float] = None  # Vertical centre of gravity
    HULL_LIBRARY_REF: Optional[str] = (
        None  # Cross-ref to digitalmodel hull_library catalog
    )

    # Onshore rig-specific
    MAST_HEIGHT_FT: Optional[float] = None
    WALKING_SYSTEM: Optional[bool] = None
    AC_SCR_POWER: Optional[str] = None
    SETBACK_CAPACITY_KIPS: Optional[float] = None
    RIG_MODEL: Optional[str] = None
    SUPER_SPEC: Optional[bool] = None

    # Well history
    WELLS_DRILLED_COUNT: Optional[int] = None
    LAST_WAR_DATE: Optional[str] = None
    FIRST_WAR_DATE: Optional[str] = None
    LAST_AREA_CODE: Optional[str] = None
    LAST_BLOCK_NUMBER: Optional[str] = None

    # Flag
    IS_OFFSHORE: Optional[bool] = None

    # --- Validators ---

    @field_validator(
        "RIG_TYPE",
        "RIG_STATUS",
        "RIG_DESIGN",
        "BOP_MANUFACTURER",
        "LEG_TYPE",
        "JU_DESIGN",
        "AC_SCR_POWER",
        "RIG_MODEL",
        "LAST_WAR_DATE",
        "FIRST_WAR_DATE",
        "LAST_AREA_CODE",
        "LAST_BLOCK_NUMBER",
        "HULL_FORM_TYPE",
        "HULL_LIBRARY_REF",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none_rig(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
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
        mode="before",
    )
    @classmethod
    def _coerce_rig_float_fields(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return float(v)
        return v

    @field_validator(
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
    )
    @classmethod
    def _validate_non_negative_rig_floats(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator(
        "MUD_PUMP_COUNT", "WELLS_DRILLED_COUNT", "COLUMN_COUNT", mode="before"
    )
    @classmethod
    def _coerce_rig_int_fields(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return int(float(v))
        if isinstance(v, float):
            return int(v)
        return v
