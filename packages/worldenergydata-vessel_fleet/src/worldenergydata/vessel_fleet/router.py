"""Query interface for the curated vessel fleet."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logger = logging.getLogger(__name__)

# Curated data ships INSIDE this member as package data (ADR 0001 Phase 2,
# batch 4, #529 — option (i): data travels with the package), at
# ``worldenergydata/vessel_fleet/_data/curated/`` (one level up from this
# module). Resolved package-relative so the no-arg ``FleetRouter()`` runtime
# path works identically from an editable workspace install or the built wheel.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "_data" / "curated"


class FleetRouter:
    """Query interface for the curated vessel fleet data.

    Provides filtering by vessel type, owner, region, status.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
    ) -> None:
        self._store = ParquetStore(base_dir=data_dir or _DEFAULT_DATA_DIR)
        self._drilling_rigs: Optional[list[dict[str, Any]]] = None
        self._construction_vessels: Optional[list[dict[str, Any]]] = None

    def _load_drilling_rigs(self) -> list[dict[str, Any]]:
        if self._drilling_rigs is None:
            self._drilling_rigs = self._store.load("drilling_rigs.parquet")
        return self._drilling_rigs

    def _load_construction_vessels(self) -> list[dict[str, Any]]:
        if self._construction_vessels is None:
            self._construction_vessels = self._store.load(
                "construction_vessels.parquet",
            )
        return self._construction_vessels

    def query_drilling_rigs(
        self,
        *,
        rig_type: Optional[str] = None,
        owner: Optional[str] = None,
        min_water_depth_ft: Optional[float] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Query drilling rigs with optional filters."""
        rigs = self._load_drilling_rigs()
        results = rigs

        if rig_type:
            results = [r for r in results if r.get("RIG_TYPE") == rig_type]
        if owner:
            owner_lower = owner.lower()
            results = [
                r
                for r in results
                if r.get("OWNER") and owner_lower in r["OWNER"].lower()
            ]
        if min_water_depth_ft is not None:
            results = [
                r
                for r in results
                if r.get("WATER_DEPTH_RATING_FT") is not None
                and r["WATER_DEPTH_RATING_FT"] >= min_water_depth_ft
            ]
        if status:
            results = [r for r in results if r.get("STATUS") == status]

        return results

    def query_construction_vessels(
        self,
        *,
        vessel_type: Optional[str] = None,
        owner: Optional[str] = None,
        min_crane_capacity_t: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """Query construction vessels with optional filters."""
        vessels = self._load_construction_vessels()
        results = vessels

        if vessel_type:
            results = [r for r in results if r.get("VESSEL_TYPE") == vessel_type]
        if owner:
            owner_lower = owner.lower()
            results = [
                r
                for r in results
                if r.get("OWNER") and owner_lower in r["OWNER"].lower()
            ]
        if min_crane_capacity_t is not None:
            results = [
                r
                for r in results
                if r.get("MAIN_CRANE_CAPACITY_T") is not None
                and r["MAIN_CRANE_CAPACITY_T"] >= min_crane_capacity_t
            ]

        return results

    def fleet_summary(self) -> dict[str, int]:
        """Return counts by category."""
        return {
            "drilling_rigs": len(self._load_drilling_rigs()),
            "construction_vessels": len(self._load_construction_vessels()),
        }
