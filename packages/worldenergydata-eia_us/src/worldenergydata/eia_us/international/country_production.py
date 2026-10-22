"""International country-level oil production from EIA INTL series.

EIA series format: INTL.57-1-{country_code}-TBPD.A
  (annual, thousand barrels per day)

The historical built-in estimates are synthetic fixtures with no qualified
source revision. Their engineering status is NOT_EVALUATED. For live data,
use EIAApiClient with the INTL series IDs and qualify the source separately.

Reference: EIA International Energy Statistics
https://www.eia.gov/international/data/world
"""

import logging
from typing import Any, ClassVar

import pandas as pd

from ..production.measurement import (
    RATE,
    declared_unit,
    monthly_period,
    number_or_missing,
)

logger = logging.getLogger(__name__)


# Top crude + condensate producers (kbd, approximate 2023 estimates)
# Historical ranking only; no revision-qualified source is available.
TOP_PRODUCERS: list[str] = [
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
MOCK_COUNTRY_PRODUCTION: list[dict[str, Any]] = [
    {"country": "United States", "year": 2023, "production_kbd": 12900},
    {"country": "Saudi Arabia", "year": 2023, "production_kbd": 11900},
    {"country": "Russia", "year": 2023, "production_kbd": 10800},
    {"country": "Canada", "year": 2023, "production_kbd": 5600},
    {"country": "Iraq", "year": 2023, "production_kbd": 4400},
    {"country": "China", "year": 2023, "production_kbd": 4200},
    {"country": "UAE", "year": 2023, "production_kbd": 4000},
    {"country": "Brazil", "year": 2023, "production_kbd": 3700},
    {"country": "Iran", "year": 2023, "production_kbd": 3400},
    {"country": "Kuwait", "year": 2023, "production_kbd": 2700},
    {"country": "Norway", "year": 2023, "production_kbd": 1900},
    {"country": "Mexico", "year": 2023, "production_kbd": 1900},
    {"country": "Kazakhstan", "year": 2023, "production_kbd": 1900},
    {"country": "Libya", "year": 2023, "production_kbd": 1200},
    {"country": "Nigeria", "year": 2023, "production_kbd": 1200},
    {"country": "Venezuela", "year": 2023, "production_kbd": 800},
    {"country": "Algeria", "year": 2023, "production_kbd": 1000},
    {"country": "Angola", "year": 2023, "production_kbd": 1100},
    {"country": "Oman", "year": 2023, "production_kbd": 1000},
    {"country": "UK", "year": 2023, "production_kbd": 700},
    {"country": "Ecuador", "year": 2023, "production_kbd": 480},
    {"country": "Malaysia", "year": 2023, "production_kbd": 560},
    {"country": "Argentina", "year": 2023, "production_kbd": 640},
    {"country": "Colombia", "year": 2023, "production_kbd": 750},
    {"country": "Azerbaijan", "year": 2023, "production_kbd": 680},
]


# These historical mock estimates have no revision-qualified source. They are
# synthetic fixtures only; existing numbers are not qualified engineering data.
MOCK_COUNTRY_PRODUCTION = [
    {
        **row,
        "unit": "kbd",
        "basis": RATE,
        "source": "synthetic",
        "source_revision": None,
        "engineering_status": "NOT_EVALUATED",
    }
    for row in MOCK_COUNTRY_PRODUCTION
]


class CountryProductionLoader:
    """Load and query EIA international country production data."""

    _REQUIRED_COLS: ClassVar[list[str]] = [
        "country",
        "year",
        "production_kbd",
        "production_kbd_missing",
        "unit",
        "basis",
        "source",
        "source_revision",
        "engineering_status",
    ]

    def load(self, records: list[dict[str, Any]]) -> pd.DataFrame:
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
            # Named production_kbd declares thousand bbl/day, not annual volume.
            declared_unit(rec, schema_unit="kbd")
            year = rec.get("year")
            if isinstance(year, str) and year.isascii() and year.isdigit():
                year = int(year)
            if isinstance(year, bool) or not isinstance(year, int):
                raise TypeError("Country production year must be an integer")
            monthly_period(f"{year:04d}-01")
            value = number_or_missing(rec.get("production_kbd"))
            rows.append(
                {
                    "country": rec.get("country", ""),
                    "year": year,
                    "production_kbd": value,
                    "production_kbd_missing": pd.isna(value),
                    "unit": "kbd",
                    "basis": RATE,
                    "source": rec.get("source", "unspecified"),
                    "source_revision": rec.get("source_revision"),
                    # A supplied revision is evidence, not engineering qualification.
                    "engineering_status": "NOT_EVALUATED",
                }
            )
        return pd.DataFrame(rows, columns=self._REQUIRED_COLS)

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
        year: int | None = None,
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
        # Select actual rows so provenance and missing state survive ranking.
        return (
            filtered.sort_values("production_kbd", ascending=False, kind="stable")
            .drop_duplicates("country")
            .head(n)
            .reset_index(drop=True)
        )
