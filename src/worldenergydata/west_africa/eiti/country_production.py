"""
EITI multi-country production data loader.

Loads annual production volumes by country and company via the EITI
Data Explorer API. Supports Nigeria, Angola, Ghana, and other EITI
member countries.

Angola note: EITI pilot compliance only — production volume coverage
is limited and may be incomplete.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .eiti_api import EitiApiClient

logger = logging.getLogger(__name__)

MIN_VALID_YEAR = 1990
DAYS_PER_YEAR = 365

# Countries with verified production data in EITI reports.
# Angola is included but marked as pilot — data may be incomplete.
SUPPORTED_EITI_COUNTRIES = [
    "Nigeria",
    "Angola",
    "Ghana",
    "Mozambique",
    "Tanzania",
    "Liberia",
    "Cameroon",
    "Kazakhstan",
    "Azerbaijan",
]


@dataclass
class ProductionRecord:
    """Annual production record for one company in one EITI member country."""

    country: str
    year: int
    company: str
    volume_bbl: float
    commodity: str

    def __post_init__(self) -> None:
        if self.volume_bbl < 0:
            raise ValueError(
                f"volume_bbl cannot be negative, got {self.volume_bbl}"
            )
        if self.year < MIN_VALID_YEAR:
            raise ValueError(
                f"year must be >= {MIN_VALID_YEAR}, got {self.year}"
            )

    @property
    def volume_kbd(self) -> float:
        """Convert annual volume in barrels to daily rate (kbd)."""
        return self.volume_bbl / (DAYS_PER_YEAR * 1000)


def aggregate_annual_production(
    records: List[ProductionRecord],
) -> Dict[Tuple[str, int], float]:
    """
    Sum production volumes grouped by (country, year).

    Args:
        records: List of ProductionRecord instances.

    Returns:
        Dict mapping (country, year) tuples to total volume in barrels.
    """
    totals: Dict[Tuple[str, int], float] = {}
    for rec in records:
        key = (rec.country, rec.year)
        totals[key] = totals.get(key, 0.0) + rec.volume_bbl
    return totals


def _parse_production_record(raw: Dict[str, Any]) -> Optional[ProductionRecord]:
    """
    Parse a raw EITI API dict into a ProductionRecord.

    Returns None if required fields are missing or invalid.
    """
    try:
        return ProductionRecord(
            country=str(raw["country"]),
            year=int(raw["year"]),
            company=str(raw.get("company", "Unknown")),
            volume_bbl=float(raw.get("volume_bbl", 0.0)),
            commodity=str(raw.get("commodity", "crude_oil")),
        )
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping malformed production record %s: %s", raw, exc)
        return None


class CountryProductionLoader:
    """
    Loads EITI annual production data for one or more countries.

    Validates country against the supported list and delegates to
    EitiApiClient for data retrieval.
    """

    def __init__(self, cache_enabled: bool = True):
        self._client = EitiApiClient(cache_enabled=cache_enabled)

    def load(
        self,
        country: str,
        year: int,
        company: Optional[str] = None,
    ) -> List[ProductionRecord]:
        """
        Load production records for a country and year.

        Args:
            country: EITI member country name.
            year: Reporting year.
            company: Optional company name filter.

        Returns:
            List of ProductionRecord instances.

        Raises:
            ValueError: If country is not in SUPPORTED_EITI_COUNTRIES.
        """
        if country not in SUPPORTED_EITI_COUNTRIES:
            raise ValueError(
                f"'{country}' is not a supported EITI country. "
                f"Supported: {SUPPORTED_EITI_COUNTRIES}"
            )

        raw_records = self._client.get_production_data(
            country=country, year=year, company=company
        )
        records = []
        for raw in raw_records:
            parsed = _parse_production_record(raw)
            if parsed is not None:
                records.append(parsed)

        logger.info(
            "Loaded %d EITI production records for %s %d",
            len(records),
            country,
            year,
        )
        return records

    def load_multiple(
        self,
        countries: List[str],
        year: int,
    ) -> List[ProductionRecord]:
        """
        Load production records for multiple countries in one year.

        Unsupported countries are skipped with a warning.

        Args:
            countries: List of EITI member country names.
            year: Reporting year.

        Returns:
            Combined list of ProductionRecord instances.
        """
        all_records: List[ProductionRecord] = []
        for country in countries:
            try:
                records = self.load(country=country, year=year)
                all_records.extend(records)
            except ValueError as exc:
                logger.warning("Skipping unsupported country: %s", exc)
            except Exception as exc:
                logger.warning(
                    "Failed to load EITI data for %s %d: %s",
                    country,
                    year,
                    exc,
                )

        return all_records
