"""Enrich status.json with staleness details and alert history.

Called by StatusReporter to add structured staleness data
for the monitoring dashboard (per D-14).
"""
import logging
from typing import Any, Dict

from worldenergydata.scheduler.staleness import get_staleness_details

logger = logging.getLogger(__name__)


def enrich_status(status: dict) -> dict:
    """Add staleness and alerts sections to a status report dict.

    Args:
        status: Base status dict from StatusReporter.build_report()

    Returns:
        Enriched status dict with added 'staleness' and 'alerts' keys.
    """
    enriched = dict(status)
    enriched["staleness"] = {}
    for detail in get_staleness_details(status):
        enriched["staleness"][detail["job_name"]] = {
            "threshold_hours": detail["threshold_hours"],
            "is_stale": detail["is_stale"],
            "hours_since_last_success": detail["hours_since_last_run"],
        }
    if "alerts" not in enriched:
        enriched["alerts"] = []
    return enriched
