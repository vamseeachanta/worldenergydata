"""
ABOUTME: MAIB occurrence CSV loader for the incident taxonomy pipeline.
ABOUTME: Reads MAIB accident data files and normalises to taxonomy schema.
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
)

logger = logging.getLogger(__name__)

# MAIB statistical data downloads are available from:
# https://www.gov.uk/government/statistical-data-sets/maib-accident-data
MAIB_PUBLIC_DATA_URL = (
    "https://www.gov.uk/government/statistical-data-sets/maib-accident-data"
)

# Expected core columns in a standard MAIB occurrence CSV export.
MAIB_EXPECTED_COLUMNS = {
    "Occurrence_Id",
    "Date",
    "Main_Event",
    "Vessel_Name",
    "Vessel_Type",
}


class MAIBLoader:
    """
    Loader for MAIB (UK Marine Accident Investigation Branch) occurrence data.

    Reads MAIB annual occurrence CSV exports and normalises them to the shared
    taxonomy schema (same canonical column set used by load_uscg_csv).

    MAIB publishes CSV datasets at:
    https://www.gov.uk/government/statistical-data-sets/maib-accident-data

    The occurrence CSV uses a semicolon delimiter and includes columns such as
    Occurrence_Id, Date, Main_Event, Vessel_Name, Vessel_Type, Latitude,
    Longitude, Deaths, and Injuries.

    Usage::

        loader = MAIBLoader()
        df = loader.load("maib_occurrences.csv")
        records = loader.load_to_records("maib_occurrences.csv")
    """

    def __init__(
        self,
        delimiter: str = ";",
        encoding: str = "utf-8",
    ) -> None:
        """
        Initialise MAIBLoader.

        Args:
            delimiter: Column delimiter used in MAIB CSV files (default ";").
            encoding: File encoding (default "utf-8").
        """
        self._delimiter = delimiter
        self._encoding = encoding
        self._normaliser = IncidentDataFrameNormaliser()

    def load(
        self,
        file_path: str | Path,
        year_filter: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Load a MAIB occurrence CSV and return a normalised DataFrame.

        Applies the MAIB column map, coerces numeric and coordinate fields,
        and optionally filters to a specific incident year.

        Args:
            file_path: Path to the MAIB occurrence CSV file on disk.
            year_filter: If given, keep only rows where incident_date year matches.

        Returns:
            Normalised DataFrame ready for taxonomy classification.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            ValueError: If the file cannot be parsed as a CSV.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"MAIB data file not found: {path}")

        try:
            raw_df = pd.read_csv(
                path,
                delimiter=self._delimiter,
                encoding=self._encoding,
                low_memory=False,
            )
        except Exception as exc:
            raise ValueError(f"Failed to parse MAIB CSV at {path}: {exc}") from exc

        logger.info("Loaded %d rows from MAIB CSV: %s", len(raw_df), path.name)

        df = self._normaliser.normalise(raw_df, source="maib")

        if year_filter is not None and "incident_date" in df.columns:
            df = _filter_by_year(df, year_filter)
            logger.info("After year filter (%d): %d rows remain", year_filter, len(df))

        return df

    def load_to_records(
        self,
        file_path: str | Path,
        year_filter: Optional[int] = None,
        classifier: Optional[IncidentTaxonomyClassifier] = None,
    ) -> List[TaxonomyRecord]:
        """
        Load a MAIB CSV and return classified TaxonomyRecord instances.

        Args:
            file_path: Path to the MAIB CSV file.
            year_filter: Optional year to filter records.
            classifier: Optional pre-built IncidentTaxonomyClassifier.

        Returns:
            List of TaxonomyRecord with root_cause populated.
        """
        df = self.load(file_path, year_filter=year_filter)
        records = self._normaliser.to_taxonomy_records(
            df, source="maib", classifier=classifier
        )
        logger.info("Produced %d taxonomy records from MAIB data", len(records))
        return records


def load_maib_csv(
    file_path: str | Path,
    delimiter: str = ";",
    encoding: str = "utf-8",
    year_filter: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load a MAIB occurrence CSV export file into a normalised DataFrame.

    Convenience function wrapping MAIBLoader for one-shot usage.

    Args:
        file_path: Path to the MAIB CSV file on disk.
        delimiter: Column delimiter (default ";").
        encoding: Character encoding of the CSV (default "utf-8").
        year_filter: If given, keep only rows where incident_date year matches.

    Returns:
        Normalised DataFrame ready for taxonomy classification.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file cannot be parsed as a CSV.
    """
    loader = MAIBLoader(delimiter=delimiter, encoding=encoding)
    return loader.load(file_path, year_filter=year_filter)


def load_maib_csv_to_records(
    file_path: str | Path,
    delimiter: str = ";",
    encoding: str = "utf-8",
    year_filter: Optional[int] = None,
    classifier: Optional[IncidentTaxonomyClassifier] = None,
) -> List[TaxonomyRecord]:
    """
    Load a MAIB CSV and return classified TaxonomyRecord instances.

    Args:
        file_path: Path to the MAIB CSV file.
        delimiter: Column delimiter (default ";").
        encoding: CSV encoding.
        year_filter: Optional year to filter records.
        classifier: Optional pre-built IncidentTaxonomyClassifier.

    Returns:
        List of TaxonomyRecord with root_cause populated.
    """
    loader = MAIBLoader(delimiter=delimiter, encoding=encoding)
    return loader.load_to_records(
        file_path, year_filter=year_filter, classifier=classifier
    )


def load_dataframe_as_maib(
    df: pd.DataFrame,
    classifier: Optional[IncidentTaxonomyClassifier] = None,
) -> List[TaxonomyRecord]:
    """
    Treat an in-memory DataFrame as MAIB occurrence data and classify it.

    Useful for unit testing without a file on disk.

    Args:
        df: DataFrame with MAIB-style columns (raw or pre-renamed).
        classifier: Optional pre-built classifier.

    Returns:
        List of TaxonomyRecord instances.
    """
    normaliser = IncidentDataFrameNormaliser()
    normalised = normaliser.normalise(df, source="maib")
    return normaliser.to_taxonomy_records(
        normalised, source="maib", classifier=classifier
    )


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


def describe_maib_dataset(df: pd.DataFrame) -> dict:
    """
    Return a brief summary dict describing a MAIB normalised DataFrame.

    Args:
        df: Normalised MAIB DataFrame.

    Returns:
        Dict with keys: total_records, date_range, vessel_types, columns_present.
    """
    if df.empty:
        return {
            "total_records": 0,
            "date_range": None,
            "vessel_types": [],
            "columns_present": [],
        }

    date_range = None
    if "incident_date" in df.columns:
        dates = pd.to_datetime(df["incident_date"], errors="coerce").dropna()
        if not dates.empty:
            date_range = (
                dates.min().date().isoformat(),
                dates.max().date().isoformat(),
            )

    vessel_types: List[str] = []
    if "vessel_type" in df.columns:
        vessel_types = sorted(df["vessel_type"].dropna().unique().tolist())

    return {
        "total_records": len(df),
        "date_range": date_range,
        "vessel_types": vessel_types,
        "columns_present": list(df.columns),
    }
