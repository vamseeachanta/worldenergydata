"""Base classes for scheduler jobs: JobResult dataclass and AbstractJob interface."""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

INTERVAL_THRESHOLDS = {
    "daily": timedelta(hours=24),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}


@dataclass
class JobResult:
    """Result of a single job execution."""

    job_name: str
    start_time: datetime
    end_time: datetime
    status: str  # "success", "failure", "skipped"
    records_updated: int
    error_msg: Optional[str]


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
