"""
Dashboard data loader — BSEE production, platform, and FDAS incident data.

Each public function returns a pandas DataFrame with a guaranteed schema.
When the real data files are absent, a synthetic sample is returned so the
dashboard always starts without requiring the ~300 MB BSEE binary data.

Public API:
    load_production_data(data_dir=None) -> pd.DataFrame
    load_platform_data(data_dir=None)   -> pd.DataFrame
    load_incident_data(data_dir=None)   -> pd.DataFrame

Internal helpers (also exported for testing):
    _sample_production_data() -> pd.DataFrame
    _sample_platform_data()   -> pd.DataFrame
    _sample_incident_data()   -> pd.DataFrame
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default data root relative to this file's package location
_DEFAULT_DATA_ROOT = Path(__file__).parent.parent.parent.parent.parent / "data"

# Gulf of Mexico bounding box used for synthetic coordinates
_GOM_LAT = (24.5, 30.5)
_GOM_LON = (-97.0, -81.0)

_VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

_FIELD_NAMES = [
    "Mars",
    "Thunder Horse",
    "Atlantis",
    "Olympus",
    "Jack/St. Malo",
    "Shenandoah",
    "Anchor",
    "Whale",
    "Appomattox",
    "Caesar/Tonga",
]

_OPERATORS = [
    "Shell Offshore Inc",
    "BP Exploration",
    "Chevron USA Inc",
    "ExxonMobil",
    "Murphy Exploration",
]

_INCIDENT_TYPES = [
    "Equipment Failure",
    "Personnel Injury",
    "Hydrocarbon Release",
    "Structural Damage",
    "Fire/Explosion",
    "Dropped Object",
    "Near Miss",
]


# ---------------------------------------------------------------------------
# Public loaders
# ---------------------------------------------------------------------------


def load_production_data(
    data_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load BSEE monthly production data.

    Attempts to read from <data_dir>/modules/bsee/current/production/production.csv.
    Falls back to synthetic sample data when the file does not exist.

    Args:
        data_dir: Root data directory.  Defaults to the repo-level ``data/``
                  folder.  Pass a custom path in tests or when data lives
                  elsewhere.

    Returns:
        DataFrame with columns:
          WELL_API, PRODUCTION_DATE, OIL_BBL, GAS_MCF, WATER_BBL,
          FIELD_NAME, OPERATOR
    """
    root = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_ROOT
    csv_path = root / "modules" / "bsee" / "current" / "production" / "production.csv"

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path, parse_dates=["PRODUCTION_DATE"])
            df = _normalise_production_columns(df)
            logger.info("Loaded production data from %s (%d rows)", csv_path, len(df))
            return df
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read %s: %s — using sample data", csv_path, exc)

    logger.debug("Production CSV not found at %s — using sample data", csv_path)
    return _sample_production_data()


def load_platform_data(
    data_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load BSEE well / platform location data.

    Attempts to read from <data_dir>/modules/bsee/current/wells/well_data.csv.
    Falls back to synthetic sample data when the file does not exist.

    Args:
        data_dir: Root data directory.

    Returns:
        DataFrame with columns:
          API_WELL_NUMBER, WELL_NAME, OPERATOR_NAME, FIELD_NAME,
          SURFACE_LATITUDE (as LATITUDE), SURFACE_LONGITUDE (as LONGITUDE),
          WELL_STATUS, WATER_DEPTH, AREA_NAME
    """
    root = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_ROOT
    csv_path = root / "modules" / "bsee" / "current" / "wells" / "well_data.csv"

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            df = _normalise_platform_columns(df)
            logger.info("Loaded platform data from %s (%d rows)", csv_path, len(df))
            return df
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read %s: %s — using sample data", csv_path, exc)

    logger.debug("Platform CSV not found at %s — using sample data", csv_path)
    return _sample_platform_data()


def load_incident_data(
    data_dir: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Load FDAS incident severity data.

    Attempts to read from <data_dir>/modules/fdas/incidents.csv.
    Falls back to synthetic sample data when the file does not exist.

    Args:
        data_dir: Root data directory.

    Returns:
        DataFrame with columns:
          INCIDENT_ID, INCIDENT_DATE, INCIDENT_YEAR, INCIDENT_TYPE,
          SEVERITY, AREA_NAME, OPERATOR, DESCRIPTION
    """
    root = Path(data_dir) if data_dir is not None else _DEFAULT_DATA_ROOT
    csv_path = root / "modules" / "fdas" / "incidents.csv"

    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path, parse_dates=["INCIDENT_DATE"])
            df = _normalise_incident_columns(df)
            logger.info("Loaded incident data from %s (%d rows)", csv_path, len(df))
            return df
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read %s: %s — using sample data", csv_path, exc)

    logger.debug("Incident CSV not found at %s — using sample data", csv_path)
    return _sample_incident_data()


# ---------------------------------------------------------------------------
# Column normalisation helpers
# ---------------------------------------------------------------------------


