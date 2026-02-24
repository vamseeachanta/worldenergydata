"""
ABOUTME: USCG MISLE public data CSV loader for incident taxonomy pipeline.
ABOUTME: Reads USCG Marine Casualty Investigation CSV exports and normalises to taxonomy schema.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from worldenergydata.marine_safety.analysis.incidents.incident_taxonomy import (
    IncidentDataFrameNormaliser,
    IncidentTaxonomyClassifier,
    TaxonomyRecord,
    USCG_COLUMN_MAP,
)

logger = logging.getLogger(__name__)

# USCG MISLE public data portal
# Bulk CSV exports are available from:
# https://www.dco.uscg.mil/Our-Organization/Assistant-Commandant-for-Prevention-Policy-CG-5P/
#   Inspections-Compliance-CG-5PC-/Office-of-Investigations-Casualty-Analysis/
USCG_PUBLIC_DATA_URL = (
    "https://www.dco.uscg.mil/Our-Organization/"
    "Assistant-Commandant-for-Prevention-Policy-CG-5P/"
    "Inspections-Compliance-CG-5PC-/"
    "Office-of-Investigations-Casualty-Analysis/"
)

# Expected columns in a standard USCG MISLE CSV export.
# The public download may use slightly different names depending on the report year;
# the USCG_COLUMN_MAP handles the most common variants.
USCG_EXPECTED_COLUMNS = {
    "report_id",
    "incident_date",
    "vessel_name",
    "vessel_type",
    "primary_cause",
    "narrative",
}


def load_uscg_csv(
    file_path: str | Path,
    encoding: str = "latin-1",
    year_filter: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load a USCG MISLE public CSV export file into a normalised DataFrame.

    The function applies the standard column map, coerces numeric fields,
    and optionally filters to a specific report year.

    Args:
        file_path: Path to the USCG CSV file on disk.
        encoding: Character encoding of the CSV (USCG exports are often latin-1).
        year_filter: If given, keep only rows where incident_date year matches.

    Returns:
        Normalised DataFrame ready for taxonomy classification.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file cannot be parsed as a CSV.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"USCG data file not found: {path}")

    try:
        raw_df = pd.read_csv(path, encoding=encoding, low_memory=False)
    except Exception as exc:
        raise ValueError(f"Failed to parse USCG CSV at {path}: {exc}") from exc

    logger.info("Loaded %d rows from USCG CSV: %s", len(raw_df), path.name)

    normaliser = IncidentDataFrameNormaliser()
    df = normaliser.normalise(raw_df, source="uscg")

    if year_filter is not None and "incident_date" in df.columns:
        df = _filter_by_year(df, year_filter)
        logger.info("After year filter (%d): %d rows remain", year_filter, len(df))

    return df


def load_uscg_csv_to_records(
    file_path: str | Path,
    encoding: str = "latin-1",
    year_filter: Optional[int] = None,
    classifier: Optional[IncidentTaxonomyClassifier] = None,
) -> List[TaxonomyRecord]:
    """
    Load a USCG CSV and return classified TaxonomyRecord instances.

    Args:
        file_path: Path to the USCG CSV file.
        encoding: CSV encoding.
        year_filter: Optional year to filter records.
        classifier: Optional pre-built IncidentTaxonomyClassifier.

    Returns:
        List of TaxonomyRecord with root_cause populated.
    """
    df = load_uscg_csv(file_path, encoding=encoding, year_filter=year_filter)
    normaliser = IncidentDataFrameNormaliser()
    records = normaliser.to_taxonomy_records(df, source="uscg", classifier=classifier)
    logger.info("Produced %d taxonomy records from USCG data", len(records))
    return records


def load_dataframe_as_uscg(
    df: pd.DataFrame,
    classifier: Optional[IncidentTaxonomyClassifier] = None,
) -> List[TaxonomyRecord]:
    """
    Treat an in-memory DataFrame as USCG MISLE data and classify it.

    Useful for unit testing without a file on disk.

    Args:
        df: DataFrame with USCG-style columns (raw or pre-renamed).
        classifier: Optional pre-built classifier.

    Returns:
        List of TaxonomyRecord instances.
    """
    normaliser = IncidentDataFrameNormaliser()
    normalised = normaliser.normalise(df, source="uscg")
    return normaliser.to_taxonomy_records(normalised, source="uscg", classifier=classifier)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filter_by_year(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Filter DataFrame rows to the specified calendar year in incident_date."""
    try:
        dates = pd.to_datetime(df["incident_date"], errors="coerce")
        mask = dates.dt.year == year
        return df[mask].copy()
    except Exception as exc:
        logger.warning("Year filtering failed: %s — returning unfiltered data", exc)
        return df


def describe_uscg_dataset(df: pd.DataFrame) -> dict:
    """
    Return a brief summary dict describing a USCG normalised DataFrame.

    Args:
        df: Normalised USCG DataFrame.

    Returns:
        Dict with keys: total_records, date_range, vessel_types, columns_present.
    """
    if df.empty:
        return {"total_records": 0, "date_range": None, "vessel_types": [], "columns_present": []}

    date_range = None
    if "incident_date" in df.columns:
        dates = pd.to_datetime(df["incident_date"], errors="coerce").dropna()
        if not dates.empty:
            date_range = (dates.min().date().isoformat(), dates.max().date().isoformat())

    vessel_types: List[str] = []
    if "vessel_type" in df.columns:
        vessel_types = sorted(df["vessel_type"].dropna().unique().tolist())

    return {
        "total_records": len(df),
        "date_range": date_range,
        "vessel_types": vessel_types,
        "columns_present": list(df.columns),
    }
