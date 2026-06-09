"""UK Continental Shelf (UKCS) data refresh job."""

import logging
from datetime import datetime
from pathlib import Path

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import (
    AbstractJob,
    JobResult,
    write_refresh_metadata,
)
from worldenergydata.scheduler.parquet_output import write_parquet
from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader
from worldenergydata.ukcs.production.nsta_client import NSTAClient

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("ukcs")
_DEFAULT_DATASET = "monthly"


class UkcsRefreshJob(AbstractJob):
    """Refresh one NSTA UKCS production dataset into raw and normalized snapshots."""

    name = "ukcs_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Download a configured NSTA production year/dataset."""
        start = datetime.now()
        if "output_dir" not in config:
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="skipped",
                records_updated=0,
                error_msg="UKCS live refresh requires an explicit output_dir",
            )

        output_dir = Path(config["output_dir"])
        year = int(config.get("year", datetime.now().year))
        dataset = str(config.get("dataset", _DEFAULT_DATASET))
        force_refresh = bool(config.get("force_refresh", False))
        max_records = int(config["max_records"]) if "max_records" in config else None

        try:
            client_kwargs = {"cache_dir": str(output_dir / "raw")}
            download_url = config.get("download_url") or config.get("base_url")
            if download_url:
                client_kwargs["base_url"] = str(download_url)
            client = NSTAClient(**client_kwargs)
            raw_df = client.download(
                year=year,
                dataset=dataset,
                force_refresh=force_refresh,
                max_records=max_records,
            )
            if max_records is not None:
                raw_df = raw_df.head(max_records)
            raw_records = len(raw_df)
            raw_dir = output_dir / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            raw_df.to_parquet(
                raw_dir / f"nsta_production_{year}_{dataset}.parquet",
                engine="pyarrow",
                index=False,
                compression="snappy",
            )

            normalized = UKCSFieldProductionLoader().load(raw_df)
            write_parquet(
                normalized,
                output_dir,
                f"ukcs_production_{year}_{dataset}.parquet",
            )
            write_refresh_metadata("ukcs", output_dir, raw_records)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=raw_records,
                error_msg=None,
            )
        except Exception as exc:
            logger.warning("UKCS refresh failed: %s", exc)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=str(exc),
            )
