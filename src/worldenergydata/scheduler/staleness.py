"""Staleness detection with per-source cadence thresholds.

Compares last-run timestamps against configured thresholds to identify
data sources that are overdue for refresh (per D-13/D-14 requirements).
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Per-source staleness thresholds (D-13 cadences with safety margin).
# Tier 1 sources only — Tier 2 sources are not tracked for staleness.
STALENESS_THRESHOLDS: Dict[str, timedelta] = {
    "sodir_refresh": timedelta(hours=36),
    "bsee_refresh": timedelta(days=10),
    "eia_us_refresh": timedelta(days=45),
}


def check_staleness(status: dict) -> List[str]:
    """Return list of job names whose data is stale.

    Args:
        status: Status dict from StatusReporter.build_report() with
                shape ``{"jobs": {"name": {"start_time": ..., ...}, ...}}``.

    Returns:
        List of stale job names (only those tracked in STALENESS_THRESHOLDS).
    """
    stale_jobs: List[str] = []
    jobs = status.get("jobs", {})

    now = datetime.now()

    for job_name, threshold in STALENESS_THRESHOLDS.items():
        entry = jobs.get(job_name, {})
        start_time_iso = entry.get("start_time") or entry.get("last_run")

        if start_time_iso is None:
            # Never run or missing — always stale
            stale_jobs.append(job_name)
            continue

        try:
            last_run = datetime.fromisoformat(start_time_iso)
        except (ValueError, TypeError):
            stale_jobs.append(job_name)
            continue

        if (now - last_run) > threshold:
            stale_jobs.append(job_name)

    return stale_jobs


def get_staleness_details(status: dict) -> List[Dict[str, Any]]:
    """Return detailed staleness info for each tracked job.

    Args:
        status: Status dict with shape ``{"jobs": {"name": {...}, ...}}``.

    Returns:
        List of dicts with keys: job_name, threshold_hours, is_stale,
        hours_since_last_run (None if never run).
    """
    details: List[Dict[str, Any]] = []
    jobs = status.get("jobs", {})
    now = datetime.now()

    for job_name, threshold in STALENESS_THRESHOLDS.items():
        threshold_hours = threshold.total_seconds() / 3600.0

        entry = jobs.get(job_name, {})
        start_time_iso = entry.get("start_time") or entry.get("last_run")

        if start_time_iso is None:
            details.append({
                "job_name": job_name,
                "threshold_hours": threshold_hours,
                "is_stale": True,
                "hours_since_last_run": None,
            })
            continue

        try:
            last_run = datetime.fromisoformat(start_time_iso)
        except (ValueError, TypeError):
            details.append({
                "job_name": job_name,
                "threshold_hours": threshold_hours,
                "is_stale": True,
                "hours_since_last_run": None,
            })
            continue

        elapsed = now - last_run
        hours_since = elapsed.total_seconds() / 3600.0

        details.append({
            "job_name": job_name,
            "threshold_hours": threshold_hours,
            "is_stale": elapsed > threshold,
            "hours_since_last_run": hours_since,
        })

    return details
