"""BSEE (Bureau of Safety and Environmental Enforcement) data refresh job.

Downloads platform structures, pipeline permits/locations, and deepwater
structures via BSEEWebScraper, extracting the primary table from each
raw-data archive and writing Parquet.

The dataset catalog is externalized to ``config/bsee.yml`` (knowledge
from closed issues #9 / #11 / #12); built-in defaults below mirror it
so the job still runs from an installed package without the repo
checkout.  Payload classification and archive extraction live in
``worldenergydata.bsee.data.refresh.payload`` (issue #267): BSEE serves
HTTP 200 + HTML for stale URLs, and healthy archives contain quoted-CSV
``.txt`` members behind a directory entry rather than a ``.csv`` in the
first slot.

Per-dataset failures are classified deterministic vs transient (issue
#460) so the scheduler's retry layer can skip pointless backoff.
"""

import logging
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from worldenergydata.bsee.data.refresh.payload import (
    DatasetFailure,
    FailureClass,
    PayloadKind,
    classify_payload,
    extract_primary_table,
)
from worldenergydata.bsee.data.scrapers.bsee_web import BSEEWebScraper
from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import (
    AbstractJob,
    JobResult,
    write_refresh_metadata,
)

logger = logging.getLogger(__name__)

#: Built-in defaults mirroring config/bsee.yml ``scheduler_datasets``.
#: Keep in sync with the YAML catalog (drift-guarded by unit tests).
BSEE_DATASETS = {
    "platform": {
        "url_key": "platform",
        "output_file": "bsee_platform_structures.parquet",
        "primary_member_patterns": ["mv_platstruc_structures.txt"],
    },
    "pipeline_permit": {
        "url_key": "pipeline_permit",
        "output_file": "bsee_pipeline_permits.parquet",
        "primary_member_patterns": ["mv_pipeperm_applications.txt"],
    },
    "pipeline_location": {
        "url_key": "pipeline_location",
        "output_file": "bsee_pipeline_locations.parquet",
        "primary_member_patterns": ["mv_pipelinelocation*.txt"],
    },
    "deepwater_structure": {
        "url_key": "deepwater_structure",
        "output_file": "bsee_deepwater_structures.parquet",
        "primary_member_patterns": ["mv_perm_platforms.txt"],
    },
}

#: Repo-level YAML catalog (issue #9 knowledge as reviewable config).
DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[4] / "config" / "bsee.yml"

_DEFAULT_OUTPUT_DIR = get_module_data_safe("bsee")


def load_dataset_catalog(catalog_path: Optional[Path] = None) -> dict:
    """Load the scheduler dataset catalog from ``config/bsee.yml``.

    Falls back to the built-in ``BSEE_DATASETS`` defaults when the YAML
    catalog is absent (e.g. installed package without repo checkout) or
    unreadable -- the refresh must not hard-fail on missing config.
    """
    path = catalog_path or DEFAULT_CATALOG_PATH
    try:
        raw = yaml.safe_load(path.read_text())
        datasets = raw["scheduler_datasets"]
        if not isinstance(datasets, dict) or not datasets:
            raise ValueError("scheduler_datasets empty or not a mapping")
        return datasets
    except Exception as exc:
        logger.warning(
            "BSEE catalog %s unusable (%s); using built-in defaults", path, exc
        )
        return BSEE_DATASETS


