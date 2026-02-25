#!/usr/bin/env python3
"""Collect construction vessel data from all contractor fleet pages.

Usage:
    python scripts/vessel_fleet/collect_construction_fleet.py [--output-dir <dir>]
"""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data" / "modules" / "vessel_fleet" / "raw" / "construction_contractors"

_CONSTRUCTION_CONFIGS = [
    "worldenergydata.vessel_fleet.config.construction.heerema",
    "worldenergydata.vessel_fleet.config.construction.allseas",
    "worldenergydata.vessel_fleet.config.construction.saipem_vessels",
    "worldenergydata.vessel_fleet.config.construction.subsea7",
    "worldenergydata.vessel_fleet.config.construction.boskalis",
    "worldenergydata.vessel_fleet.config.construction.deme",
    "worldenergydata.vessel_fleet.config.construction.mcdermott",
    "worldenergydata.vessel_fleet.config.construction.van_oord",
    "worldenergydata.vessel_fleet.config.construction.eneti",
    "worldenergydata.vessel_fleet.config.construction.oht",
]


def _load_known_vessels(module_path: str) -> list[dict[str, Any]]:
    """Load known vessels from a config module."""
    try:
        mod = importlib.import_module(module_path)
        config = getattr(mod, "CONFIG", None)
        known = getattr(mod, "KNOWN_VESSELS", [])
        if config and known:
            for vessel in known:
                vessel.setdefault("OWNER", config.owner)
                vessel.setdefault("VESSEL_CATEGORY", config.vessel_category)
                vessel.setdefault("DATA_SOURCE", "contractor_fleet_page")
                vessel.setdefault("DATA_SOURCE_URL", config.fleet_url)
        return known
    except Exception as exc:
        logger.warning("Failed to load config %s: %s", module_path, exc)
        return []


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Collect construction fleet data")
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Output directory",
    )
    args = parser.parse_args()

    all_vessels: list[dict[str, Any]] = []

    for config_path in _CONSTRUCTION_CONFIGS:
        vessels = _load_known_vessels(config_path)
        contractor_name = config_path.rsplit(".", 1)[-1]
        logger.info("Loaded %d known vessels from %s", len(vessels), contractor_name)
        all_vessels.extend(vessels)

    logger.info("Total construction vessels collected: %d", len(all_vessels))

    store = ParquetStore(base_dir=args.output_dir)
    store.save(all_vessels, "construction_contractors.parquet")

    logger.info("Saved to %s", args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
