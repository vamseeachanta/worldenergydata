"""Pydantic schema for rig fleet records.

Validates and coerces raw data from rig fleet datasets and WAR
(Well Activity Report) enrichments.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class RigFleetSchema(BaseModel):
    """Schema for a single rig fleet record.

    Field names match upstream CSV column headers so that records can be
    loaded directly from pandas DataFrames via
    ``RigFleetSchema(**row)``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required fields
    RIG_NAME: str

    # Optional string fields
    RIG_TYPE: Optional[str] = None
    RIG_STATUS: Optional[str] = None
    OWNER: Optional[str] = None
    OPERATOR: Optional[str] = None
    IMO_NUMBER: Optional[str] = None
    FLAG_STATE: Optional[str] = None
    LAST_WAR_DATE: Optional[str] = None
    LAST_AREA_CODE: Optional[str] = None

    # Optional float fields
    WATER_DEPTH_RATING_FT: Optional[float] = None
    DRILLING_DEPTH_RATING_FT: Optional[float] = None
    LOA_M: Optional[float] = None
    BEAM_M: Optional[float] = None
    DISPLACEMENT_TONNES: Optional[float] = None
    MOONPOOL_DIAMETER_M: Optional[float] = None

    # Optional int fields
    DP_CLASS: Optional[int] = None
    YEAR_BUILT: Optional[int] = None
    WELLS_DRILLED_COUNT: Optional[int] = None

    # --- Validators ---

    @field_validator("RIG_NAME", mode="before")
    @classmethod
    def _strip_rig_name_quotes(cls, v: object) -> object:
        """Strip surrounding quotes from rig name."""
        if isinstance(v, str):
            return v.strip().strip('"').strip("'")
        return v

    @field_validator(
        "RIG_TYPE",
        "RIG_STATUS",
        "OWNER",
        "OPERATOR",
        "IMO_NUMBER",
        "FLAG_STATE",
        "LAST_WAR_DATE",
        "LAST_AREA_CODE",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        """Coerce empty or whitespace-only strings to None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "WATER_DEPTH_RATING_FT",
        "DRILLING_DEPTH_RATING_FT",
        "LOA_M",
        "BEAM_M",
        "DISPLACEMENT_TONNES",
        "MOONPOOL_DIAMETER_M",
        mode="before",
    )
    @classmethod
    def _coerce_float_fields(cls, v: object) -> object:
        """Coerce string floats, empty to None."""
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
        "LOA_M",
        "BEAM_M",
        "DISPLACEMENT_TONNES",
        "MOONPOOL_DIAMETER_M",
    )
    @classmethod
    def _validate_non_negative_floats(
        cls, v: Optional[float],
    ) -> Optional[float]:
        """Float measurements must be non-negative when provided."""
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator("DP_CLASS", "YEAR_BUILT", "WELLS_DRILLED_COUNT", mode="before")
    @classmethod
    def _coerce_int_fields(cls, v: object) -> object:
        """Coerce string integers, empty to None."""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return int(v)
        return v

    @field_validator("YEAR_BUILT")
    @classmethod
    def _validate_year_built(cls, v: Optional[int]) -> Optional[int]:
        """Year built must be in range 1900-2035."""
        if v is not None and (v < 1900 or v > 2035):
            raise ValueError("YEAR_BUILT must be between 1900 and 2035")
        return v
