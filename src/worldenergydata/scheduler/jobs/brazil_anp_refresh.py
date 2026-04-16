"""Brazilian ANP (National Petroleum Agency) data refresh job -- Tier 2 (scaffolding only).

TODO: Implement data fetching for Brazil ANP production data.
- Identify ANP public data portal download URLs
- Add HTTP client or scraper logic for production reports
- Write Parquet output to data/brazil_anp/ directory
- Add tests in tests/unit/scheduler/test_brazil_anp_adapter.py
"""

import logging
from datetime import datetime
from pathlib import Path

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("brazil_anp")


class BrazilAnpRefreshJob(AbstractJob):
    """Refresh Brazilian ANP production data -- Tier 2 stub.

    This adapter follows the standard pattern (D-17) but data
    fetching is not yet implemented. Returns a skipped result
    until implementation is complete.
    """

    name = "brazil_anp_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Return skipped result until ANP fetching is implemented.

        Args:
            config: Reserved for future use (e.g., output_dir, data_format).

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
