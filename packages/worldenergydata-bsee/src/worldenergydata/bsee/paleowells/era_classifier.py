"""Geological Era Classifier for BSEE wells.

Classifies wells and fields by geological era using paleontological
data from the BSEE Paleowells dataset.
"""

import logging
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class GeologicalEraClassifier:
    """Classifies wells and fields by geological era.

    Uses Paleowells.csv data to extract era from the 'Paleo Age' column
    and map wells (via API Well Number) to their dominant geological era.
    """

    ERAS = [
        "Paleocene",
        "Eocene",
        "Oligocene",
        "Miocene",
        "Pliocene",
        "Pleistocene",
    ]

    _ERA_PATTERN = "|".join(ERAS)

    def __init__(
        self,
        paleowells_csv: Optional[Path] = None,
        dataframe: Optional[pd.DataFrame] = None,
    ):
        """Initialize with either a CSV path or a pre-loaded DataFrame."""
        if dataframe is not None:
            self._df = dataframe
        elif paleowells_csv is not None:
            self._df = self._load_csv(paleowells_csv)
        else:
            self._df = pd.DataFrame()

        self._well_eras: Optional[Dict[str, str]] = None
        if not self._df.empty and "Paleo Age" in self._df.columns:
            self._extract_eras()

    def _load_csv(self, csv_path: Path) -> pd.DataFrame:
        """Load Paleowells CSV file."""
        try:
            df = pd.read_csv(csv_path)
            logger.info("Loaded %d paleowells records from %s", len(df), csv_path)
            return df
        except Exception as e:
            logger.error("Error loading paleowells CSV: %s", e)
            return pd.DataFrame()

    def _extract_eras(self) -> None:
        """Extract era from Paleo Age column for each record."""
        self._df = self._df.copy()
        self._df["_era"] = self._df["Paleo Age"].str.extract(
            rf"({self._ERA_PATTERN})", expand=False
        )

    def classify_well(self, api_well_number: str) -> Optional[str]:
        """Classify a single well by its dominant geological era.

        Returns the era with the most records for this well, or None if
        the well is not found or has no era data.
        """
        if self._df.empty or "API Well Number" not in self._df.columns:
            return None

        api_str = str(api_well_number).strip()
        well_df = self._df[self._df["API Well Number"].astype(str) == api_str]

        if well_df.empty:
            return None

        era_counts = well_df["_era"].dropna().value_counts()
        if era_counts.empty:
            return None

        return era_counts.index[0]

    def classify_field(self, field_wells: List[str]) -> str:
        """Classify a field by the dominant era of its wells.

        Returns the era that appears most frequently across all wells
        in the field, or 'Unknown' if no era data is available.
        """
        if not field_wells:
            return "Unknown"

        era_counter: Counter = Counter()
        for api in field_wells:
            era = self.classify_well(api)
            if era:
                era_counter[era] += 1

        if not era_counter:
            return "Unknown"

        return era_counter.most_common(1)[0][0]

    def get_well_eras(self) -> Dict[str, str]:
        """Get era classification for all wells in the dataset.

        Returns dict mapping API Well Number -> era string.
        Wells without era data are excluded.
        """
        if self._well_eras is not None:
            return self._well_eras

        if self._df.empty or "_era" not in self._df.columns:
            self._well_eras = {}
            return self._well_eras

        # For each well, pick the dominant era
        result = {}
        for api, group in self._df.groupby("API Well Number"):
            era_counts = group["_era"].dropna().value_counts()
            if not era_counts.empty:
                result[str(api)] = era_counts.index[0]

        self._well_eras = result
        return self._well_eras

    def get_era_summary(self) -> Dict[str, int]:
        """Get summary of unique wells per era.

        Returns dict mapping era name -> count of unique wells.
        """
        well_eras = self.get_well_eras()
        counter: Counter = Counter(well_eras.values())
        return dict(counter)
