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
#460). Transient failures are retried in-job (bounded); when all
remaining failures are deterministic the JobResult is marked
``retryable=False`` so the scheduler's retry layer skips backoff.
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

SCRAPER_URLS = dict(BSEEWebScraper.URLS)

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

#: Catalog URLs may only point at the official BSEE data portal.
ALLOWED_URL_PREFIX = "https://www.data.bsee.gov/"

#: Bounded in-job attempts per dataset when a failure is transient.
TRANSIENT_DATASET_ATTEMPTS = 2

_DEFAULT_OUTPUT_DIR = get_module_data_safe("bsee")


def validate_dataset_entry(name: str, info: dict) -> None:
    """Validate one catalog entry before it can drive downloads/writes.

    The catalog path is runtime-overridable config, so entries are an
    injection surface: a malformed ``url`` could fetch an arbitrary
    host and a relative ``output_file`` like ``../escape.parquet``
    could write outside the output directory.

    Raises:
        ValueError: With a clear message naming the dataset and field.
    """
    if not isinstance(info, dict):
        raise ValueError(f"BSEE catalog entry '{name}' must be a mapping")

    url_key = info.get("url_key")
    if url_key not in SCRAPER_URLS:
        raise ValueError(
            f"BSEE catalog entry '{name}': url_key {url_key!r} is not a "
            f"known BSEEWebScraper URL key {sorted(SCRAPER_URLS)}"
        )

    url = info.get("url")
    if url is not None and not str(url).startswith(ALLOWED_URL_PREFIX):
        raise ValueError(
            f"BSEE catalog entry '{name}': url {url!r} must be HTTPS under "
            f"{ALLOWED_URL_PREFIX}"
        )

    patterns = info.get("primary_member_patterns")
    if (
        not isinstance(patterns, list)
        or not patterns
        or not all(isinstance(p, str) and p.strip() for p in patterns)
    ):
        raise ValueError(
            f"BSEE catalog entry '{name}': primary_member_patterns must be "
            "a non-empty list of non-empty glob strings"
        )

    output_file = info.get("output_file")
    if (
        not isinstance(output_file, str)
        or output_file != Path(output_file).name
        or not output_file.endswith(".parquet")
    ):
        raise ValueError(
            f"BSEE catalog entry '{name}': output_file {output_file!r} must "
            "be a bare *.parquet filename (no path separators)"
        )


def validate_dataset_catalog(datasets: dict) -> None:
    """Validate every catalog entry; raise ValueError on the first bad one."""
    for name, info in datasets.items():
        validate_dataset_entry(name, info)


def load_dataset_catalog(catalog_path: Optional[Path] = None) -> dict:
    """Load and validate the scheduler dataset catalog from ``config/bsee.yml``.

    Falls back to the built-in ``BSEE_DATASETS`` defaults when the YAML
    catalog is absent (e.g. installed package without repo checkout) or
    unreadable -- the refresh must not hard-fail on missing config.

    A catalog that *parses* but contains invalid entries (foreign URL
    host, path-traversal output_file, empty member patterns) is
    rejected loudly rather than silently replaced.

    Raises:
        ValueError: If a parsed catalog entry fails validation.
    """
    path = catalog_path or DEFAULT_CATALOG_PATH
    try:
        raw = yaml.safe_load(path.read_text())
        datasets = raw["scheduler_datasets"]
        if not isinstance(datasets, dict) or not datasets:
            raise ValueError("scheduler_datasets empty or not a mapping")
    except Exception as exc:
        logger.warning(
            "BSEE catalog %s unusable (%s); using built-in defaults", path, exc
        )
        return BSEE_DATASETS
    # Deliberately OUTSIDE the fallback try/except: an invalid catalog
    # is a deterministic config error, not a missing-file condition.
    validate_dataset_catalog(datasets)
    return datasets


