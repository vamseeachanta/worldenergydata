"""Metocean/weather data refresh job -- Tier 2 (scaffolding only).

TODO: Implement data fetching for metocean sources.
- Identify API endpoint (e.g., NOAA buoy data, OpenWeather maritime API)
- Add HTTP client for weather/wave data retrieval
- Write Parquet output to data/metocean/ directory
- Add tests in tests/unit/scheduler/test_metocean_adapter.py
"""
import logging
from datetime import datetime

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)


class MetoceanRefreshJob(AbstractJob):
    """Refresh metocean data -- Tier 2 stub.

    This adapter follows the standard pattern (D-17) but data
    fetching is not yet implemented. Returns a skipped result
    until implementation is complete.
    """

    name = "metocean_refresh"

    def run(self, config: dict) -> JobResult:
        """Return skipped result until metocean fetching is implemented.

        Args:
            config: Reserved for future use (e.g., locations, API keys).

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
