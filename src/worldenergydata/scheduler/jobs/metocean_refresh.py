"""Metocean data refresh job using Open-Meteo marine forecasts."""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.metocean.clients.open_meteo_client import OpenMeteoClient
from worldenergydata.scheduler.jobs.base import (
    AbstractJob,
    JobResult,
    write_refresh_metadata,
)
from worldenergydata.scheduler.parquet_output import write_parquet

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("metocean")


class MetoceanRefreshJob(AbstractJob):
    """Refresh bounded Open-Meteo marine forecasts for configured locations."""

    name = "metocean_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Fetch Open-Meteo forecasts and write one Parquet file per location."""
        start = datetime.now()
        output_dir = Path(config.get("output_dir", self.default_output_dir))
        locations = config.get("locations") or []
        forecast_days = int(config.get("forecast_days", 1))

        if not locations:
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="skipped",
                records_updated=0,
                error_msg="No metocean locations configured",
            )

        client = OpenMeteoClient()
        total_records = 0
        failures: list[str] = []

        for location in locations:
            name = str(location.get("name") or "location")
            try:
                rows = self._fetch_location(client, location, forecast_days)
                if not rows:
                    failures.append(name)
                    continue
                df = pd.DataFrame(rows)
                write_parquet(df, output_dir, f"open_meteo_{_safe_slug(name)}.parquet")
                total_records += len(rows)
            except Exception as exc:
                logger.warning("Metocean %s fetch failed: %s", name, exc)
                failures.append(name)

        if total_records == 0:
            error_msg = f"All metocean locations failed: {', '.join(failures)}"
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=error_msg,
            )

        write_refresh_metadata("metocean", output_dir, total_records)
        error_msg = None
        if failures:
            error_msg = f"Partial metocean refresh failures: {', '.join(failures)}"

        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="success",
            records_updated=total_records,
            error_msg=error_msg,
        )

    def _fetch_location(
        self,
        client: OpenMeteoClient,
        location: dict[str, Any],
        forecast_days: int,
    ) -> list[dict[str, Any]]:
        latitude = float(location["lat"])
        longitude = float(location["lon"])
        location_name = str(location.get("name") or f"{latitude}_{longitude}")
        result = client.fetch_forecast(
            latitude=latitude,
            longitude=longitude,
            forecast_days=forecast_days,
        )
        if result.had_errors or not result.data:
            return []

        rows: list[dict[str, Any]] = []
        for forecast in result.data:
            row = asdict(forecast)
            row["forecast_time"] = row["forecast_time"].isoformat()
            row["location_name"] = location_name
            row["source"] = result.source.value
            row["fetch_time"] = result.fetch_time.isoformat()
            rows.append(row)
        return rows


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "location"
