"""Load drilling riser component data from curated dataset.

Validates CSV widths, required query/provenance columns and populated provenance.
Empty physical lines are skipped; whitespace and delimiter-only records are checked.
Queries cover component type, size and pressure rating.
"""

from __future__ import annotations

import csv
import logging
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd

from worldenergydata.vessel_fleet.models.drilling_riser import (
    RiserJointEntry,
    RiserLineEntry,
)
from worldenergydata.vessel_fleet.schemas.drilling_riser import RiserJointSchema

logger = logging.getLogger(__name__)

# Curated data ships INSIDE this member as package data (ADR 0001 Phase 2,
# batch 4, #529 — option (i): data travels with the package). See
# construction_vessel_loader for the resolution rationale.
_DATA_DIR = Path(__file__).resolve().parent.parent / "_data" / "curated"
_DEFAULT_FILE = "drilling_riser_components.csv"
_REQUIRED_COLUMNS = (
    "COMPONENT_ID",
    "DATA_SOURCE",
    "NOTES",
    "COMPONENT_TYPE",
    "OD_IN",
    "PRESSURE_RATING_PSI",
    "BORE_SIZE_IN",
    "BOP_TYPE",
    "MANUFACTURER",
)

VALID_COMPONENT_TYPES = (
    "riser_joint",
    "bop",
    "lmrp",
    "flex_joint",
    "telescopic_joint",
)


def _validate_row_widths(content: str) -> None:
    """Check widths except empty physical lines; retain physical start numbers."""
    reader = csv.reader(StringIO(content), strict=True)
    try:
        header = next(reader, [])
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV at line 1: {exc}") from exc
    expected = len(header)
    while True:
        line_number = reader.line_num + 1
        try:
            row = next(reader)
        except StopIteration:
            break
        except csv.Error as exc:
            raise ValueError(f"Malformed CSV at line {line_number}: {exc}") from exc
        if not row:
            continue
        if len(row) != expected:
            raise ValueError(
                f"CSV line {line_number}: expected {expected} fields, "
                f"actual {len(row)}"
            )


