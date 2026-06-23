"""
EITI government revenue and company payment data loader.

Provides access to EITI reconciliation data on government revenues
and company payments-to-government (royalties, taxes, profit oil, etc.)
for EITI member countries.

Also provides cross-validation logic to compare EITI Nigeria production
totals against NUPRC PDF-sourced totals.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .eiti_api import EitiApiClient

logger = logging.getLogger(__name__)

DAYS_PER_YEAR = 365


@dataclass
class PaymentRecord:
    """A single company payment-to-government record from EITI."""

    country: str
    year: int
    company: str
    payment_type: str
    amount_usd: float

    def __post_init__(self) -> None:
        if self.amount_usd < 0:
            raise ValueError(f"amount_usd cannot be negative, got {self.amount_usd}")


def aggregate_by_company(
    records: List[PaymentRecord],
    year: Optional[int] = None,
) -> Dict[str, float]:
    """
    Sum payment amounts grouped by company name.

    Args:
        records: List of PaymentRecord instances.
        year: Optional year filter; if None, all years are included.

    Returns:
        Dict mapping company name to total payment amount in USD.
    """
    filtered = records if year is None else [r for r in records if r.year == year]
    totals: Dict[str, float] = {}
    for rec in filtered:
        totals[rec.company] = totals.get(rec.company, 0.0) + rec.amount_usd
    return totals


def aggregate_by_payment_type(
    records: List[PaymentRecord],
    year: Optional[int] = None,
) -> Dict[str, float]:
    """
    Sum payment amounts grouped by payment type.

    Args:
        records: List of PaymentRecord instances.
        year: Optional year filter.

    Returns:
        Dict mapping payment type to total amount in USD.
    """
    filtered = records if year is None else [r for r in records if r.year == year]
    totals: Dict[str, float] = {}
    for rec in filtered:
        totals[rec.payment_type] = totals.get(rec.payment_type, 0.0) + rec.amount_usd
    return totals


def cross_validate_nuprc_eiti(
    nuprc_total_kbd: float,
    eiti_total_bbl: float,
    year: int,
) -> Dict[str, Any]:
    """
    Cross-validate Nigeria production totals from NUPRC (PDF) vs EITI (API).

    Converts NUPRC kbd to annual barrels for comparison.
    EITI has 18-24 month publication lag, so perfect alignment is rare.

    Args:
        nuprc_total_kbd: Average annual production from NUPRC in kbd.
        eiti_total_bbl: Total annual production from EITI in barrels.
        year: Reporting year (used in output context only).

    Returns:
        Dict with keys: nuprc_bbl, eiti_bbl, discrepancy_bbl,
        discrepancy_pct, year, note.
    """
    nuprc_bbl = nuprc_total_kbd * 1000 * DAYS_PER_YEAR
    discrepancy_bbl = nuprc_bbl - eiti_total_bbl
    discrepancy_pct = (
        (discrepancy_bbl / eiti_total_bbl * 100) if eiti_total_bbl else 0.0
    )

    return {
        "year": year,
        "nuprc_bbl": nuprc_bbl,
        "eiti_bbl": eiti_total_bbl,
        "discrepancy_bbl": discrepancy_bbl,
        "discrepancy_pct": round(discrepancy_pct, 2),
        "note": (
            "EITI data lags NUPRC by 18-24 months; " "minor discrepancies are expected"
        ),
    }


def _parse_payment_record(raw: Dict[str, Any]) -> Optional[PaymentRecord]:
    """Parse a raw EITI API dict into a PaymentRecord. Returns None on error."""
    try:
        return PaymentRecord(
            country=str(raw["country"]),
            year=int(raw["year"]),
            company=str(raw.get("company", "Unknown")),
            payment_type=str(raw.get("payment_type", "unspecified")),
            amount_usd=float(raw.get("amount_usd", 0.0)),
        )
    except (KeyError, ValueError, TypeError) as exc:
        logger.debug("Skipping malformed payment record %s: %s", raw, exc)
        return None


class PaymentDataLoader:
    """
    Loads EITI government revenue and company payment data.

    Delegates to EitiApiClient for data retrieval and parses records
    into typed PaymentRecord instances.
    """

    def __init__(self, cache_enabled: bool = True):
        self._client = EitiApiClient(cache_enabled=cache_enabled)

    def load(
        self,
        country: str,
        year: int,
        company: Optional[str] = None,
    ) -> List[PaymentRecord]:
        """
        Load payment records for a country and year.

        Args:
            country: EITI member country name.
            year: Reporting year.
            company: Optional company name filter.

        Returns:
            List of PaymentRecord instances.
        """
        raw_records = self._client.get_payment_data(
            country=country, year=year, company=company
        )
        records = []
        for raw in raw_records:
            parsed = _parse_payment_record(raw)
            if parsed is not None:
                records.append(parsed)

        logger.info(
            "Loaded %d EITI payment records for %s %d",
            len(records),
            country,
            year,
        )
        return records