def _normalise_production_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename BSEE production CSV columns to dashboard schema."""
    rename = {
        "WELL_API": "WELL_API",
        "PRODUCTION_DATE": "PRODUCTION_DATE",
        "OIL_BBL": "OIL_BBL",
        "GAS_MCF": "GAS_MCF",
        "WATER_BBL": "WATER_BBL",
        "FIELD_NAME": "FIELD_NAME",
        "OPERATOR": "OPERATOR",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})
    # Ensure numeric volumes
    for col in ("OIL_BBL", "GAS_MCF", "WATER_BBL"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def _normalise_platform_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map BSEE well_data.csv coordinate columns to standard names."""
    rename_map = {
        "SURFACE_LATITUDE": "LATITUDE",
        "SURFACE_LONGITUDE": "LONGITUDE",
        "OPERATOR_NAME": "OPERATOR_NAME",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


def _normalise_incident_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise incident CSV column names."""
    if "INCIDENT_DATE" in df.columns:
        df["INCIDENT_YEAR"] = (
            pd.to_datetime(df["INCIDENT_DATE"], errors="coerce")
            .dt.year.fillna(0)
            .astype(int)
        )
    severity_map = {
        "low": "LOW",
        "medium": "MEDIUM",
        "med": "MEDIUM",
        "high": "HIGH",
        "critical": "CRITICAL",
    }
    if "SEVERITY" in df.columns:
        df["SEVERITY"] = (
            df["SEVERITY"].str.strip().str.lower().map(severity_map).fillna("LOW")
        )
    return df


# ---------------------------------------------------------------------------
# Synthetic sample data (fallback when real data absent)
# ---------------------------------------------------------------------------


def _sample_production_data(n_records: int = 240) -> pd.DataFrame:
    """
    Generate synthetic monthly production data for GOM fields.

    Args:
        n_records: Number of rows to generate.

    Returns:
        DataFrame matching the production schema.
    """
    rng = np.random.default_rng(seed=42)
    dates = pd.date_range(start="2019-01-01", periods=n_records, freq="ME")
    fields = rng.choice(_FIELD_NAMES, size=n_records)
    operators = rng.choice(_OPERATORS, size=n_records)

    oil = (rng.exponential(scale=15_000, size=n_records) + 1_000).round(1)
    gas = (oil * rng.uniform(0.5, 2.5, size=n_records)).round(1)
    water = (oil * rng.uniform(0.1, 1.2, size=n_records)).round(1)

    return pd.DataFrame(
        {
            "WELL_API": [f"60817{i:07d}00" for i in range(n_records)],
            "PRODUCTION_DATE": dates,
            "OIL_BBL": oil,
            "GAS_MCF": gas,
            "WATER_BBL": water,
            "FIELD_NAME": fields,
            "OPERATOR": operators,
        }
    )


def _sample_platform_data(n_records: int = 60) -> pd.DataFrame:
    """
    Generate synthetic well/platform location data within the GOM.

    Args:
        n_records: Number of rows to generate.

    Returns:
        DataFrame matching the platform schema.
    """
    rng = np.random.default_rng(seed=7)
    lat = rng.uniform(_GOM_LAT[0], _GOM_LAT[1], size=n_records).round(4)
    lon = rng.uniform(_GOM_LON[0], _GOM_LON[1], size=n_records).round(4)
    fields = rng.choice(_FIELD_NAMES, size=n_records)
    statuses = rng.choice(["ACTIVE", "SHUT-IN", "P&A"], size=n_records)
    operators = rng.choice(_OPERATORS, size=n_records)
    areas = rng.choice(
        ["Mississippi Canyon", "Green Canyon", "Keathley Canyon", "Garden Banks"],
        size=n_records,
    )

    return pd.DataFrame(
        {
            "API_WELL_NUMBER": [f"60817{i:07d}00" for i in range(n_records)],
            "WELL_NAME": [f"WELL-{i+1:03d}" for i in range(n_records)],
            "OPERATOR_NAME": operators,
            "FIELD_NAME": fields,
            "LATITUDE": lat,
            "LONGITUDE": lon,
            "WELL_STATUS": statuses,
            "WATER_DEPTH": rng.uniform(1_000, 10_000, size=n_records).round(0),
            "AREA_NAME": areas,
        }
    )


def _sample_incident_data(n_records: int = 150) -> pd.DataFrame:
    """
    Generate synthetic FDAS incident data for heatmap visualisation.

    Args:
        n_records: Number of rows to generate.

    Returns:
        DataFrame matching the incident schema.
    """
    rng = np.random.default_rng(seed=99)
    years = rng.integers(2000, 2025, size=n_records)
    months = rng.integers(1, 13, size=n_records)

    dates = [
        pd.Timestamp(year=int(y), month=int(m), day=1) for y, m in zip(years, months)
    ]

    severity_weights = [0.35, 0.35, 0.20, 0.10]
    severities = rng.choice(_VALID_SEVERITIES, size=n_records, p=severity_weights)
    types = rng.choice(_INCIDENT_TYPES, size=n_records)
    areas = rng.choice(
        ["Mississippi Canyon", "Green Canyon", "Keathley Canyon", "Garden Banks"],
        size=n_records,
    )
    operators = rng.choice(_OPERATORS, size=n_records)

    return pd.DataFrame(
        {
            "INCIDENT_ID": [f"INC-{i+1:04d}" for i in range(n_records)],
            "INCIDENT_DATE": dates,
            "INCIDENT_YEAR": years,
            "INCIDENT_TYPE": types,
            "SEVERITY": severities,
            "AREA_NAME": areas,
            "OPERATOR": operators,
            "DESCRIPTION": [f"Synthetic incident #{i+1}" for i in range(n_records)],
        }
    )
