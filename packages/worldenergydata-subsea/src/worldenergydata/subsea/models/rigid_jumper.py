"""Pydantic validation model for rigid jumper curated CSV data."""

from math import isfinite
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, field_validator


class RigidJumperSpec(BaseModel):
    """A rigid jumper specification from manufacturer catalogs."""

    component_id: str
    manufacturer: str
    od_in: float
    wall_thickness_in: float
    length_ft: float
    material_grade: str
    pressure_rating_psi: float
    weight_air_kips: float | None = None
    connection_type: str | None = None
    data_source: str
    notes: str | None = None

    @field_validator("od_in")
    @classmethod
    def od_positive(cls, v: float) -> float:
        """OD must be positive."""
        # Issue #1305: positivity requires finiteness as well as sign.
        if not isfinite(v) or v <= 0:
            raise ValueError("OD must be positive and finite")
        return v

    @field_validator("wall_thickness_in")
    @classmethod
    def wall_thickness_positive(cls, v: float) -> float:
        """Wall thickness must be positive."""
        # Issue #1305: positivity requires finiteness as well as sign.
        if not isfinite(v) or v <= 0:
            raise ValueError("Wall thickness must be positive and finite")
        return v

    @field_validator("pressure_rating_psi")
    @classmethod
    def pressure_positive(cls, v: float) -> float:
        """Pressure rating must be positive."""
        # Issue #1305: positivity requires finiteness as well as sign.
        if not isfinite(v) or v <= 0:
            raise ValueError("Pressure rating must be positive and finite")
        return v

    @field_validator("weight_air_kips")
    @classmethod
    def weight_nonnegative(cls, v: float | None) -> float | None:
        """Absent weight is allowed; present weight must be finite/nonnegative."""
        # Issue #1305 input contract: negative weight and nonfinite values
        # are invalid. Zero is a domain boundary, not a design acceptance limit.
        if v is not None and (not isfinite(v) or v < 0):
            raise ValueError("Weight must be nonnegative and finite")
        return v


def load_rigid_jumpers(csv_path: Path) -> list[RigidJumperSpec]:
    """Load and validate rigid jumper specs from a CSV file.

    Args:
        csv_path: Path to the rigid_jumper_specs.csv file.

    Only empty cells are omitted; literal NA-like strings are preserved.
    Invalid present numeric values raise a Pydantic validation error.

    Returns:
        List of validated RigidJumperSpec instances.
    """
    # Issue #1305: only empty cells denote absence, not tokens such as NA.
    # Object dtype preserves text identifiers; Pydantic parses numeric fields.
    df = pd.read_csv(csv_path, keep_default_na=False, dtype=object)
    return [
        RigidJumperSpec(**{k.lower(): v for k, v in row.items() if v != ""})
        for _, row in df.iterrows()
    ]
