"""Pydantic schema for well-intervention vessel records."""

from __future__ import annotations

from math import isfinite

from pydantic import field_validator

from worldenergydata.vessel_fleet.constants import InterventionClass
from worldenergydata.vessel_fleet.schemas.base import BaseVesselSchema


class InterventionVesselSchema(BaseVesselSchema):
    """Schema for a well-intervention vessel record.

    Extends BaseVesselSchema with fields specific to riser-based and
    riserless light well-intervention (RLWI) units, heavy intervention
    semi-submersibles, and multipurpose support vessels (MPSV).
    """

    # Riser / intervention capability
    RISER_CAPABLE: bool | None = None
    INTERVENTION_CLASS: InterventionClass | None = None
    SUBSEA_LUBRICATOR: bool | None = None
    IRS_SYSTEM: str | None = None
    WELL_CONTROL_PACKAGE: str | None = None
    CT_CAPABLE: bool | None = None
    GOM_RESIDENT: bool | None = None

    # Operational
    WATER_DEPTH_RATING_M: float | None = None

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

    @field_validator("INTERVENTION_CLASS", mode="before")
    @classmethod
    def _validate_intervention_class(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower() or None
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
        v: float | None,
    ) -> float | None:
        # A depth is finite and nonnegative by definition, not a design limit.
        if v is not None and (not isfinite(v) or v < 0):
            raise ValueError("Water depth must be finite and >= 0")
        return v
