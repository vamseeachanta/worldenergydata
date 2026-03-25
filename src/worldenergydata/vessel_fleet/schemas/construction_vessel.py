"""Pydantic schema for construction and service vessel records."""

from __future__ import annotations

from typing import Optional

from pydantic import field_validator

from worldenergydata.vessel_fleet.schemas.base import BaseVesselSchema


class ConstructionVesselSchema(BaseVesselSchema):
    """Schema for a construction or service vessel record.

    Extends BaseVesselSchema with fields specific to crane vessels,
    pipelay vessels, heavy-lift, wind installation, and similar.
    """

    # Crane
    MAIN_CRANE_CAPACITY_T: Optional[float] = None
    MAIN_CRANE_REACH_M: Optional[float] = None
    AUX_CRANE_CAPACITY_T: Optional[float] = None
    AUX_CRANE_REACH_M: Optional[float] = None

    # Pipelay
    PIPELAY_CAPACITY_IN: Optional[float] = None
    PIPELAY_TENSION_T: Optional[float] = None
    PIPELAY_METHOD: Optional[str] = None

    # Deck
    DECK_AREA_M2: Optional[float] = None
    DECK_LOAD_CAPACITY_T: Optional[float] = None

    # Operational
    BOLLARD_PULL_T: Optional[float] = None
    HEAVY_LIFT_CAPACITY_T: Optional[float] = None
    WATER_DEPTH_RATING_M: Optional[float] = None

    # Equipment
    ROV_SYSTEMS: Optional[int] = None
    MOONPOOL: Optional[bool] = None

    # Wind installation
    TURBINE_CAPACITY_MW: Optional[float] = None
    FOUNDATION_TYPE: Optional[str] = None

    # --- Validators ---

    @field_validator(
        "PIPELAY_METHOD", "FOUNDATION_TYPE",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none_cv(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "MAIN_CRANE_CAPACITY_T", "MAIN_CRANE_REACH_M",
        "AUX_CRANE_CAPACITY_T", "AUX_CRANE_REACH_M",
        "PIPELAY_CAPACITY_IN", "PIPELAY_TENSION_T",
        "DECK_AREA_M2", "DECK_LOAD_CAPACITY_T",
        "BOLLARD_PULL_T", "HEAVY_LIFT_CAPACITY_T",
        "WATER_DEPTH_RATING_M", "TURBINE_CAPACITY_MW",
        mode="before",
    )
    @classmethod
    def _coerce_cv_float_fields(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return float(v)
        return v

    @field_validator(
        "MAIN_CRANE_CAPACITY_T", "MAIN_CRANE_REACH_M",
        "AUX_CRANE_CAPACITY_T", "AUX_CRANE_REACH_M",
        "PIPELAY_CAPACITY_IN", "PIPELAY_TENSION_T",
        "DECK_AREA_M2", "DECK_LOAD_CAPACITY_T",
        "BOLLARD_PULL_T", "HEAVY_LIFT_CAPACITY_T",
        "WATER_DEPTH_RATING_M", "TURBINE_CAPACITY_MW",
    )
    @classmethod
    def _validate_non_negative_cv_floats(
        cls, v: Optional[float],
    ) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator("ROV_SYSTEMS", mode="before")
    @classmethod
    def _coerce_cv_int_fields(cls, v: object) -> object:
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
