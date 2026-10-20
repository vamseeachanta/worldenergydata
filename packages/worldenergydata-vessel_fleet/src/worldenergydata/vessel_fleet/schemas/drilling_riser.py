"""Pydantic schemas for drilling riser component records."""

from __future__ import annotations

import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from worldenergydata.vessel_fleet.models.drilling_riser import (
    AuxiliaryLineEntry,
    RiserClass,
)


class RiserJointSchema(BaseModel):
    """Schema for a drilling, lift/mining or production riser joint.

    Field names are UPPERCASE to match tabular column headers.
    Units: OD/ID/WT in inches, joint lengths in feet, weights in kips;
    design water depth is in metres. OD/ID/WT describe the main tube.

    GRADE preserves the source designation. The catalog mixes line-pipe
    designations (API Spec 5L) and drill-pipe designations (API Spec 5DP);
    they are separate vocabularies, not interchangeable material properties.
    See the API 2025 Publications Catalog, Tubular Goods entries cited below.
    """

    # GRADE is source text, not a common strength vocabulary. API's public
    # 2025 Publications Catalog, Tubular Goods, distinguishes Spec 5L (Line
    # Pipe, 46th edition, 2018) from Spec 5DP (Drill Pipe, 2nd edition, 2020).
    # No equivalence or material property follows from a designation alone.
    model_config = ConfigDict(str_strip_whitespace=True)

    COMPONENT_ID: str
    COMPONENT_TYPE: str = "riser_joint"
    MANUFACTURER: Optional[str] = None
    MODEL: Optional[str] = None

    OD_IN: Optional[float] = None
    ID_IN: Optional[float] = None
    WALL_THICKNESS_IN: Optional[float] = None
    LENGTH_FT: Optional[float] = None
    WEIGHT_AIR_KIPS: Optional[float] = None
    WEIGHT_WATER_KIPS: Optional[float] = None
    GRADE: Optional[str] = None
    CONNECTION_TYPE: Optional[str] = None
    BUOYANCY_COVERAGE_PCT: Optional[float] = None
    BUOYANCY_OD_IN: Optional[float] = None
    PRESSURE_RATING_PSI: Optional[float] = None

    DATA_SOURCE: Optional[str] = None
    NOTES: Optional[str] = None

    RISER_CLASS: RiserClass = "drilling"
    AUXILIARY_LINES: tuple[AuxiliaryLineEntry, ...] = ()
    # Depth is an input describing intended use, not a qualified depth rating.
    DESIGN_WATER_DEPTH_M: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    INTERNAL_MEDIUM: str | None = None

    @field_validator("RISER_CLASS", mode="before")
    @classmethod
    def _legacy_class(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
        return "drilling" if value is None or value == "" else value

    @field_validator("AUXILIARY_LINES", mode="before")
    @classmethod
    def _bundle_json(cls, value: object) -> object:
        """Optional CSV cell: JSON array of line objects with lower-case keys."""
        if value is None or (isinstance(value, str) and not value.strip()):
            return ()
        return json.loads(value) if isinstance(value, str) else value

    @field_validator("DESIGN_WATER_DEPTH_M", "INTERNAL_MEDIUM", mode="before")
    @classmethod
    def _blank_metadata(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "MANUFACTURER",
        "MODEL",
        "GRADE",
        "CONNECTION_TYPE",
        "DATA_SOURCE",
        "NOTES",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "OD_IN",
        "ID_IN",
        "WALL_THICKNESS_IN",
        "LENGTH_FT",
        "WEIGHT_AIR_KIPS",
        "WEIGHT_WATER_KIPS",
        "BUOYANCY_COVERAGE_PCT",
        "BUOYANCY_OD_IN",
        "PRESSURE_RATING_PSI",
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
        "OD_IN",
        "ID_IN",
        "WALL_THICKNESS_IN",
        "LENGTH_FT",
        "WEIGHT_AIR_KIPS",
        "BUOYANCY_COVERAGE_PCT",
        "BUOYANCY_OD_IN",
        "PRESSURE_RATING_PSI",
    )
    @classmethod
    def _validate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        # Submerged weight is deliberately signed: packaged catalog record
        # RJ-21-75-BUOY has net uplift (WEIGHT_WATER_KIPS = -4.2).
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v


class BOPSchema(BaseModel):
    """Schema for a blowout preventer stack.

    Covers both surface and subsea BOP configurations.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    COMPONENT_ID: str
    COMPONENT_TYPE: str = "bop"
    BOP_TYPE: Optional[str] = None  # surface / subsea
    MANUFACTURER: Optional[str] = None
    MODEL: Optional[str] = None

    BORE_SIZE_IN: Optional[float] = None
    PRESSURE_RATING_PSI: Optional[float] = None
    HEIGHT_FT: Optional[float] = None
    WEIGHT_AIR_KIPS: Optional[float] = None
    WEIGHT_WATER_KIPS: Optional[float] = None

    ANNULAR_COUNT: Optional[int] = None
    SHEAR_RAM_COUNT: Optional[int] = None
    PIPE_RAM_COUNT: Optional[int] = None
    CASING_SHEAR_RAM: Optional[bool] = None

    DATA_SOURCE: Optional[str] = None
    NOTES: Optional[str] = None

    @field_validator(
        "BOP_TYPE",
        "MANUFACTURER",
        "MODEL",
        "DATA_SOURCE",
        "NOTES",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "BORE_SIZE_IN",
        "PRESSURE_RATING_PSI",
        "HEIGHT_FT",
        "WEIGHT_AIR_KIPS",
        "WEIGHT_WATER_KIPS",
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
        "BORE_SIZE_IN",
        "PRESSURE_RATING_PSI",
        "HEIGHT_FT",
        "WEIGHT_AIR_KIPS",
        "WEIGHT_WATER_KIPS",
    )
    @classmethod
    def _validate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator(
        "ANNULAR_COUNT",
        "SHEAR_RAM_COUNT",
        "PIPE_RAM_COUNT",
        mode="before",
    )
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


class LMRPSchema(BaseModel):
    """Schema for a Lower Marine Riser Package."""

    model_config = ConfigDict(str_strip_whitespace=True)

    COMPONENT_ID: str
    COMPONENT_TYPE: str = "lmrp"
    MANUFACTURER: Optional[str] = None
    MODEL: Optional[str] = None

    BORE_SIZE_IN: Optional[float] = None
    PRESSURE_RATING_PSI: Optional[float] = None
    HEIGHT_FT: Optional[float] = None
    WEIGHT_AIR_KIPS: Optional[float] = None
    WEIGHT_WATER_KIPS: Optional[float] = None
    ANNULAR_COUNT: Optional[int] = None
    CONNECTOR_TYPE: Optional[str] = None

    DATA_SOURCE: Optional[str] = None
    NOTES: Optional[str] = None

    @field_validator(
        "MANUFACTURER",
        "MODEL",
        "CONNECTOR_TYPE",
        "DATA_SOURCE",
        "NOTES",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "BORE_SIZE_IN",
        "PRESSURE_RATING_PSI",
        "HEIGHT_FT",
        "WEIGHT_AIR_KIPS",
        "WEIGHT_WATER_KIPS",
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
        "BORE_SIZE_IN",
        "PRESSURE_RATING_PSI",
        "HEIGHT_FT",
        "WEIGHT_AIR_KIPS",
        "WEIGHT_WATER_KIPS",
    )
    @classmethod
    def _validate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v

    @field_validator("ANNULAR_COUNT", mode="before")
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


class FlexJointSchema(BaseModel):
    """Schema for a flex/ball joint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    COMPONENT_ID: str
    COMPONENT_TYPE: str = "flex_joint"
    POSITION: Optional[str] = None  # upper / lower
    MANUFACTURER: Optional[str] = None
    MODEL: Optional[str] = None

    BORE_SIZE_IN: Optional[float] = None
    MAX_ANGLE_DEG: Optional[float] = None
    STIFFNESS_FT_KIP_PER_DEG: Optional[float] = None
    HEIGHT_FT: Optional[float] = None
    WEIGHT_AIR_KIPS: Optional[float] = None
    PRESSURE_RATING_PSI: Optional[float] = None

    DATA_SOURCE: Optional[str] = None
    NOTES: Optional[str] = None

    @field_validator(
        "POSITION",
        "MANUFACTURER",
        "MODEL",
        "DATA_SOURCE",
        "NOTES",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "BORE_SIZE_IN",
        "MAX_ANGLE_DEG",
        "STIFFNESS_FT_KIP_PER_DEG",
        "HEIGHT_FT",
        "WEIGHT_AIR_KIPS",
        "PRESSURE_RATING_PSI",
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
        "BORE_SIZE_IN",
        "MAX_ANGLE_DEG",
        "STIFFNESS_FT_KIP_PER_DEG",
        "HEIGHT_FT",
        "WEIGHT_AIR_KIPS",
        "PRESSURE_RATING_PSI",
    )
    @classmethod
    def _validate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v


class TelescopicJointSchema(BaseModel):
    """Schema for a telescopic (slip) joint."""

    model_config = ConfigDict(str_strip_whitespace=True)

    COMPONENT_ID: str
    COMPONENT_TYPE: str = "telescopic_joint"
    MANUFACTURER: Optional[str] = None
    MODEL: Optional[str] = None

    OD_IN: Optional[float] = None
    BORE_SIZE_IN: Optional[float] = None
    STROKE_FT: Optional[float] = None
    OUTER_BARREL_LENGTH_FT: Optional[float] = None
    INNER_BARREL_LENGTH_FT: Optional[float] = None
    WEIGHT_AIR_KIPS: Optional[float] = None
    PRESSURE_RATING_PSI: Optional[float] = None

    DATA_SOURCE: Optional[str] = None
    NOTES: Optional[str] = None

    @field_validator(
        "MANUFACTURER",
        "MODEL",
        "DATA_SOURCE",
        "NOTES",
        mode="before",
    )
    @classmethod
    def _empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @field_validator(
        "OD_IN",
        "BORE_SIZE_IN",
        "STROKE_FT",
        "OUTER_BARREL_LENGTH_FT",
        "INNER_BARREL_LENGTH_FT",
        "WEIGHT_AIR_KIPS",
        "PRESSURE_RATING_PSI",
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
        "OD_IN",
        "BORE_SIZE_IN",
        "STROKE_FT",
        "OUTER_BARREL_LENGTH_FT",
        "INNER_BARREL_LENGTH_FT",
        "WEIGHT_AIR_KIPS",
        "PRESSURE_RATING_PSI",
    )
    @classmethod
    def _validate_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Value must be >= 0")
        return v
