"""
Nigeria monthly blend/stream production loader.

Loads and aggregates Nigeria crude oil production data by blend/stream
from NUPRC monthly PDF reports. Provides filtering, aggregation,
and total production calculation utilities.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .nuprc_client import NuprcAPIError, NuprcClient, parse_blend_table_from_pdf

logger = logging.getLogger(__name__)

MIN_VALID_YEAR = 1960
MAX_MONTH = 12
MIN_MONTH = 1


@dataclass
class BlendRecord:
    """A single monthly production record for one Nigeria crude blend/stream."""

    blend: str
    volume_kbd: float  # thousand barrels per day (monthly average)
    month: int
    year: int

    def __post_init__(self) -> None:
        if self.volume_kbd < 0:
            raise ValueError(
                f"volume_kbd cannot be negative, got {self.volume_kbd}"
            )
        if not MIN_MONTH <= self.month <= MAX_MONTH:
            raise ValueError(
                f"month must be 1-12, got {self.month}"
            )
        if self.year < MIN_VALID_YEAR:
            raise ValueError(
                f"year must be >= {MIN_VALID_YEAR}, got {self.year}"
            )


def aggregate_by_blend(records: List[BlendRecord]) -> Dict[str, float]:
    """
    Sum production volumes grouped by blend name.

    Args:
        records: List of BlendRecord instances.

    Returns:
        Dict mapping blend name to total volume_kbd.
    """
    totals: Dict[str, float] = {}
    for rec in records:
        totals[rec.blend] = totals.get(rec.blend, 0.0) + rec.volume_kbd
    return totals


def filter_by_period(
    records: List[BlendRecord],
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> List[BlendRecord]:
    """
    Filter records by year and/or month.

    Args:
        records: List of BlendRecord instances.
        year: Optional year filter.
        month: Optional month filter.

    Returns:
        Filtered list of BlendRecord instances.
    """
    result = records
    if year is not None:
        result = [r for r in result if r.year == year]
    if month is not None:
        result = [r for r in result if r.month == month]
    return result


class BlendProductionLoader:
    """
    Loads Nigeria monthly blend production from NUPRC PDF reports.

    Uses NuprcClient for PDF download and parse_blend_table_from_pdf
    for table extraction. Handles missing or malformed PDFs gracefully.
    """

    def __init__(self, cache_enabled: bool = True):
        self._client = NuprcClient(cache_enabled=cache_enabled)

    def load(
        self,
        year: int,
        month: int,
        pdf_url: Optional[str] = None,
    ) -> List[BlendRecord]:
        """
        Load blend production records for a given year/month.

        Args:
            year: Reporting year.
            month: Reporting month (1-12).
            pdf_url: Optional explicit PDF URL; if None, attempts construction.

        Returns:
            List of BlendRecord. Empty list if PDF unavailable or parse fails.
        """
        url = pdf_url or self._build_pdf_url(year, month)
        try:
            pdf_bytes = self._client.download_pdf(url)
        except NuprcAPIError as exc:
            logger.warning(
                "Could not download NUPRC PDF for %04d-%02d: %s",
                year,
                month,
                exc,
            )
            return []

        raw_rows = parse_blend_table_from_pdf(pdf_bytes)
        records = []
        for row in raw_rows:
            try:
                records.append(
                    BlendRecord(
                        blend=row["blend"],
                        volume_kbd=float(row["volume_kbd"]),
                        month=row.get("month") or month,
                        year=row.get("year") or year,
                    )
                )
            except (ValueError, KeyError) as exc:
                logger.debug("Skipping malformed row %s: %s", row, exc)

        return records

    def total_production(self, records: List[BlendRecord]) -> float:
        """
        Sum total production across all blend records.

        Args:
            records: List of BlendRecord instances.

        Returns:
            Total volume in kbd (thousand barrels per day).
        """
        return sum(r.volume_kbd for r in records)

    def _build_pdf_url(self, year: int, month: int) -> str:
        """
        Construct a candidate NUPRC PDF URL for a given year/month.

        NUPRC URLs do not follow a strict pattern; this returns a
        best-guess URL that may not exist. Callers must handle failures.
        """
        month_names = [
            "", "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ]
        month_name = month_names[month]
        return (
            f"https://www.nuprc.gov.ng/wp-content/uploads/"
            f"{year}/{month:02d}/"
            f"monthly-oil-production-status-{month_name}-{year}.pdf"
        )
