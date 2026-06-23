"""Query interface for the curated subsea-manifold supplier database.

Loads ``data/modules/subsea/curated/manifold_suppliers.csv`` (the
human-readable source of truth), validates every row against
:class:`ManifoldSupplierSchema`, and exposes simple filters.

Example::

    from worldenergydata.subsea import ManifoldSupplierLoader

    loader = ManifoldSupplierLoader()
    oems = loader.query(role="OEM", tier="tier_1")
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.subsea.schemas.manifold_supplier import (
    ManifoldSupplierSchema,
)

logger = logging.getLogger(__name__)

_DEFAULT_CSV = get_module_data_safe("subsea") / "curated" / "manifold_suppliers.csv"


class ManifoldSupplierLoader:
    """Loader / query interface for the curated manifold-supplier records."""

    def __init__(self, csv_path: Optional[Path] = None) -> None:
        self._csv_path = Path(csv_path) if csv_path else _DEFAULT_CSV
        self._records: Optional[list[ManifoldSupplierSchema]] = None

    def _load(self) -> list[ManifoldSupplierSchema]:
        if self._records is None:
            if not self._csv_path.exists():
                logger.warning("Supplier DB not found: %s", self._csv_path)
                self._records = []
                return self._records
            with open(self._csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self._records = [ManifoldSupplierSchema(**row) for row in rows]
            logger.info(
                "Loaded %d manifold suppliers from %s",
                len(self._records),
                self._csv_path,
            )
        return self._records

    def all(self) -> list[ManifoldSupplierSchema]:
        """Return every validated supplier record."""
        return list(self._load())

    def query(
        self,
        *,
        role: Optional[str] = None,
        tier: Optional[str] = None,
        country: Optional[str] = None,
        min_water_depth_m: Optional[int] = None,
    ) -> list[ManifoldSupplierSchema]:
        """Filter suppliers by role, tier, HQ country, and depth capability."""
        results = self._load()
        if role is not None:
            results = [r for r in results if r.MANIFOLD_ROLE == role]
        if tier is not None:
            results = [r for r in results if r.ROLE_TIER == tier]
        if country is not None:
            needle = country.lower()
            results = [
                r for r in results if r.HQ_COUNTRY and needle in r.HQ_COUNTRY.lower()
            ]
        if min_water_depth_m is not None:
            results = [
                r
                for r in results
                if r.MAX_WATER_DEPTH_M is not None
                and r.MAX_WATER_DEPTH_M >= min_water_depth_m
            ]
        return results

    def get(self, company: str) -> Optional[ManifoldSupplierSchema]:
        """Return the record whose COMPANY contains ``company`` (case-insensitive)."""
        needle = company.lower()
        for r in self._load():
            if needle in r.COMPANY.lower():
                return r
        return None
