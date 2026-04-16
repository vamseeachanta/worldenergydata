"""EIA (US Energy Information Administration) data refresh job.

Wires the scheduler adapter to EIAIngestionSync for incremental JSONL
ingestion, then produces Parquet snapshots of each feed output.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.eia.ingestion import EIAIngestionSync
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.parquet_output import write_parquet

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("eia")


class EiaUsRefreshJob(AbstractJob):
    """Refresh US EIA energy production and consumption data.

    Uses EIAIngestionSync to fetch incremental JSONL data, then converts
    each JSONL output to a Parquet snapshot via the shared write_parquet
    utility.
    """

    name = "eia_us_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Execute EIA US data refresh.

        Args:
            config: May contain:
                - "api_key": EIA API key (falls back to EIA_API_KEY env var)
                - "output_dir": Output directory path (defaults to "data/modules/eia")

        Returns:
            JobResult indicating success or failure.
        """
        start = datetime.now()
        try:
            api_key = config.get("api_key") or os.environ.get("EIA_API_KEY")
            output_dir = Path(config.get("output_dir", self.default_output_dir))

            sync = EIAIngestionSync(api_key=api_key, output_dir=output_dir)
            results = sync.run_all()

            total_records = sum(r.get("records_written", 0) for r in results)

            # Convert JSONL files to Parquet snapshots
            self._write_parquet_snapshots(sync.output_dir)

            logger.info(
                "EIA US data refresh completed: %d records across %d feeds.",
                total_records,
                len(results),
            )
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=total_records,
                error_msg=None,
            )
        except Exception as exc:
            logger.error("EIA US refresh failed: %s", exc)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=str(exc),
            )

    def _write_parquet_snapshots(self, output_dir: Path) -> None:
        """Convert JSONL files in output_dir to Parquet snapshots.

        Only processes files matching eia_*.jsonl that are non-empty.

        Args:
            output_dir: Directory containing JSONL output files.
        """
        if not output_dir.exists():
            return

        for jsonl_path in sorted(output_dir.glob("eia_*.jsonl")):
            if jsonl_path.stat().st_size == 0:
                continue
            try:
                df = pd.read_json(jsonl_path, lines=True)
                if len(df) > 0:
                    parquet_name = jsonl_path.stem + ".parquet"
                    write_parquet(df, output_dir, parquet_name)
                    logger.info("Wrote Parquet snapshot: %s", parquet_name)
            except Exception as exc:
                logger.warning(
                    "Failed to convert %s to Parquet: %s", jsonl_path.name, exc
                )