class BseeRefreshJob(AbstractJob):
    """Refresh BSEE Gulf of Mexico offshore structural and pipeline data."""

    name = "bsee_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Execute BSEE data refresh across all cataloged dataset types.

        Downloads each BSEE dataset independently. Partial failures are
        tolerated -- only a complete failure of all datasets returns
        failure, with each dataset's failure classified deterministic
        vs transient (issue #460).

        Args:
            config: Must contain "output_dir"; may contain
                "catalog_path" to override the YAML dataset catalog.

        Returns:
            JobResult with total records across all successful datasets.
        """
        start = datetime.now()
        if "output_dir" not in config:
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="skipped",
                records_updated=0,
                error_msg="BSEE live refresh requires an explicit output_dir",
            )

        output_dir = Path(config["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        catalog_path = config.get("catalog_path")
        datasets = load_dataset_catalog(Path(catalog_path) if catalog_path else None)

        scraper = BSEEWebScraper()
        total_records = 0
        failures: list[DatasetFailure] = []

        for dataset_name, info in datasets.items():
            try:
                outcome = self._process_dataset(scraper, dataset_name, info, output_dir)
            except Exception as exc:  # e.g. parquet write / disk errors
                outcome = DatasetFailure(
                    dataset_name,
                    f"unexpected error: {exc}",
                    FailureClass.TRANSIENT,
                )
            if isinstance(outcome, DatasetFailure):
                logger.warning("BSEE %s", outcome.summary())
                failures.append(outcome)
            else:
                total_records += outcome

        if total_records > 0:
            error_msg = None
            if failures:
                error_msg = "Partial BSEE refresh; failed: " + "; ".join(
                    f.summary() for f in failures
                )
                logger.warning(error_msg)
            write_refresh_metadata("bsee", output_dir, total_records)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=total_records,
                error_msg=error_msg,
            )

        error_msg = "All BSEE downloads failed: " + "; ".join(
            f.summary() for f in failures
        )
        if failures and all(
            f.failure_class is FailureClass.DETERMINISTIC for f in failures
        ):
            error_msg = "[deterministic] " + error_msg
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
    ):
        """Download, validate, extract, and write one BSEE dataset.

        Returns:
            Number of rows written (int) on success, or a classified
            ``DatasetFailure`` describing why the dataset was skipped.
        """
        url_key = info["url_key"]
        url = info.get("url") or BSEEWebScraper.URLS[url_key]
        logger.info("BSEE downloading %s from %s", dataset_name, url)

        try:
            payload = scraper.download_zip_to_memory(url, data_type=url_key)
        except Exception as exc:
            return DatasetFailure(
                dataset_name, f"download error: {exc}", FailureClass.TRANSIENT
            )
        if payload is None:
            # Scraper exhausted its own retries (timeouts / HTTP errors).
            return DatasetFailure(
                dataset_name,
                "download failed after retries",
                FailureClass.TRANSIENT,
            )

        kind = classify_payload(payload)
        if kind is not PayloadKind.ZIP:
            # HTTP 200 + HTML means the URL went stale upstream; retrying
            # in-process cannot succeed (issues #267 / #460).
            return DatasetFailure(
                dataset_name,
                f"expected zip, got {kind.value} payload "
                f"({len(payload)} bytes) -- URL likely stale, check "
                "https://www.data.bsee.gov/Main/RawData.aspx",
                FailureClass.DETERMINISTIC,
            )

        try:
            df, member_name = extract_primary_table(
                bytes(payload), info.get("primary_member_patterns")
            )
        except LookupError as exc:
            return DatasetFailure(dataset_name, str(exc), FailureClass.DETERMINISTIC)
        except zipfile.BadZipFile as exc:
            return DatasetFailure(
                dataset_name,
                f"corrupt zip payload: {exc}",
                FailureClass.TRANSIENT,
            )
        except Exception as exc:
            return DatasetFailure(
                dataset_name,
                f"extraction error: {exc}",
                FailureClass.DETERMINISTIC,
            )

        if df.empty:
            return DatasetFailure(
                dataset_name,
                f"primary member {member_name} parsed to 0 rows",
                FailureClass.DETERMINISTIC,
            )

        out_path = output_dir / info["output_file"]
        df.to_parquet(out_path, engine="pyarrow", index=False, compression="snappy")
        logger.info(
            "BSEE %s wrote %d rows from %s to %s",
            dataset_name,
            len(df),
            member_name,
            out_path,
        )
        return len(df)
