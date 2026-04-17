"""Pydantic validation model for mooring component curated CSV data."""

from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import BaseModel, field_validator


class MooringComponentSpec(BaseModel):
    """A mooring component specification from manufacturer catalogs."""

    component_id: str
    component_type: str  # chain, wire_rope, polyester_rope, anchor, connector
    manufacturer: str
    size_mm: float
    mbl_kn: float  # minimum breaking load in kN
    weight_kg_per_m: Optional[float] = None
    material: Optional[str] = None
    grade: Optional[str] = None
    data_source: str
    notes: Optional[str] = None

    @field_validator("component_type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        """Component type must be a known mooring component category."""
        valid = {"chain", "wire_rope", "polyester_rope", "anchor", "connector"}
        if v not in valid:
            raise ValueError(f"component_type must be one of {valid}")
        return v

    @field_validator("mbl_kn")
    @classmethod
    def mbl_positive(cls, v: float) -> float:
        """Minimum breaking load must be positive."""
        if v <= 0:
            raise ValueError("MBL must be positive")
        return v


def load_mooring_components(csv_path: Path) -> list[MooringComponentSpec]:
    """Load and validate mooring component specs from a CSV file.

    Args:
        csv_path: Path to the mooring_components.csv file.

    Returns:
        List of validated MooringComponentSpec instances.
    """
    df = pd.read_csv(csv_path)
    return [
        MooringComponentSpec(**{k.lower(): v for k, v in row.items() if pd.notna(v)})
        for _, row in df.iterrows()
    ]
