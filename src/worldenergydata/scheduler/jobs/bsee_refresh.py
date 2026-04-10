"""BSEE (Bureau of Safety and Environmental Enforcement) data refresh job.

Downloads platform structures, pipeline permits/locations, and deepwater
structures via BSEEWebScraper, extracting CSVs from zips and writing Parquet.
"""

import io
import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.common.data_resolver import DataNotFoundError, get_module_data
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)

BSEE_DATASETS = {
    "platform": {
        "url_key": "platform",
        "output_file": "bsee_platform_structures.parquet",
    },
    "pipeline_permit": {
        "url_key": "pipeline_permit",
        "output_file": "bsee_pipeline_permits.parquet",
    },
    "pipeline_location": {
        "url_key": "pipeline_location",
        "output_file": "bsee_pipeline_locations.parquet",
    },
    "deepwater_structure": {
        "url_key": "deepwater_structure",
        "output_file": "bsee_deepwater_structures.parquet",
    },
}

try:
    _DEFAULT_OUTPUT_DIR = get_module_data("bsee")
except DataNotFoundError:
    _DEFAULT_OUTPUT_DIR = Path("data/modules/bsee")


class BseeRefreshJob(AbstractJob):
    """Refresh BSEE Gulf of Mexico offshore structural and pipeline data."""

    name = "bsee_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Execute BSEE data refresh across all dataset types.

        Downloads each BSEE dataset independently. Partial failures are
        tolerated -- only a complete failure of all datasets returns failure.

        Args:
            config: May contain "output_dir" for Parquet output location.

        Returns:
            JobResult with total records across all successful datasets.
        """
        start = datetime.now()
        output_dir = Path(config.get("output_dir", self.default_output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)

        scraper = BSEEWebScraper()
        total_records = 0
        failed_datasets: list[str] = []

        for dataset_name, info in BSEE_DATASETS.items():
            try:
                records = self._process_dataset(
                    scraper, dataset_name, info, output_dir
                )
                if records is not None:
                    total_records += records
                else:
                    failed_datasets.append(dataset_name)
            except Exception as exc:
                logger.warning(
                    "BSEE %s processing error: %s", dataset_name, exc
                )
                failed_datasets.append(dataset_name)

        if total_records > 0:
            if failed_datasets:
                logger.warning(
                    "BSEE refresh partial: failed datasets=%s",
                    failed_datasets,
                )
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=total_records,
                error_msg=None,
            )

        error_msg = (
            f"All BSEE downloads failed: {', '.join(failed_datasets)}"
        )
        logger.error(error_msg)
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="failure",
            records_updated=0,
            error_msg=error_msg,
        )

    def _process_dataset(
        self,
        scraper: BSEEWebScraper,
        dataset_name: str,
        info: dict,
        output_dir: Path,
    ) -> Optional[int]:
        """Download, extract, and write a single BSEE dataset to Parquet.

        Returns:
            Number of rows written, or None if download failed.
        """
        url = BSEEWebScraper.URLS[info["url_key"]]
        logger.info("BSEE downloading %s from %s", dataset_name, url)

        zip_bytes = scraper.download_zip_to_memory(
            url, data_type=info["url_key"]
        )
        if zip_bytes is None:
            logger.warning("BSEE %s download returned None", dataset_name)
            return None

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_names = [
                n for n in zf.namelist() if n.lower().endswith(".csv")
            ]
            if not csv_names:
                logger.warning(
                    "BSEE %s zip contains no CSV files", dataset_name
                )
                return None
            csv_name = csv_names[0]
            logger.info(
                "BSEE %s extracting %s", dataset_name, csv_name
            )
            df = pd.read_csv(zf.open(csv_name))

        out_path = output_dir / info["output_file"]
        df.to_parquet(out_path, engine="pyarrow", index=False, compression="snappy")
        logger.info(
            "BSEE %s wrote %d rows to %s",
            dataset_name,
            len(df),
            out_path,
        )
        return len(df)
