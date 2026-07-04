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

    # Pipelay firing line (#701 — 2011 pipelay/burial poster backfill).
    # PIPELAY_CAPACITY_IN remains the MAX lay diameter; the new
    # PIPELAY_MIN_DIAMETER_IN completes the min/max pair.
    WELDING_STATIONS_COUNT: Optional[int] = None
    TOTAL_STATIONS_COUNT: Optional[int] = None
    NDT_STATIONS_COUNT: Optional[int] = None
    WELDING_METHOD: Optional[str] = None  # manual / automatic / manual+automatic
    TENSIONER_COUNT: Optional[int] = None
    PIPELAY_MIN_DIAMETER_IN: Optional[float] = None

    # Install-method detail (beyond the single PIPELAY_METHOD string)
    SLAY_CENTER_CAPABLE: Optional[bool] = None
    SLAY_SIDE_CAPABLE: Optional[bool] = None
    JLAY_CAPABLE: Optional[bool] = None
    REEL_PERMANENT_CAPABLE: Optional[bool] = None
    REEL_REMOVABLE_CAPABLE: Optional[bool] = None
    CAROUSEL_CAPABLE: Optional[bool] = None
    TOW_INSTALL_CAPABLE: Optional[bool] = None
    TOW_METHODS: Optional[str] = None  # e.g. "surface,mid-depth,on-bottom"

    # Burial capability
    BURIAL_CAPABLE: Optional[bool] = None
    SIMULTANEOUS_LAY_BURY_CAPABLE: Optional[bool] = None
    BURIAL_MIN_DIAMETER_IN: Optional[float] = None
    BURIAL_MAX_DIAMETER_IN: Optional[float] = None
    BURIAL_MAX_WATER_DEPTH_M: Optional[float] = None

    # Water-depth envelope (WATER_DEPTH_RATING_M remains the single
    # headline rating; these carry the poster min/max/experience trio)
    PIPELAY_MIN_WATER_DEPTH_M: Optional[float] = None
    PIPELAY_MAX_WATER_DEPTH_M: Optional[float] = None
    EXPERIENCE_WATER_DEPTH_M: Optional[float] = None

    # Pipe handling
    PIPE_JOINT_LENGTH_MAX_M: Optional[float] = None
    DAVITS_COUNT: Optional[int] = None

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
        "PIPELAY_METHOD",
        "FOUNDATION_TYPE",
        "WELDING_METHOD",
        "TOW_METHODS",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none_cv(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "SLAY_CENTER_CAPABLE",
        "SLAY_SIDE_CAPABLE",
        "JLAY_CAPABLE",
        "REEL_PERMANENT_CAPABLE",
        "REEL_REMOVABLE_CAPABLE",
        "CAROUSEL_CAPABLE",
        "TOW_INSTALL_CAPABLE",
        "BURIAL_CAPABLE",
        "SIMULTANEOUS_LAY_BURY_CAPABLE",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none_cv_bools(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "MAIN_CRANE_CAPACITY_T",
        "MAIN_CRANE_REACH_M",
        "AUX_CRANE_CAPACITY_T",
        "AUX_CRANE_REACH_M",
        "PIPELAY_CAPACITY_IN",
        "PIPELAY_TENSION_T",
        "DECK_AREA_M2",
        "DECK_LOAD_CAPACITY_T",
        "BOLLARD_PULL_T",
        "HEAVY_LIFT_CAPACITY_T",
        "WATER_DEPTH_RATING_M",
        "TURBINE_CAPACITY_MW",
        "PIPELAY_MIN_DIAMETER_IN",
        "BURIAL_MIN_DIAMETER_IN",
        "BURIAL_MAX_DIAMETER_IN",
        "BURIAL_MAX_WATER_DEPTH_M",
        "PIPELAY_MIN_WATER_DEPTH_M",
        "PIPELAY_MAX_WATER_DEPTH_M",
        "EXPERIENCE_WATER_DEPTH_M",
        "PIPE_JOINT_LENGTH_MAX_M",
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
        "MAIN_CRANE_CAPACITY_T",
        "MAIN_CRANE_REACH_M",
        "AUX_CRANE_CAPACITY_T",
        "AUX_CRANE_REACH_M",
        "PIPELAY_CAPACITY_IN",
        "PIPELAY_TENSION_T",
        "DECK_AREA_M2",
        "DECK_LOAD_CAPACITY_T",
        "BOLLARD_PULL_T",
        "HEAVY_LIFT_CAPACITY_T",
        "WATER_DEPTH_RATING_M",
        "TURBINE_CAPACITY_MW",
        "PIPELAY_MIN_DIAMETER_IN",
        "BURIAL_MIN_DIAMETER_IN",
        "BURIAL_MAX_DIAMETER_IN",
        "BURIAL_MAX_WATER_DEPTH_M",
        "PIPELAY_MIN_WATER_DEPTH_M",
        "PIPELAY_MAX_WATER_DEPTH_M",
        "EXPERIENCE_WATER_DEPTH_M",
        "PIPE_JOINT_LENGTH_MAX_M",
    )
    @classmethod
    def _validate_non_negative_cv_floats(
        cls,
        v: Optional[float],
    ) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator(
        "ROV_SYSTEMS",
        "WELDING_STATIONS_COUNT",
        "TOTAL_STATIONS_COUNT",
        "NDT_STATIONS_COUNT",
        "TENSIONER_COUNT",
        "DAVITS_COUNT",
        mode="before",
    )
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
