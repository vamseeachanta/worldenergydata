"""UK Continental Shelf (UKCS) data refresh job -- Tier 2 (scaffolding only).

TODO: Implement data fetching for UKCS production data.
- Identify NSTA (North Sea Transition Authority) data endpoints
- Add HTTP client for production/well data retrieval
- Write Parquet output to data/ukcs/ directory
- Add tests in tests/unit/scheduler/test_ukcs_adapter.py
"""
import logging
from datetime import datetime

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)


class UkcsRefreshJob(AbstractJob):
    """Refresh UK Continental Shelf production data -- Tier 2 stub.

    This adapter follows the standard pattern (D-17) but data
    fetching is not yet implemented. Returns a skipped result
    until implementation is complete.
    """

    name = "ukcs_refresh"

    def run(self, config: dict) -> JobResult:
        """Return skipped result until UKCS fetching is implemented.

        Args:
            config: Reserved for future use (e.g., nsta_api_url, output_dir).

        Returns:
            JobResult with status="skipped".
        """
        start = datetime.now()
        logger.info("%s: Tier 2 stub -- not yet implemented.", self.name)
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="skipped",
            records_updated=0,
            error_msg=None,
        )
