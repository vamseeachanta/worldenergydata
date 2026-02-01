"""Pydantic schemas for BSEE pipeline permit and location records.

Validates and coerces raw data from the BSEE pipeline datasets
(PipelinePermitRawData.zip and PipelineLocationRawData.zip).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class PipelinePermitSchema(BaseModel):
    """Schema for a single BSEE pipeline permit record.

    Field names match the upstream BSEE CSV column headers.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    SEGMENT_NUM: Optional[str] = None
    PPL_SIZE_CODE: Optional[str] = None
    MAOP_PRSS: Optional[float] = None
    RECV_MAOP_PRSS: Optional[float] = None
    SEG_LENGTH: Optional[float] = None
    MAX_WTR_DPTH: Optional[float] = None
    MIN_WTR_DPTH: Optional[float] = None
    PROD_CODE: Optional[str] = None
    STATUS_CODE: Optional[str] = None
    PPL_CONST_DATE: Optional[str] = None
    ABAN_DATE: Optional[str] = None
    AREA_CODE: Optional[str] = None
    BLOCK_NUMBER: Optional[str] = None
    LEASE_NUMBER: Optional[str] = None

    # --- Validators ---

    @field_validator(
        "SEGMENT_NUM",
        "PPL_SIZE_CODE",
        "PROD_CODE",
        "STATUS_CODE",
        "PPL_CONST_DATE",
        "ABAN_DATE",
        "AREA_CODE",
        "BLOCK_NUMBER",
        "LEASE_NUMBER",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        """Coerce empty or whitespace-only strings to None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "MAOP_PRSS",
        "RECV_MAOP_PRSS",
        "SEG_LENGTH",
        "MAX_WTR_DPTH",
        "MIN_WTR_DPTH",
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

    @field_validator("MAOP_PRSS")
    @classmethod
    def _validate_maop(cls, v: Optional[float]) -> Optional[float]:
        """MAOP pressure must be non-negative when provided."""
        if v is not None and v < 0:
            raise ValueError("MAOP_PRSS must be >= 0")
        return v


class PipelineLocationSchema(BaseModel):
    """Schema for a single BSEE pipeline location point record.

    Field names match the upstream BSEE CSV column headers.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    SEGMENT_NUM: Optional[str] = None
    POINT_NUM: Optional[int] = None
    LATITUDE: Optional[float] = None
    LONGITUDE: Optional[float] = None
    WATER_DEPTH: Optional[float] = None
    AREA_CODE: Optional[str] = None
    BLOCK_NUMBER: Optional[str] = None

    # --- Validators ---

    @field_validator(
        "SEGMENT_NUM",
        "AREA_CODE",
        "BLOCK_NUMBER",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        """Coerce empty or whitespace-only strings to None."""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator("POINT_NUM", mode="before")
    @classmethod
    def _coerce_point_num(cls, v: object) -> object:
        """Coerce string point number to int, empty to None."""
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return int(v)
        return v

    @field_validator("WATER_DEPTH", "LATITUDE", "LONGITUDE", mode="before")
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
