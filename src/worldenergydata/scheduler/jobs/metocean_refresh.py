"""Metocean tracked locations refresh job."""
import logging
from datetime import datetime
from typing import List

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)


class MetoceanRefreshJob(AbstractJob):
    """Refresh metocean data for tracked geographic locations."""

    name = "metocean_refresh"

    def run(self, config: dict) -> JobResult:
        """Execute metocean data refresh for configured locations.

        Each location in config["locations"] is refreshed independently.
        records_updated equals the number of locations successfully processed.

        Args:
            config: Must contain "locations" list with lat/lon/name dicts.
                    Example: [{"lat": 28.5, "lon": -88.5, "name": "GOM"}]

        Returns:
            JobResult with records_updated set to number of locations processed.
        """
        start = datetime.now()
        locations: List[dict] = config.get("locations", [])

        if not locations:
            logger.info("Metocean refresh: no locations configured, skipping.")
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="success",
                records_updated=0,
                error_msg=None,
            )

        processed = 0
        errors = []
        for loc in locations:
            name = loc.get("name", f"({loc.get('lat')},{loc.get('lon')})")
            try:
                logger.info("Refreshing metocean data for location: %s", name)
                # Stub: real implementation would call metocean data API
                processed += 1
            except Exception as exc:  # pragma: no cover
                logger.error("Failed to refresh metocean for %s: %s", name, exc)
                errors.append(str(exc))

        status = "success" if not errors else "failure"
        error_msg = "; ".join(errors) if errors else None

        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status=status,
            records_updated=processed,
            error_msg=error_msg,
        )