class BseeRefreshJob(AbstractJob):
    """Refresh BSEE Gulf of Mexico offshore structural and pipeline data."""

    name = "bsee_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Execute BSEE data refresh across all cataloged dataset types.

        Downloads each BSEE dataset independently, retrying transient
        per-dataset failures in-job (bounded). Failure semantics
        (issue #460):

        * All datasets written -> ``success``.
        * Partial, remaining failures all deterministic -> ``success``
          with an explicitly marked, non-retryable partial message
          (retrying cannot fix a stale URL).
        * Partial with any transient failure left -> ``failure`` with
          ``retryable=True`` so the scheduler retry layer re-runs the
          job; rows already written are reported in records_updated.
        * Nothing written -> ``failure``; ``retryable=False`` when all
          failures are deterministic.

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
        try:
            datasets = load_dataset_catalog(
                Path(catalog_path) if catalog_path else None
            )
        except ValueError as exc:
            # Invalid catalog entries are a deterministic config error.
            error_msg = f"[deterministic] invalid BSEE dataset catalog: {exc}"
            logger.error(error_msg)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=error_msg,
                retryable=False,
            )

        scraper = BSEEWebScraper()
        total_records = 0
        failures: list[DatasetFailure] = []

        for dataset_name, info in datasets.items():
            outcome = self._process_dataset_with_retry(
                scraper, dataset_name, info, output_dir
            )
            if isinstance(outcome, DatasetFailure):
                logger.warning("BSEE %s", outcome.summary())
                failures.append(outcome)
            else:
                total_records += outcome

        transient_failures = [
            f for f in failures if f.failure_class is FailureClass.TRANSIENT
        ]

        if total_records > 0 and not transient_failures:
            error_msg = None
            if failures:
                # Deterministic-only partial: tolerated, but explicitly
                # marked -- retrying cannot fix a stale URL (#460).
                error_msg = (
                    "[partial:deterministic] Partial BSEE refresh "
                    "(deterministic failures, retry will not help); failed: "
                    + "; ".join(f.summary() for f in failures)
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

        if total_records > 0:
            # Transient partial failure: some datasets remain stale for
            # a retry-worthy reason, so this run must NOT be reported as
            # success (the scheduler retry layer re-runs the job).
            error_msg = (
                "Partial BSEE refresh; transient failures remain after "
                f"{TRANSIENT_DATASET_ATTEMPTS} in-job attempts: "
                + "; ".join(f.summary() for f in failures)
            )
            logger.error(error_msg)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=total_records,
                error_msg=error_msg,
                retryable=True,
            )

        error_msg = "All BSEE downloads failed: " + "; ".join(
            f.summary() for f in failures
        )
        all_deterministic = bool(failures) and not transient_failures
        if all_deterministic:
            error_msg = "[deterministic] " + error_msg
        logger.error(error_msg)
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="failure",
            records_updated=0,
            error_msg=error_msg,
            retryable=not all_deterministic,
        )

    def _process_dataset_with_retry(
        self,
        scraper: BSEEWebScraper,
        dataset_name: str,
        info: dict,
        output_dir: Path,
    ):
        """Run ``_process_dataset`` with bounded retry on transient failures.

        Deterministic failures (stale URL, contract drift) return
        immediately -- retrying them in-process cannot succeed.
        """
        outcome = None
        for attempt in range(1, TRANSIENT_DATASET_ATTEMPTS + 1):
            try:
                outcome = self._process_dataset(scraper, dataset_name, info, output_dir)
            except Exception as exc:  # e.g. parquet write / disk errors
                outcome = DatasetFailure(
                    dataset_name,
                    f"unexpected error: {exc}",
                    FailureClass.TRANSIENT,
                )
            if not isinstance(outcome, DatasetFailure):
                return outcome
            if outcome.failure_class is not FailureClass.TRANSIENT:
                return outcome
            if attempt < TRANSIENT_DATASET_ATTEMPTS:
                logger.info(
                    "BSEE %s transient failure (attempt %d/%d); retrying: %s",
                    dataset_name,
                    attempt,
                    TRANSIENT_DATASET_ATTEMPTS,
                    outcome.reason,
                )
        return outcome

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
        url = info.get("url") or SCRAPER_URLS[url_key]
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
        if kind is PayloadKind.UNKNOWN:
            # Unrecognized non-zip, non-HTML body: could be a gateway
            # error, proxy banner, or rate-limit message. Not evidence
            # of a stale URL, so treat as transient (retry-worthy).
            return DatasetFailure(
                dataset_name,
                f"expected zip, got unrecognized {len(payload)}-byte "
                "payload (gateway/proxy error?); will retry",
                FailureClass.TRANSIENT,
            )
        if kind is not PayloadKind.ZIP:
            # HTTP 200 + HTML (or an empty body) means the URL went
            # stale upstream; retrying in-process cannot succeed
            # (issues #267 / #460).
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

        out_path = (output_dir / info["output_file"]).resolve()
        # Defense in depth on top of catalog validation: the resolved
        # output path must stay inside output_dir (no path traversal).
        if out_path.parent != output_dir.resolve():
            return DatasetFailure(
                dataset_name,
                f"output_file {info['output_file']!r} escapes output_dir "
                f"{output_dir} -- rejected",
                FailureClass.DETERMINISTIC,
            )
        df.to_parquet(out_path, engine="pyarrow", index=False, compression="snappy")
        logger.info(
            "BSEE %s wrote %d rows from %s to %s",
            dataset_name,
            len(df),
            member_name,
            out_path,
        )
        return len(df)
