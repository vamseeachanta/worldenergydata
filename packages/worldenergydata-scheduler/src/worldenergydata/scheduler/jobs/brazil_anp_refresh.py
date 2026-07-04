"""Brazilian ANP production data refresh job."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from worldenergydata.brazil_anp.production.anp_client import ANPClient
from worldenergydata.brazil_anp.production.well_production import WellProductionLoader
from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import (
    AbstractJob,
    JobResult,
    write_refresh_metadata,
)
from worldenergydata.scheduler.parquet_output import write_parquet

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("brazil_anp")


class BrazilAnpRefreshJob(AbstractJob):
    """Refresh one ANP production month into raw and normalized snapshots."""

    name = "brazil_anp_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Download a configured or latest-completed ANP production month."""
        start = datetime.now()
        if "output_dir" not in config:
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="skipped",
                records_updated=0,
                error_msg="Brazil ANP live refresh requires an explicit output_dir",
            )

        output_dir = Path(config["output_dir"])
        year, month = _resolve_year_month(config)
        force_refresh = bool(config.get("force_refresh", False))

        try:
            client = ANPClient(cache_dir=str(output_dir / "raw"))
            raw_df = client.download_month(
                year=year,
                month=month,
                force_refresh=force_refresh,
            )
            raw_records = len(raw_df)
            raw_dir = output_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_df.to_parquet(
                raw_dir / f"anp_production_{year}_{month:02d}.parquet",
                engine="pyarrow",
                index=False,
                compression="snappy",
            )

            normalized = WellProductionLoader().load(raw_df)
            write_parquet(
                normalized,
                output_dir,
                f"anp_production_{year}_{month:02d}.parquet",
            )
            write_refresh_metadata("brazil_anp", output_dir, raw_records)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=raw_records,
                error_msg=None,
            )
        except Exception as exc:
            logger.warning("Brazil ANP refresh failed: %s", exc)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=str(exc),
            )


def _resolve_year_month(config: dict) -> tuple[int, int]:
    if "year" in config and "month" in config:
        return int(config["year"]), int(config["month"])

    if "year" in config and "semester" in config:
        semester = int(config["semester"])
        if semester not in (1, 2):
            raise ValueError("semester must be 1 or 2")
        return int(config["year"]), 6 if semester == 1 else 12

    now = datetime.now()
    month = now.month - 2
    year = now.year
    if month <= 0:
        month += 12
        year -= 1
    return year, month


def _resolve_year_semester(config: dict) -> tuple[int, int]:
    """Legacy helper retained for import compatibility."""
    year, month = _resolve_year_month(config)
    return year, 1 if month <= 6 else 2
