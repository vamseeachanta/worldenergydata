#!/usr/bin/env python3
"""End-to-end vessel fleet collection pipeline.

Orchestrates all steps in order:
1. Ingest XLS historical data
2. Collect from contractor fleet pages
3. Enrich from maritime registries
4. Enrich from government data
5. Fuse, deduplicate, and validate
6. Export curated Parquet + CSV

Usage:
    python scripts/vessel_fleet/run_full_pipeline.py [--xls-path <path>]
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _run_step(script_name: str, args: list[str] | None = None) -> bool:
    """Run a pipeline step script. Returns True on success."""
    script_path = _SCRIPT_DIR / script_name
    if not script_path.exists():
        logger.warning("Script not found: %s", script_path)
        return False

    cmd = [sys.executable, str(script_path)] + (args or [])
    logger.info("Running: %s", " ".join(cmd))

    result = subprocess.run(cmd, cwd=str(_PROJECT_ROOT))
    if result.returncode != 0:
        logger.error("Step failed: %s (exit %d)", script_name, result.returncode)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Full vessel fleet pipeline")
    parser.add_argument("--xls-path", help="Path to DrillRigs.xls for historical ingest")
    parser.add_argument("--skip-web", action="store_true", help="Skip web collection steps")
    args = parser.parse_args()

    steps_ok = True

    # Step 1: XLS ingest (if path provided)
    if args.xls_path:
        logger.info("=== Step 1: XLS Historical Ingest ===")
        if not _run_step("ingest_xls_historical.py", [args.xls_path]):
            steps_ok = False

    if not args.skip_web:
        # Step 2: Contractor fleet collection
        logger.info("=== Step 2: Contractor Fleet Collection ===")
        _run_step("collect_drilling_fleet.py")
        _run_step("collect_construction_fleet.py")

        # Step 3: Registry enrichment
        logger.info("=== Step 3: Maritime Registry Enrichment ===")
        _run_step("enrich_from_registries.py")

        # Step 4: Government data
        logger.info("=== Step 4: Government Data Enrichment ===")
        _run_step("enrich_from_government.py")

    # Step 5: Fuse and deduplicate
    logger.info("=== Step 5: Fusion & Deduplication ===")
    if not _run_step("fuse_and_deduplicate.py"):
        steps_ok = False

    if steps_ok:
        logger.info("Pipeline completed successfully")
    else:
        logger.warning("Pipeline completed with some failures")

    return 0 if steps_ok else 1


if __name__ == "__main__":
    sys.exit(main())
