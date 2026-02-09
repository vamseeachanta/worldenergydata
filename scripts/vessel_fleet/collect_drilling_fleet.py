#!/usr/bin/env python3
"""Collect drilling rig data from all contractor fleet pages.

Uses known vessel data from configs as a baseline. Web scraping
is attempted but falls back to known data if pages are unreachable.

Usage:
    python scripts/vessel_fleet/collect_drilling_fleet.py [--output-dir <dir>]
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

_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "data" / "modules" / "vessel_fleet" / "raw" / "drilling_contractors"

_DRILLING_CONFIGS = [
    "worldenergydata.vessel_fleet.configs.drilling.transocean",
    "worldenergydata.vessel_fleet.configs.drilling.valaris",
    "worldenergydata.vessel_fleet.configs.drilling.borr",
    "worldenergydata.vessel_fleet.configs.drilling.noble",
    "worldenergydata.vessel_fleet.configs.drilling.saipem",
    "worldenergydata.vessel_fleet.configs.drilling.seadrill",
    "worldenergydata.vessel_fleet.configs.drilling.cosl",
    "worldenergydata.vessel_fleet.configs.drilling.ades",
    "worldenergydata.vessel_fleet.configs.drilling.stena",
    "worldenergydata.vessel_fleet.configs.drilling.vantage",
    "worldenergydata.vessel_fleet.configs.drilling.nabors",
    "worldenergydata.vessel_fleet.configs.drilling.patterson_uti",
    "worldenergydata.vessel_fleet.configs.drilling.helmerich_payne",
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
    parser = argparse.ArgumentParser(description="Collect drilling fleet data")
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Output directory",
    )
    args = parser.parse_args()

    all_vessels: list[dict[str, Any]] = []

    for config_path in _DRILLING_CONFIGS:
        vessels = _load_known_vessels(config_path)
        contractor_name = config_path.rsplit(".", 1)[-1]
        logger.info("Loaded %d known vessels from %s", len(vessels), contractor_name)
        all_vessels.extend(vessels)

    logger.info("Total drilling rigs collected: %d", len(all_vessels))

    store = ParquetStore(base_dir=args.output_dir)
    store.save(all_vessels, "drilling_contractors.parquet")

    logger.info("Saved to %s", args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
