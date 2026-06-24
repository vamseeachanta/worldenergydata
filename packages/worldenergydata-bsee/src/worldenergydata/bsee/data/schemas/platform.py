"""Pydantic schema for BSEE platform structure records.

Validates and coerces raw data from the BSEE platform/structure dataset
(PlatStrucRawData.zip).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class PlatformStructureSchema(BaseModel):
    """Schema for a single BSEE platform structure record.

    Field names match the upstream BSEE CSV column headers so that
    records can be loaded directly from pandas DataFrames via
    ``PlatformStructureSchema(**row)``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required fields
    AREA_CODE: str
    BLOCK_NUMBER: str
    STRUCTURE_NUMBER: str

    # Optional fields
    COMPLEX_ID_NUM: Optional[str] = None
    STRUCTURE_NAME: Optional[str] = None
    STRUC_TYPE_CODE: Optional[str] = None
    MAJ_STRUC_FLAG: Optional[str] = None
    FIELD_NAME_CODE: Optional[str] = None
    WATER_DEPTH: Optional[float] = None
    INSTALL_DATE: Optional[str] = None
    REMOVAL_DATE: Optional[str] = None
    DECK_COUNT: Optional[int] = None
    SLOT_COUNT: Optional[int] = None
    LATITUDE: Optional[float] = None
    LONGITUDE: Optional[float] = None
    LEASE_NUMBER: Optional[str] = None
    DISTRICT_CODE: Optional[str] = None

    # --- Validators ---

    @field_validator(
        "COMPLEX_ID_NUM",
        "STRUCTURE_NAME",
        "STRUC_TYPE_CODE",
        "MAJ_STRUC_FLAG",
        "FIELD_NAME_CODE",
        "INSTALL_DATE",
        "REMOVAL_DATE",
        "LEASE_NUMBER",
        "DISTRICT_CODE",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        """Coerce empty or whitespace-only strings to None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("WATER_DEPTH", mode="before")
    @classmethod
    def _coerce_water_depth(cls, v: object) -> object:
        """Coerce string water depth to float, empty to None."""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return float(v)
        return v

    @field_validator("WATER_DEPTH")
    @classmethod
    def _validate_water_depth(cls, v: Optional[float]) -> Optional[float]:
        """Water depth must be non-negative when provided."""
        if v is not None and v < 0:
            raise ValueError("WATER_DEPTH must be >= 0")
        return v

    @field_validator("DECK_COUNT", "SLOT_COUNT", mode="before")
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

    @field_validator("LATITUDE")
    @classmethod
    def _validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        """Latitude must be in range -90..90."""
        if v is not None and (v < -90 or v > 90):
            raise ValueError("LATITUDE must be between -90 and 90")
        return v

    @field_validator("LONGITUDE")
    @classmethod
    def _validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        """Longitude must be in range -180..180."""
        if v is not None and (v < -180 or v > 180):
            raise ValueError("LONGITUDE must be between -180 and 180")
        return v
