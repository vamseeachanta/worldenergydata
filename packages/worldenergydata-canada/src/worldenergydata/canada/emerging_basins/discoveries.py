"""Query interface for the curated frontier-basin discovery dataset.

Loads ``data/modules/frontier_basins/curated/frontier_discoveries.csv`` (the
human-readable source of truth), validates every row against
:class:`DiscoverySchema`, and exposes simple filters.

This complements the basin-level :mod:`watch_list` (one stub per basin) with a
discovery-level catalog (one row per well/discovery) for the three frontier
deepwater plays tracked in issue #603 — Guyana (Stabroek + adjacent),
Suriname (Block 58 + adjacent), and Namibia (Orange Basin).

Example::

    from worldenergydata.canada.emerging_basins import FrontierDiscoveryLoader

    loader = FrontierDiscoveryLoader()
    guyana = loader.query(country="Guyana", tier="high")
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

from worldenergydata.canada.emerging_basins.discovery_schema import DiscoverySchema
from worldenergydata.common.data_resolver import get_module_data_safe

logger = logging.getLogger(__name__)

_DEFAULT_CSV = (
    get_module_data_safe("frontier_basins") / "curated" / "frontier_discoveries.csv"
)


class FrontierDiscoveryLoader:
    """Loader / query interface for curated frontier-basin discovery records."""

    def __init__(self, csv_path: Optional[Path] = None) -> None:
        self._csv_path = Path(csv_path) if csv_path else _DEFAULT_CSV
        self._records: Optional[list[DiscoverySchema]] = None

    def _load(self) -> list[DiscoverySchema]:
        if self._records is None:
            if not self._csv_path.exists():
                logger.warning("Frontier discovery DB not found: %s", self._csv_path)
                self._records = []
                return self._records
            with open(self._csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self._records = [DiscoverySchema(**row) for row in rows]
            logger.info(
                "Loaded %d frontier discoveries from %s",
                len(self._records),
                self._csv_path,
            )
        return self._records

    def all(self) -> list[DiscoverySchema]:
        """Return every validated discovery record."""
        return list(self._load())

    def query(
        self,
        *,
        country: Optional[str] = None,
        block: Optional[str] = None,
        operator: Optional[str] = None,
        tier: Optional[str] = None,
        status: Optional[str] = None,
        min_water_depth_m: Optional[int] = None,
    ) -> list[DiscoverySchema]:
        """Filter discoveries by country, block, operator, tier, status, depth."""
        results = self._load()
        if country is not None:
            results = [r for r in results if r.COUNTRY == country]
        if block is not None:
            results = [r for r in results if r.BLOCK == block]
        if operator is not None:
            results = [
                r for r in results if operator.lower() in (r.OPERATOR or "").lower()
            ]
        if tier is not None:
            results = [r for r in results if r.CONFIDENCE_TIER == tier]
        if status is not None:
            results = [r for r in results if r.STATUS == status]
        if min_water_depth_m is not None:
            results = [
                r
                for r in results
                if r.WATER_DEPTH_M is not None and r.WATER_DEPTH_M >= min_water_depth_m
            ]
        return results

    def get(self, name: str) -> Optional[DiscoverySchema]:
        """Return the first discovery whose name contains ``name`` (case-insensitive)."""
        needle = name.lower()
        for r in self._load():
            if needle in r.DISCOVERY_NAME.lower():
                return r
        return None
