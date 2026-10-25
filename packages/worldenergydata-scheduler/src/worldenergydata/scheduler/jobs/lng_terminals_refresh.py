"""Disabled LNG refresh placeholder with an explicit non-retryable failure.

Issue #458 permits disabling the adapter until a real upstream refresh exists.
Invoking it directly or accidentally enabling it must expose the implementation
gap without backoff or a successful freshness manifest.
"""

import logging
from datetime import datetime

from worldenergydata.common.data_resolver import get_module_data_safe
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = get_module_data_safe("lng_terminals")


class LngTerminalsRefreshJob(AbstractJob):
    """Reject refresh requests until upstream collection is implemented."""

    name = "lng_terminals_refresh"
    implemented = False
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def run(self, config: dict) -> JobResult:
        """Return actionable failure without collection, writes, or retries."""
        start = datetime.now()
        reason = (
            "LNG terminal refresh is not implemented; keep enabled: false "
            "in scheduler configuration until an upstream adapter writes data "
            "and reports success (issue #458)."
        )
        logger.error("%s: %s", self.name, reason)
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="failure",
            records_updated=0,
            error_msg=reason,
            retryable=False,
        )
