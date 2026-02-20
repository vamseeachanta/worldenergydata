"""SODIR (Norwegian Offshore Directorate) data refresh job."""
import logging
from datetime import datetime

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)


class SodirRefreshJob(AbstractJob):
    """Refresh SODIR Norwegian Continental Shelf production data."""

    name = "sodir_refresh"

    def run(self, config: dict) -> JobResult:
        """Execute SODIR data refresh.

        Args:
            config: Optional configuration (e.g., api_url, output_dir).

        Returns:
            JobResult indicating success or failure.
        """
        start = datetime.now()
        try:
            logger.info("SODIR data refresh started.")
            # Stub: real implementation calls SODIR public API
            logger.info("SODIR data refresh completed (stub).")
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=0,
                error_msg=None,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("SODIR refresh failed: %s", exc)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=str(exc),
            )