class DrillingRiserLoader:
    """Query drilling riser component data from the curated dataset.

    Loads riser components from CSV storage and provides query methods
    by component type, size, and pressure rating.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir or _DATA_DIR
        self._df: Optional[pd.DataFrame] = None

    def load(self) -> pd.DataFrame:
        """Validate widths, required columns and provenance before caching.

        Only empty physical lines are exempt from record-width validation.
        """
        if self._df is not None:
            return self._df

        csv_path = self._data_dir / _DEFAULT_FILE
        if not csv_path.exists():
            logger.warning("Drilling riser data not found: %s", csv_path)
            self._df = pd.DataFrame()
            return self._df

        # Parse the same snapshot that was checked, so a file replacement
        # cannot introduce unchecked rows between preflight and pandas.
        content = csv_path.read_text(encoding="utf-8-sig")
        _validate_row_widths(content)
        df = pd.read_csv(StringIO(content))
        missing_columns = [field for field in _REQUIRED_COLUMNS if field not in df]
        if missing_columns:
            raise ValueError("Missing required column " + ", ".join(missing_columns))
        for field in ("DATA_SOURCE", "NOTES"):
            missing = df[field].isna() | df[field].astype(str).str.strip().eq("")
            if missing.any():
                ids = df.loc[missing, "COMPONENT_ID"].tolist()
                raise ValueError(f"{field} must be populated for components {ids}")
        self._df = df
        logger.info("Loaded %d drilling riser components", len(df))
        return self._df

    def get_by_id(self, component_id: str) -> Optional[dict]:
        """Look up component by ID."""
        df = self.load()
        if df.empty:
            return None
        mask = df["COMPONENT_ID"] == component_id
        matches = df[mask]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    def get_by_type(self, component_type: str) -> pd.DataFrame:
        """Get all components of a given type.

        Args:
            component_type: One of riser_joint, bop, lmrp,
                flex_joint, telescopic_joint.
        """
        df = self.load()
        if df.empty:
            return df
        mask = df["COMPONENT_TYPE"] == component_type
        return df[mask].copy()

    def get_riser_joints(self) -> pd.DataFrame:
        """Get all riser joints."""
        return self.get_by_type("riser_joint")

    def get_riser_joint_entries(
        self,
        riser_class: Optional[str] = None,
    ) -> list[RiserJointEntry]:
        """Validate joint records and expose classes, bundle lines and OD ratios.

        Missing optional CSV cells become None before schema validation. Legacy
        records without RISER_CLASS default to drilling. Tabular methods retain
        their original columns; no derived value is written into the source CSV.
        """
        if riser_class is not None and riser_class not in (
            "drilling",
            "lift",
            "production",
        ):
            raise ValueError("Unknown riser_class")
        entries = []
        for row in self.get_riser_joints().to_dict(orient="records"):
            fields = {
                key: None if pd.api.types.is_scalar(value) and pd.isna(value) else value
                for key, value in row.items()
                if key in RiserJointSchema.model_fields
            }
            schema = RiserJointSchema(**fields)
            values = {key.lower(): value for key, value in schema.model_dump().items()}
            values["auxiliary_lines"] = [
                RiserLineEntry(**line) for line in values["auxiliary_lines"]
            ]
            entry = RiserJointEntry(**values)
            if riser_class is None or entry.riser_class == riser_class:
                entries.append(entry)
        return entries

    def get_bops(self) -> pd.DataFrame:
        """Get all BOPs."""
        return self.get_by_type("bop")

    def get_lmrps(self) -> pd.DataFrame:
        """Get all LMRPs."""
        return self.get_by_type("lmrp")

    def get_flex_joints(self) -> pd.DataFrame:
        """Get all flex joints."""
        return self.get_by_type("flex_joint")

    def get_telescopic_joints(self) -> pd.DataFrame:
        """Get all telescopic joints."""
        return self.get_by_type("telescopic_joint")

    def filter_by_size(
        self,
        od_in: float,
        tolerance_in: float = 0.1,
    ) -> pd.DataFrame:
        """Filter riser joints by OD (inches) with optional tolerance.

        Uses tolerance-based matching to handle floating-point OD values
        extracted from model files (e.g., OrcaFlex .dat → inches conversion).

        Args:
            od_in: Target outer diameter in inches.
            tolerance_in: Allowable deviation in inches (default 0.1").
                Set to 0.0 for exact equality matching.
        """
        df = self.get_riser_joints()
        if df.empty:
            return df
        mask = (df["OD_IN"] - od_in).abs() <= tolerance_in
        return df[mask].copy()

    def query(
        self,
        component_type: Optional[str] = None,
        od_in: Optional[float] = None,
        manufacturer: Optional[str] = None,
        min_pressure_psi: Optional[float] = None,
    ) -> pd.DataFrame:
        """General-purpose query across all riser components.

        Each kwarg filters the result; omit to skip that filter.

        Args:
            component_type: One of riser_joint, bop, lmrp,
                flex_joint, telescopic_joint.
            od_in: OD filter (tolerance ±0.1" applied automatically).
            manufacturer: Exact manufacturer name match.
            min_pressure_psi: Minimum pressure rating filter.
        """
        df = self.load()
        if df.empty:
            return df

        if component_type is not None:
            df = df[df["COMPONENT_TYPE"] == component_type]

        if od_in is not None and "OD_IN" in df.columns:
            df = df[(df["OD_IN"] - od_in).abs() <= 0.1]

        if manufacturer is not None and "MANUFACTURER" in df.columns:
            df = df[df["MANUFACTURER"] == manufacturer]

        if min_pressure_psi is not None and "PRESSURE_RATING_PSI" in df.columns:
            df = df[df["PRESSURE_RATING_PSI"] >= min_pressure_psi]

        return df.copy()

    def filter_by_pressure_rating(
        self,
        min_psi: float,
        max_psi: Optional[float] = None,
    ) -> pd.DataFrame:
        """Filter all components by pressure rating range."""
        df = self.load()
        if df.empty:
            return df
        mask = df["PRESSURE_RATING_PSI"] >= min_psi
        if max_psi is not None:
            mask = mask & (df["PRESSURE_RATING_PSI"] <= max_psi)
        return df[mask].copy()

    def filter_bops_by_bore(self, bore_in: float) -> pd.DataFrame:
        """Filter BOPs by bore size."""
        bops = self.get_bops()
        if bops.empty:
            return bops
        mask = bops["BORE_SIZE_IN"] == bore_in
        return bops[mask].copy()

    def filter_subsea_bops(self) -> pd.DataFrame:
        """Get subsea BOPs only."""
        bops = self.get_bops()
        if bops.empty:
            return bops
        mask = bops["BOP_TYPE"].str.lower() == "subsea"
        return bops[mask].copy()

    def component_type_summary(self) -> dict:
        """Count of components by type."""
        df = self.load()
        if df.empty:
            return {}
        return df["COMPONENT_TYPE"].value_counts().to_dict()

    def manufacturer_summary(self) -> dict:
        """Count of components by manufacturer."""
        df = self.load()
        if df.empty:
            return {}
        mfr = df["MANUFACTURER"].dropna()
        return mfr.value_counts().to_dict()
