"""Base classes for scheduler jobs: JobResult dataclass and AbstractJob interface."""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

INTERVAL_THRESHOLDS = {
    "daily": timedelta(hours=24),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}

INTERVAL_DAYS = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
}


@dataclass
class JobResult:
    """Result of a single job execution.

    Attributes:
        retryable: Whether the scheduler retry layer may re-run the job
            after a non-success result. Jobs set this to False for
            deterministic failures (e.g. a stale upstream URL serving
            HTML) that cannot succeed on immediate retry (issue #460).
            Ignored when status is "success".
    """

    job_name: str
    start_time: datetime
    end_time: datetime
    status: str  # "success", "failure", "skipped"
    records_updated: int
    error_msg: Optional[str]
    retryable: bool = True


class AbstractJob(ABC):
    """Abstract base class for all data collection jobs."""

    name: str
    default_output_dir: Path

    @abstractmethod
    def run(self, config: dict) -> JobResult:
        """Execute the job and return a result.

        Args:
            config: Job-specific configuration dictionary.

        Returns:
            JobResult with execution details.
        """

    def is_due(self, last_run: Optional[datetime], interval: str) -> bool:
        """Determine whether the job should run based on last execution time.

        Args:
            last_run: Timestamp of the last successful run, or None if never run.
            interval: Scheduling interval string ("daily", "weekly", "monthly").

        Returns:
            True if the job is due to run, False otherwise.
        """
        if last_run is None:
            return True

        threshold = INTERVAL_THRESHOLDS.get(interval)
        if threshold is None:
            logger.warning(
                "Unknown interval '%s' for job '%s'; treating as due.",
                interval,
                self.name,
            )
            return True

        elapsed = datetime.now() - last_run
        return elapsed >= threshold


def write_refresh_metadata(
    module_name: str,
    output_dir: Path,
    records_updated: int,
) -> None:
    """Write a ``_metadata.json`` file after a successful refresh.

    This provides a lightweight signal for the CLI ``status`` command and
    any downstream freshness dashboards.

    Args:
        module_name: Logical module identifier (e.g. ``"bsee"``).
        output_dir: Module data directory where ``_metadata.json`` is written.
        records_updated: Total records written during this refresh.
    """
    try:
        file_count = sum(
            1
            for p in output_dir.rglob("*")
            if p.is_file() and p.name != "_metadata.json"
        )
        total_size = sum(
            p.stat().st_size
            for p in output_dir.rglob("*")
            if p.is_file() and p.name != "_metadata.json"
        )
        metadata = {
            "module": module_name,
            "last_refresh": datetime.now(tz=timezone.utc).isoformat(),
            "record_count": records_updated,
            "file_count": file_count,
            "total_size_bytes": total_size,
            "source_url": "",
            "format": "parquet",
            "files": [],
        }
        meta_path = output_dir / "_metadata.json"
        meta_path.write_text(json.dumps(metadata, indent=2) + "\n")
        logger.info("Wrote %s", meta_path)
    except Exception as exc:
        logger.warning("Failed to write _metadata.json for %s: %s", module_name, exc)


def write_success_manifest(
    job_name: str,
    output_dir: Path,
    result: JobResult,
    interval: str,
) -> None:
    """Write scheduler health manifest for a successful refresh."""
    if result.status != "success":
        return

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest = {
            "job_name": job_name,
            "status": result.status,
            "last_success_ts": result.end_time.astimezone(timezone.utc).isoformat(),
            "refresh_interval_days": INTERVAL_DAYS.get(interval, 7),
            "records_updated": result.records_updated,
            "start_time": result.start_time.astimezone(timezone.utc).isoformat(),
            "end_time": result.end_time.astimezone(timezone.utc).isoformat(),
            "error_msg": result.error_msg,
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        logger.info("Wrote %s", manifest_path)
    except Exception as exc:
        logger.warning("Failed to write manifest.json for %s: %s", job_name, exc)
