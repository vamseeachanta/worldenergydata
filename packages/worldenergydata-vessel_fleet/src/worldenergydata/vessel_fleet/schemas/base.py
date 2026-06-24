"""Base vessel schema shared across all vessel categories."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class BaseVesselSchema(BaseModel):
    """Schema for shared vessel fields.

    Field names are UPPERCASE to match tabular column headers and
    allow direct loading from DataFrames via ``BaseVesselSchema(**row)``.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Required
    VESSEL_NAME: str

    # Optional string fields
    VESSEL_CATEGORY: Optional[str] = None
    VESSEL_TYPE: Optional[str] = None
    VESSEL_SUBTYPE: Optional[str] = None
    OWNER: Optional[str] = None
    OPERATOR: Optional[str] = None
    IMO_NUMBER: Optional[str] = None
    MMSI: Optional[str] = None
    FLAG_STATE: Optional[str] = None
    CLASSIFICATION_SOCIETY: Optional[str] = None
    CLASS_NOTATION: Optional[str] = None
    STATUS: Optional[str] = None
    DATA_SOURCE: Optional[str] = None
    DATA_SOURCE_URL: Optional[str] = None
    COLLECTION_DATE: Optional[str] = None

    # Optional float fields
    LOA_M: Optional[float] = None
    BEAM_M: Optional[float] = None
    DEPTH_M: Optional[float] = None
    DRAFT_M: Optional[float] = None
    DISPLACEMENT_TONNES: Optional[float] = None
    GROSS_TONNAGE: Optional[float] = None
    DEADWEIGHT_TONNES: Optional[float] = None
    TRANSIT_SPEED_KNOTS: Optional[float] = None

    # Optional int fields
    DP_CLASS: Optional[int] = None
    YEAR_BUILT: Optional[int] = None
    QUARTERS_CAPACITY: Optional[int] = None

    # Optional bool fields
    HELIDECK: Optional[bool] = None

    # --- Validators ---

    @field_validator("VESSEL_NAME", mode="before")
    @classmethod
    def _strip_vessel_name_quotes(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().strip('"').strip("'")
        return v

    @field_validator(
        "VESSEL_CATEGORY",
        "VESSEL_TYPE",
        "VESSEL_SUBTYPE",
        "OWNER",
        "OPERATOR",
        "IMO_NUMBER",
        "MMSI",
        "FLAG_STATE",
        "CLASSIFICATION_SOCIETY",
        "CLASS_NOTATION",
        "STATUS",
        "DATA_SOURCE",
        "DATA_SOURCE_URL",
        "COLLECTION_DATE",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "LOA_M",
        "BEAM_M",
        "DEPTH_M",
        "DRAFT_M",
        "DISPLACEMENT_TONNES",
        "GROSS_TONNAGE",
        "DEADWEIGHT_TONNES",
        "TRANSIT_SPEED_KNOTS",
        mode="before",
    )
    @classmethod
    def _coerce_float_fields(cls, v: object) -> object:
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            if v == "":
                return None
            return float(v)
        return v

    @field_validator(
        "LOA_M",
        "BEAM_M",
        "DEPTH_M",
        "DRAFT_M",
        "DISPLACEMENT_TONNES",
        "GROSS_TONNAGE",
        "DEADWEIGHT_TONNES",
        "TRANSIT_SPEED_KNOTS",
    )
    @classmethod
    def _validate_non_negative_floats(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator("DP_CLASS", "YEAR_BUILT", "QUARTERS_CAPACITY", mode="before")
    @classmethod
    def _coerce_int_fields(cls, v: object) -> object:
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

    @field_validator("YEAR_BUILT")
    @classmethod
    def _validate_year_built(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1900 or v > 2035):
            raise ValueError("YEAR_BUILT must be between 1900 and 2035")
        return v

    @field_validator("IMO_NUMBER")
    @classmethod
    def _validate_imo_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not (v.isdigit() and len(v) == 7):
            raise ValueError("IMO_NUMBER must be exactly 7 digits")
        return v
