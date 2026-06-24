"""YAML config loader and validation for the data collection scheduler."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

VALID_INTERVALS = {"daily", "weekly", "monthly"}


@dataclass
class SchedulerConfig:
    """Parsed and validated scheduler configuration."""

    jobs: List[Dict[str, Any]]
    monitoring: Dict[str, Any]

    def get_job_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Return config dict for the named job, or None if not found."""
        for job in self.jobs:
            if job.get("name") == name:
                return job
        return None

    def get_enabled_jobs(self) -> List[Dict[str, Any]]:
        """Return only the jobs with enabled=true."""
        return [j for j in self.jobs if j.get("enabled", True)]


def load_config(config_path: str) -> SchedulerConfig:
    """Load and parse scheduler YAML config.

    Args:
        config_path: Absolute or relative path to the YAML config file.

    Returns:
        SchedulerConfig with parsed jobs and monitoring settings.

    Raises:
        FileNotFoundError: If config_path does not exist.
        ValueError: If required sections are missing or job config is invalid.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict) or "jobs" not in raw:
        raise ValueError(
            f"Config at '{config_path}' must contain a top-level 'jobs' list."
        )

    jobs = raw["jobs"]
    if not isinstance(jobs, list):
        raise ValueError("'jobs' must be a YAML list.")

    for job in jobs:
        if "name" not in job:
            raise ValueError(f"Each job entry must have a 'name' field. Got: {job}")

    monitoring = raw.get("monitoring", {})
    config = SchedulerConfig(jobs=jobs, monitoring=monitoring)
    return config


def validate_config(config: SchedulerConfig) -> None:
    """Validate a parsed SchedulerConfig for semantic correctness.

    Args:
        config: A SchedulerConfig returned by load_config().

    Raises:
        ValueError: If any job has an invalid interval, or monitoring
                    settings are out of range.
    """
    for job in config.jobs:
        interval = job.get("interval")
        if interval is not None and interval not in VALID_INTERVALS:
            raise ValueError(
                f"Job '{job.get('name')}' has invalid interval '{interval}'. "
                f"Must be one of: {sorted(VALID_INTERVALS)}."
            )

    retry_max = config.monitoring.get("retry_max")
    if retry_max is not None and retry_max < 0:
        raise ValueError(f"monitoring.retry_max must be >= 0, got {retry_max}.")

    retention = config.monitoring.get("log_retention_days")
    if retention is not None and retention < 1:
        raise ValueError(
            f"monitoring.log_retention_days must be >= 1, got {retention}."
        )
