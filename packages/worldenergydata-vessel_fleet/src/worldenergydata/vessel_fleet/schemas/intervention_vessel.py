"""Pydantic schema for well-intervention vessel records."""

from __future__ import annotations

from typing import Optional

from pydantic import field_validator

from worldenergydata.vessel_fleet.schemas.base import BaseVesselSchema


class InterventionVesselSchema(BaseVesselSchema):
    """Schema for a well-intervention vessel record.

    Extends BaseVesselSchema with fields specific to riser-based and
    riserless light well-intervention (RLWI) units, heavy intervention
    semi-submersibles, and multipurpose support vessels (MPSV).
    """

    # Riser / intervention capability
    RISER_CAPABLE: Optional[bool] = None
    INTERVENTION_CLASS: Optional[str] = None  # "light" / "heavy"
    SUBSEA_LUBRICATOR: Optional[bool] = None
    IRS_SYSTEM: Optional[str] = None
    WELL_CONTROL_PACKAGE: Optional[str] = None
    CT_CAPABLE: Optional[bool] = None
    GOM_RESIDENT: Optional[bool] = None

    # Operational
    WATER_DEPTH_RATING_M: Optional[float] = None

    # --- Validators ---

    @field_validator(
        "INTERVENTION_CLASS",
        "IRS_SYSTEM",
        "WELL_CONTROL_PACKAGE",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none_iv(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("INTERVENTION_CLASS")
    @classmethod
    def _validate_intervention_class(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in {"light", "heavy"}:
            raise ValueError("INTERVENTION_CLASS must be 'light' or 'heavy'")
        return v

    @field_validator("WATER_DEPTH_RATING_M", mode="before")
    @classmethod
    def _coerce_iv_float_fields(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return float(v)
        return v

    @field_validator("WATER_DEPTH_RATING_M")
    @classmethod
    def _validate_non_negative_iv_floats(
        cls,
        v: Optional[float],
    ) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v
