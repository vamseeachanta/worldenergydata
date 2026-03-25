#!/usr/bin/env python3
"""Collect drilling rig data from all contractor fleet pages.

Multi-source fallback per operator:
  1. Live web scrape via FleetPageCollector (if --try-web)
  2. Pre-collected Puppeteer scrape JSON (if available in --scrape-dir)
  3. KNOWN_VESSELS from config module (always available)

The best source (most records) wins per operator.

Usage:
    python scripts/vessel_fleet/collect_drilling_fleet.py [--output-dir <dir>] [--try-web]
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

from worldenergydata.vessel_fleet.collectors.fleet_page_collector import (
    ContractorConfig,
    FleetPageCollector,
)
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = (
    _PROJECT_ROOT / "data" / "modules" / "vessel_fleet" / "raw" / "drilling_contractors"
)
_DEFAULT_SCRAPE_DIR = (
    _PROJECT_ROOT / "data" / "modules" / "vessel_fleet" / "raw" / "contractor_scrape"
)

_DRILLING_CONFIGS = [
    "worldenergydata.vessel_fleet.config.drilling.transocean",
    "worldenergydata.vessel_fleet.config.drilling.valaris",
    "worldenergydata.vessel_fleet.config.drilling.borr",
    "worldenergydata.vessel_fleet.config.drilling.noble",
    "worldenergydata.vessel_fleet.config.drilling.saipem",
    "worldenergydata.vessel_fleet.config.drilling.seadrill",
    "worldenergydata.vessel_fleet.config.drilling.cosl",
    "worldenergydata.vessel_fleet.config.drilling.ades",
    "worldenergydata.vessel_fleet.config.drilling.stena",
    "worldenergydata.vessel_fleet.config.drilling.vantage",
    "worldenergydata.vessel_fleet.config.drilling.nabors",
    "worldenergydata.vessel_fleet.config.drilling.patterson_uti",
    "worldenergydata.vessel_fleet.config.drilling.helmerich_payne",
]

# Operators with pre-collected Puppeteer scrape JSON
_SCRAPE_PARSERS: dict[str, str] = {
    "noble": "parse_noble_scrape",
    "seadrill": "parse_seadrill_scrape",
}


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


def _collect_from_web(config: ContractorConfig) -> list[dict[str, Any]]:
    """Attempt live web scrape via FleetPageCollector."""
    try:
        collector = FleetPageCollector(config)
        vessels = collector.collect()
        if vessels:
            logger.info(
                "  Web scrape: %d vessels from %s", len(vessels), config.fleet_url
            )
        return vessels
    except Exception as exc:
        logger.info("  Web scrape failed for %s: %s", config.name, exc)
        return []


def _collect_from_scrape_json(
    contractor_name: str,
    scrape_dir: Path,
) -> list[dict[str, Any]]:
    """Parse pre-collected Puppeteer scrape JSON if available."""
    parser_func_name = _SCRAPE_PARSERS.get(contractor_name)
    if not parser_func_name:
        return []

    json_path = scrape_dir / f"{contractor_name}.json"
    if not json_path.exists():
        return []

    try:
        from worldenergydata.vessel_fleet.collectors.scrape_parser import (
            parse_noble_scrape,
            parse_seadrill_scrape,
        )

        parsers = {
            "parse_noble_scrape": parse_noble_scrape,
            "parse_seadrill_scrape": parse_seadrill_scrape,
        }
        parse_fn = parsers.get(parser_func_name)
        if parse_fn is None:
            return []

        records = parse_fn(json_path)
        if records:
            logger.info(
                "  Scrape JSON: %d vessels from %s", len(records), json_path.name
            )
        return records
    except Exception as exc:
        logger.info("  Scrape JSON parse failed for %s: %s", contractor_name, exc)
        return []


def collect_operator_fleet(
    config_path: str,
    scrape_dir: Path,
    try_web: bool = False,
) -> list[dict[str, Any]]:
    """Collect fleet data for a single operator using fallback chain.

    Returns the source with the most records:
      1. Live web scrape (if try_web=True)
      2. Pre-collected scrape JSON (if available)
      3. KNOWN_VESSELS from config
    """
    contractor_name = config_path.rsplit(".", 1)[-1]

    # Load the config module
    try:
        mod = importlib.import_module(config_path)
        config = getattr(mod, "CONFIG", None)
    except Exception:
        config = None

    candidates: list[tuple[str, list[dict[str, Any]]]] = []

    # Source 1: Live web scrape
    if try_web and config:
        web_vessels = _collect_from_web(config)
        if web_vessels:
            candidates.append(("web", web_vessels))

    # Source 2: Pre-collected scrape JSON
    scrape_vessels = _collect_from_scrape_json(contractor_name, scrape_dir)
    if scrape_vessels:
        candidates.append(("scrape_json", scrape_vessels))

    # Source 3: KNOWN_VESSELS (always available)
    known_vessels = _load_known_vessels(config_path)
    if known_vessels:
        candidates.append(("known_vessels", known_vessels))

    if not candidates:
        logger.warning("  No data for %s from any source", contractor_name)
        return []

    # Pick the source with the most records
    best_source, best_records = max(candidates, key=lambda x: len(x[1]))
    logger.info(
        "  Selected: %s (%d records) for %s",
        best_source, len(best_records), contractor_name,
    )
    return best_records


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Collect drilling fleet data")
    parser.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Output directory",
    )
    parser.add_argument(
        "--scrape-dir",
        default=str(_DEFAULT_SCRAPE_DIR),
        help="Directory with pre-collected scrape JSON files",
    )
    parser.add_argument(
        "--try-web",
        action="store_true",
        default=False,
        help="Attempt live web scraping (slow, may be blocked)",
    )
    args = parser.parse_args()

    scrape_dir = Path(args.scrape_dir)
    all_vessels: list[dict[str, Any]] = []

    for config_path in _DRILLING_CONFIGS:
        contractor_name = config_path.rsplit(".", 1)[-1]
        logger.info("Collecting %s ...", contractor_name)
        vessels = collect_operator_fleet(
            config_path=config_path,
            scrape_dir=scrape_dir,
            try_web=args.try_web,
        )
        logger.info("  %s: %d vessels", contractor_name, len(vessels))
        all_vessels.extend(vessels)

    logger.info("Total drilling rigs collected: %d", len(all_vessels))

    store = ParquetStore(base_dir=args.output_dir)
    store.save(all_vessels, "drilling_contractors.parquet")

    logger.info("Saved to %s", args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
