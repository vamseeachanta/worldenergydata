"""SODIR (Norwegian Offshore Directorate) data refresh job."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict

import pandas as pd

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.sodir.api_client import SodirAPIClient
from worldenergydata.sodir.endpoints import SODIR_ENDPOINTS
from worldenergydata.sodir.errors import SodirAPIError

logger = logging.getLogger(__name__)

# Datasets fetched by the scheduler job — maps endpoint key to output filename
SODIR_DATASETS: Dict[str, str] = {
    "blocks": "sodir_blocks.parquet",
    "wellbores": "sodir_wellbores.parquet",
    "fields": "sodir_fields.parquet",
}

_DEFAULT_OUTPUT_DIR = get_module_data_safe("sodir")


class SodirRefreshJob(AbstractJob):
    """Refresh SODIR Norwegian Continental Shelf production data.

    Fetches blocks, wellbores, and fields from the SODIR factmaps API
    and writes each dataset as a Parquet file.  Handles partial failures
    gracefully — if one endpoint fails the remaining endpoints are still
    fetched and persisted.
    """

    name = "sodir_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Execute SODIR data refresh.

        Args:
            config: Configuration dictionary.  Recognised keys:
                - base_url: SODIR API base URL (default https://factmaps.sodir.no)
                - output_dir: Directory for Parquet output (default data/modules/sodir)

        Returns:
            JobResult indicating success or failure.
        """
        start = datetime.now()
        base_url = config.get("base_url", "https://factmaps.sodir.no")
        output_dir = Path(config.get("output_dir", self.default_output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        client = SodirAPIClient(base_url=base_url)

        total_records = 0
        failures = []

        for dataset_key, output_file in SODIR_DATASETS.items():
            try:
                endpoint_cfg = SODIR_ENDPOINTS[dataset_key]
                endpoint_path = endpoint_cfg["endpoint"]
                table_id = endpoint_cfg["table_id"]

                response = client.get(
                    endpoint_path, params={"table": table_id}
                )
                rows = response.get("data", [])

                if rows:
                    df = pd.DataFrame(rows)
                    df.to_parquet(
                        output_dir / output_file,
                        engine="pyarrow",
                        index=False,
                        compression="snappy",
                    )
                    total_records += len(rows)
                    logger.info(
                        "SODIR %s: wrote %d records to %s",
                        dataset_key,
                        len(rows),
                        output_file,
                    )
                else:
                    logger.warning("SODIR %s: endpoint returned no data", dataset_key)

            except (SodirAPIError, Exception) as exc:
                logger.warning("SODIR %s fetch failed: %s", dataset_key, exc)
                failures.append(dataset_key)

        all_failed = len(failures) == len(SODIR_DATASETS)

        if all_failed:
            error_msg = f"All SODIR endpoints failed: {', '.join(failures)}"
            logger.error(error_msg)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=error_msg,
            )

        if failures:
            logger.warning(
                "SODIR refresh partial: %d/%d endpoints failed (%s)",
                len(failures),
                len(SODIR_DATASETS),
                ", ".join(failures),
            )

        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="success",
            records_updated=total_records,
            error_msg=None,
        )
