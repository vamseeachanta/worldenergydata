"""Pydantic validation model for rigid jumper curated CSV data."""

from pathlib import Path
from typing import Optional

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
    weight_air_kips: Optional[float] = None
    connection_type: Optional[str] = None
    data_source: str
    notes: Optional[str] = None

    @field_validator("od_in")
    @classmethod
    def od_positive(cls, v: float) -> float:
        """OD must be positive."""
        if v <= 0:
            raise ValueError("OD must be positive")
        return v

    @field_validator("wall_thickness_in")
    @classmethod
    def wall_thickness_positive(cls, v: float) -> float:
        """Wall thickness must be positive."""
        if v <= 0:
            raise ValueError("Wall thickness must be positive")
        return v

    @field_validator("pressure_rating_psi")
    @classmethod
    def pressure_positive(cls, v: float) -> float:
        """Pressure rating must be positive."""
        if v <= 0:
            raise ValueError("Pressure rating must be positive")
        return v


def load_rigid_jumpers(csv_path: Path) -> list[RigidJumperSpec]:
    """Load and validate rigid jumper specs from a CSV file.

    Args:
        csv_path: Path to the rigid_jumper_specs.csv file.

    Returns:
        List of validated RigidJumperSpec instances.
    """
    df = pd.read_csv(csv_path)
    return [
        RigidJumperSpec(**{k.lower(): v for k, v in row.items() if pd.notna(v)})
        for _, row in df.iterrows()
    ]
