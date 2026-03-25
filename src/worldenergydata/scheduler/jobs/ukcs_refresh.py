"""UKCS (UK Continental Shelf) data refresh job."""
import logging
from datetime import datetime

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)


class UkcsRefreshJob(AbstractJob):
    """Refresh UK Continental Shelf oil and gas production data."""

    name = "ukcs_refresh"

    def run(self, config: dict) -> JobResult:
        """Execute UKCS data refresh.

        Args:
            config: Optional configuration (e.g., nsta_api_url, output_dir).

        Returns:
            JobResult indicating success or failure.
        """
        start = datetime.now()
        try:
            logger.info("UKCS data refresh started.")
            # Stub: real implementation fetches from NSTA (North Sea Transition Authority) data
            logger.info("UKCS data refresh completed (stub).")
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=0,
                error_msg=None,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("UKCS refresh failed: %s", exc)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=str(exc),
            )
