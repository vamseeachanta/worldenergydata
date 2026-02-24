"""Standalone runner for EIA weekly feed ingestion.

Used by the cron script (scripts/eia_weekly_sync.sh) for automated
weekly execution. Can also be invoked directly:

    python -m worldenergydata.eia.ingestion_runner
    python -m worldenergydata.eia.ingestion_runner --output-dir ./data/eia

Exit codes:
    0 — all feeds synced successfully
    1 — configuration error (missing EIA_API_KEY)
    2 — one or more feeds failed to sync
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EIA weekly feed ingestion (all feeds)."
    )
    parser.add_argument(
        "--output-dir",
        default="./data/eia",
        help="Directory for JSONL output files (default: ./data/eia)",
    )
    parser.add_argument(
        "--state-dir",
        default=None,
        help="Directory for ingestion state file (default: --output-dir)",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point for the EIA ingestion runner.

    Returns:
        Exit code: 0 on success, 1 on config error, 2 on sync failure.
    """
    args = _parse_args()
    output_dir = Path(args.output_dir)
    state_dir = Path(args.state_dir) if args.state_dir else output_dir

    try:
        from worldenergydata.eia.client import EIAKeyError
        from worldenergydata.eia.ingestion import EIAIngestionSync
    except ImportError as exc:
        logger.error("Import failed: %s", exc)
        return 2

    try:
        sync = EIAIngestionSync(output_dir=output_dir, state_dir=state_dir)
    except EIAKeyError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    try:
        results = sync.run_all()
    except Exception as exc:  # noqa: BLE001
        logger.error("Sync failed: %s", exc, exc_info=True)
        return 2

    for result in results:
        logger.info(
            "Feed=%s  records_written=%d  latest_period=%s",
            result["feed"],
            result["records_written"],
            result.get("latest_period") or "N/A",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
