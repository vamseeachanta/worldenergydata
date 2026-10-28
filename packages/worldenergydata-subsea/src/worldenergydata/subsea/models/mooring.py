"""Pydantic validation model for mooring component curated CSV data."""

from math import isfinite
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, field_validator


class MooringComponentSpec(BaseModel):
    """A mooring component specification from manufacturer catalogs."""

    component_id: str
    component_type: str  # chain, wire_rope, polyester_rope, anchor, connector
    manufacturer: str
    size_mm: float
    mbl_kn: float  # minimum breaking load in kN
    weight_kg_per_m: float | None = None
    material: str | None = None
    grade: str | None = None
    data_source: str
    notes: str | None = None

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
        # Issue #1305: positivity requires finiteness as well as sign.
        if not isfinite(v) or v <= 0:
            raise ValueError("MBL must be positive and finite")
        return v

    @field_validator("weight_kg_per_m")
    @classmethod
    def weight_nonnegative(cls, v: float | None) -> float | None:
        """Absent weight is allowed; present weight must be finite/nonnegative."""
        # Issue #1305 input contract: negative weight and nonfinite values
        # are invalid. Zero is a domain boundary, not a design acceptance limit.
        if v is not None and (not isfinite(v) or v < 0):
            raise ValueError("Weight must be nonnegative and finite")
        return v


def load_mooring_components(csv_path: Path) -> list[MooringComponentSpec]:
    """Load and validate mooring component specs from a CSV file.

    Args:
        csv_path: Path to the mooring_components.csv file.

    Only empty cells are omitted; literal NA-like strings are preserved.
    Invalid present numeric values raise a Pydantic validation error.

    Returns:
        List of validated MooringComponentSpec instances.
    """
    # Issue #1305: only empty cells denote absence, not tokens such as NA.
    # Object dtype preserves text identifiers; Pydantic parses numeric fields.
    df = pd.read_csv(csv_path, keep_default_na=False, dtype=object)
    return [
        MooringComponentSpec(**{k.lower(): v for k, v in row.items() if v != ""})
        for _, row in df.iterrows()
    ]
