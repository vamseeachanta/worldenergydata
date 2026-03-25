"""International country-level oil production from EIA INTL series.

EIA series format: INTL.57-1-{country_code}-TBPD.A
  (annual, thousand barrels per day)

This module ships built-in mock data for 25 countries (year 2023 estimates)
so tests run without any live API access. For live data, use EIAApiClient
with the INTL series IDs.

Reference: EIA International Energy Statistics
https://www.eia.gov/international/data/world
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


# Top crude + condensate producers (kbd, approximate 2023 estimates)
# Source: EIA International Energy Statistics
TOP_PRODUCERS: List[str] = [
    "United States",
    "Saudi Arabia",
    "Russia",
    "Canada",
    "Iraq",
    "China",
    "UAE",
    "Brazil",
    "Iran",
    "Kuwait",
    "Norway",
    "Mexico",
    "Kazakhstan",
    "Libya",
    "Nigeria",
    "Venezuela",
    "Algeria",
    "Angola",
    "Oman",
    "UK",
]

# Built-in mock data for 25 countries (2023 annual, kbd)
MOCK_COUNTRY_PRODUCTION: List[Dict[str, Any]] = [
    {"country": "United States", "year": 2023, "production_kbd": 12900},
    {"country": "Saudi Arabia",  "year": 2023, "production_kbd": 11900},
    {"country": "Russia",        "year": 2023, "production_kbd": 10800},
    {"country": "Canada",        "year": 2023, "production_kbd": 5600},
    {"country": "Iraq",          "year": 2023, "production_kbd": 4400},
    {"country": "China",         "year": 2023, "production_kbd": 4200},
    {"country": "UAE",           "year": 2023, "production_kbd": 4000},
    {"country": "Brazil",        "year": 2023, "production_kbd": 3700},
    {"country": "Iran",          "year": 2023, "production_kbd": 3400},
    {"country": "Kuwait",        "year": 2023, "production_kbd": 2700},
    {"country": "Norway",        "year": 2023, "production_kbd": 1900},
    {"country": "Mexico",        "year": 2023, "production_kbd": 1900},
    {"country": "Kazakhstan",    "year": 2023, "production_kbd": 1900},
    {"country": "Libya",         "year": 2023, "production_kbd": 1200},
    {"country": "Nigeria",       "year": 2023, "production_kbd": 1200},
    {"country": "Venezuela",     "year": 2023, "production_kbd": 800},
    {"country": "Algeria",       "year": 2023, "production_kbd": 1000},
    {"country": "Angola",        "year": 2023, "production_kbd": 1100},
    {"country": "Oman",          "year": 2023, "production_kbd": 1000},
    {"country": "UK",            "year": 2023, "production_kbd": 700},
    {"country": "Ecuador",       "year": 2023, "production_kbd": 480},
    {"country": "Malaysia",      "year": 2023, "production_kbd": 560},
    {"country": "Argentina",     "year": 2023, "production_kbd": 640},
    {"country": "Colombia",      "year": 2023, "production_kbd": 750},
    {"country": "Azerbaijan",    "year": 2023, "production_kbd": 680},
]


class CountryProductionLoader:
    """Load and query EIA international country production data."""

    _REQUIRED_COLS = ["country", "year", "production_kbd"]

    def load(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert country production records to normalised DataFrame.

        Args:
            records: List of dicts with 'country', 'year',
                     'production_kbd' keys.

        Returns:
            DataFrame with columns: country, year, production_kbd.
            Empty DataFrame (same columns) if records is empty.
        """
        if not records:
            return pd.DataFrame(columns=self._REQUIRED_COLS)

        rows = []
        for rec in records:
            rows.append({
                "country": rec.get("country", ""),
                "year": int(rec.get("year", 0)),
                "production_kbd": float(rec.get("production_kbd", 0.0)),
            })

        return pd.DataFrame(rows)[self._REQUIRED_COLS].reset_index(drop=True)

    def filter_country(self, df: pd.DataFrame, country: str) -> pd.DataFrame:
        """Return rows for a specific country (exact match)."""
        return df[df["country"] == country].copy()

    def filter_year(self, df: pd.DataFrame, year: int) -> pd.DataFrame:
        """Return rows for a specific year."""
        return df[df["year"] == year].copy()

    def top_producers(
        self,
        df: pd.DataFrame,
        n: int = 10,
        year: Optional[int] = None,
    ) -> pd.DataFrame:
        """Return top N producing countries sorted by production_kbd descending.

        Args:
            df: Normalised production DataFrame.
            n: Number of top producers to return.
            year: If given, filter to that year first.

        Returns:
            DataFrame with top N rows, sorted descending by production_kbd.
        """
        if df.empty:
            return df.copy()

        filtered = df if year is None else self.filter_year(df, year)
        # Take per-country max if multiple years present
        aggregated = (
            filtered.groupby("country")["production_kbd"]
            .max()
            .reset_index()
            .sort_values("production_kbd", ascending=False)
            .head(n)
            .reset_index(drop=True)
        )
        return aggregated
