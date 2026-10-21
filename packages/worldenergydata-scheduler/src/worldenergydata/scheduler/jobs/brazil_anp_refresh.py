"""Brazilian ANP production data refresh job."""

from __future__ import annotations

import logging
import zipfile
from datetime import datetime
from http import HTTPStatus
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

        try:
            output_dir = Path(config["output_dir"])
            year, month = _resolve_year_month(config)
        except (TypeError, ValueError) as exc:
            # Only configuration conversion errors are deterministic here;
            # an unknown processing ValueError below retains retry behavior.
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=str(exc),
                retryable=False,
            )
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
                retryable=not _is_deterministic_failure(exc),
            )


def _is_deterministic_failure(exc: Exception) -> bool:
    """Classify only known endpoint and static archive contract failures."""
    from requests.exceptions import HTTPError

    # ANPClient.load_cached re-parses the same bytes, so a bad ZIP needs repair.
    if isinstance(exc, zipfile.BadZipFile):
        return True
    # RFC 9110 (2022), section 15.5.5: Not Found. A missing configured
    # endpoint stops this run; this does not assert permanent unavailability.
    return (
        isinstance(exc, HTTPError)
        and exc.response is not None
        and exc.response.status_code == HTTPStatus.NOT_FOUND
    )


def _resolve_year_month(config: dict) -> tuple[int, int]:
    explicit_date = any(key in config for key in ("year", "month", "semester"))
    if "year" in config and "month" in config:
        year, month = int(config["year"]), int(config["month"])
        # ANPClient._build_month_url defines the inclusive 1..12 contract.
        # Validate here so a configuration error never enters download retry.
        if not 1 <= month <= 12:
            raise ValueError("month must be in 1..12")
        return year, month

    if "year" in config and "semester" in config:
        semester = int(config["semester"])
        if semester not in (1, 2):
            raise ValueError("semester must be 1 or 2")
        return int(config["year"]), 6 if semester == 1 else 12

    if explicit_date:
        raise ValueError("explicit date requires year and either month or semester")

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
