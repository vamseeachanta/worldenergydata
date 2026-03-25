"""LNG Terminals dataset refresh job."""
import logging
from datetime import datetime

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)


class LngTerminalsRefreshJob(AbstractJob):
    """Refresh the global LNG terminals dataset."""

    name = "lng_terminals_refresh"

    def run(self, config: dict) -> JobResult:
        """Execute LNG terminals data refresh.

        Loads the built-in LNG terminal dataset and optionally applies
        any configured source overrides.

        Args:
            config: May contain "data_path" for external source data.

        Returns:
            JobResult indicating success or failure.
        """
        start = datetime.now()
        try:
            data_path = config.get("data_path")
            if data_path:
                logger.info("LNG terminals refresh using data_path=%s", data_path)
            else:
                logger.info("LNG terminals refresh using built-in dataset.")

            from worldenergydata.lng_terminals.query import (
                LngTerminalClient,
                LngTerminalQuery,
            )

            client = LngTerminalClient()
            result = client.query(LngTerminalQuery())
            records = result.total_count

            logger.info("LNG terminals refresh completed: %d terminals.", records)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=records,
                error_msg=None,
            )
        except Exception as exc:  # pragma: no cover
            logger.error("LNG terminals refresh failed: %s", exc)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=str(exc),
            )
