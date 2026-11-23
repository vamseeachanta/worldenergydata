#!/usr/bin/env python3
"""Enrich vessel fleet data with government sources (BOEM, Baker Hughes).

Usage:
    python scripts/vessel_fleet/enrich_from_government.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from worldenergydata.vessel_fleet.collectors.boem_collector import BOEMCollector
from worldenergydata.vessel_fleet.collectors.baker_hughes_collector import BakerHughesCollector
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DATA_DIR = _PROJECT_ROOT / "data" / "modules" / "vessel_fleet" / "raw"


def main() -> int:
    # BOEM platform data
    logger.info("Downloading BOEM platform structures...")
    boem = BOEMCollector()
    try:
        platforms_df = boem.download_platform_structures()
        if not platforms_df.empty:
            store = ParquetStore(base_dir=_DATA_DIR / "boem")
            store.save(
                platforms_df.to_dict(orient="records"),
                filename="platform_structures.parquet",
            )
            logger.info("Saved %d BOEM platform records", len(platforms_df))
    except Exception as exc:
        logger.warning("BOEM collection failed: %s", exc)

    # Baker Hughes rig count
    logger.info("Downloading Baker Hughes rig counts...")
    bh = BakerHughesCollector()
    try:
        na_df = bh.download_na_rig_count()
        if not na_df.empty:
            store = ParquetStore(base_dir=_DATA_DIR / "baker_hughes")
            store.save(
                na_df.to_dict(orient="records"),
                filename="na_rig_count.parquet",
            )
            logger.info("Saved %d NA rig count records", len(na_df))
    except Exception as exc:
        logger.warning("Baker Hughes collection failed: %s", exc)

    try:
        intl_df = bh.download_international_rig_count()
        if not intl_df.empty:
            store = ParquetStore(base_dir=_DATA_DIR / "baker_hughes")
            store.save(
                intl_df.to_dict(orient="records"),
                filename="international_rig_count.parquet",
            )
            logger.info("Saved %d international rig count records", len(intl_df))
    except Exception as exc:
        logger.warning("Baker Hughes international collection failed: %s", exc)

    logger.info("Government data enrichment complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
