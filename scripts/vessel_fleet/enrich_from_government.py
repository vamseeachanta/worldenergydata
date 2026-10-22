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

from worldenergydata.vessel_fleet.collectors.baker_hughes_collector import (
    BakerHughesCollector,
)
from worldenergydata.vessel_fleet.collectors.boem_collector import BOEMCollector
from worldenergydata.vessel_fleet.storage.parquet import ParquetStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_DATA_DIR = _PROJECT_ROOT / "data" / "modules" / "vessel_fleet" / "raw"


def export_baker_hughes(collector, store) -> dict[str, str]:
    """Attempt both independent workbook paths and return per-source states.

    Contract: #1337 (2026), knowledge pack BH-map-1. A download/parse
    exception is download_failed, a valid empty frame is empty_result, and
    a write exception or absent output file is missing_export. Only an
    existing output file is exported; file existence does not qualify bytes.
    Error details are not logged because third-party errors can expose URLs.
    """
    outcomes = {}
    for name, download, filename in (
        ("na", collector.download_na_rig_count, "na_rig_count.parquet"),
        (
            "international",
            collector.download_international_rig_count,
            "international_rig_count.parquet",
        ),
    ):
        try:
            frame = download()
        except (RuntimeError, OSError, ValueError, ImportError):
            outcomes[name] = "download_failed"
            continue
        if frame.empty:
            outcomes[name] = "empty_result"
            continue
        try:
            output = store.save(frame.to_dict(orient="records"), filename=filename)
            outcomes[name] = (
                "exported"
                if output is not None and Path(output).is_file()
                else "missing_export"
            )
        except (RuntimeError, OSError, ValueError, ImportError):
            outcomes[name] = "missing_export"
    for name, status in outcomes.items():
        logger.info("Baker Hughes %s: %s", name, status)
    return outcomes


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
    store = ParquetStore(base_dir=_DATA_DIR / "baker_hughes")
    outcomes = export_baker_hughes(bh, store)

    logger.info("Government data enrichment complete")
    return 0 if all(status == "exported" for status in outcomes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
