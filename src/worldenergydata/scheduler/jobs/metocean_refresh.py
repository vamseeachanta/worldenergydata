"""Metocean/weather data refresh job -- Tier 2 (scaffolding only).

TODO: Implement data fetching for metocean sources.
- Identify API endpoint (e.g., NOAA buoy data, OpenWeather maritime API)
- Add HTTP client for weather/wave data retrieval
- Write Parquet output to data/metocean/ directory
- Add tests in tests/unit/scheduler/test_metocean_adapter.py
"""

import logging
from datetime import datetime
from pathlib import Path

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("metocean")


class MetoceanRefreshJob(AbstractJob):
    """Refresh metocean data -- Tier 2 stub.

    This adapter follows the standard pattern (D-17) but data
    fetching is not yet implemented. Returns a skipped result
    until implementation is complete.
    """

    name = "metocean_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Return skipped result until metocean fetching is implemented.

        Args:
            config: Reserved for future use (e.g., locations, API keys, output_dir).

        Returns:
            JobResult with status="skipped".
        """
        start = datetime.now()
        output_dir = Path(config.get("output_dir", self.default_output_dir))
        # Scaffolded for future adapter implementation; path is intentionally resolved now.
        logger.info("%s: Tier 2 stub -- not yet implemented.", self.name)
        logger.debug("%s output directory: %s", self.name, output_dir)
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="skipped",
            records_updated=0,
            error_msg=None,
        )
