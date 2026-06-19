"""CLI for the worldenergydata data collection scheduler.

Usage:
    python -m worldenergydata.scheduler start
    python -m worldenergydata.scheduler stop
    python -m worldenergydata.scheduler status
    python -m worldenergydata.scheduler run-job bsee_refresh
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator, Sequence
from importlib import import_module
from typing import TYPE_CHECKING, Optional

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

if TYPE_CHECKING:
    from worldenergydata.scheduler.scheduler import DataScheduler

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "config/scheduler/scheduler_config.yml"

_JOB_SPECS: tuple[tuple[str, str], ...] = (
    ("bsee_refresh", "worldenergydata.scheduler.jobs.bsee_refresh.BseeRefreshJob"),
    ("hse_refresh", "worldenergydata.scheduler.jobs.hse_refresh.HseRefreshJob"),
    ("sodir_refresh", "worldenergydata.scheduler.jobs.sodir_refresh.SodirRefreshJob"),
    ("eia_us_refresh", "worldenergydata.scheduler.jobs.eia_us_refresh.EiaUsRefreshJob"),
    (
        "brazil_anp_refresh",
        "worldenergydata.scheduler.jobs.brazil_anp_refresh.BrazilAnpRefreshJob",
    ),
    ("ukcs_refresh", "worldenergydata.scheduler.jobs.ukcs_refresh.UkcsRefreshJob"),
    (
        "metocean_refresh",
        "worldenergydata.scheduler.jobs.metocean_refresh.MetoceanRefreshJob",
    ),
    (
        "lng_terminals_refresh",
        "worldenergydata.scheduler.jobs.lng_terminals_refresh.LngTerminalsRefreshJob",
    ),
)


class LazyRefreshJob(AbstractJob):
    """Scheduler job proxy that imports the concrete adapter only on execution."""

    def __init__(self, name: str, class_path: str) -> None:
        self.name = name
        self._class_path = class_path

    def _load(self) -> AbstractJob:
        job_cls = _load_job_class(self._class_path)
        return job_cls()

    def run(self, config: dict) -> JobResult:
        """Execute the concrete job adapter after lazy import."""
        return self._load().run(config)


class LazyJobRegistry(Sequence[AbstractJob]):
    """Backwards-compatible lazy view over the default scheduler jobs.

    Older tests and callers import ``ALL_JOBS`` and iterate over job instances.
    The previous list eagerly instantiated every job at module import time,
    which made no-op/help paths pay data-source import costs. This sequence
    keeps the public iteration behavior while deferring imports until the
    registry is actually consumed by status/start/run-job paths.
    """

    def __iter__(self) -> Iterator[AbstractJob]:
        return iter(get_all_jobs())

    def __len__(self) -> int:
        return len(_JOB_SPECS)

    def __getitem__(self, index):
        return get_all_jobs()[index]


def _load_job_class(class_path: str) -> type[AbstractJob]:
    module_name, class_name = class_path.rsplit(".", 1)
    module = import_module(module_name)
    return getattr(module, class_name)


def get_all_jobs() -> list[AbstractJob]:
    """Create lazy proxies for the default scheduler job adapters."""
    return [LazyRefreshJob(name, class_path) for name, class_path in _JOB_SPECS]


ALL_JOBS: Sequence[AbstractJob] = LazyJobRegistry()


def _coerce_jobs(jobs: Optional[Sequence[AbstractJob]]) -> list[AbstractJob]:
    if jobs is None:
        return get_all_jobs()
    return list(jobs)


def _build_scheduler(config_path: str, jobs: Sequence[AbstractJob]) -> "DataScheduler":
    """Construct and register all jobs on a DataScheduler."""
    from worldenergydata.scheduler.scheduler import DataScheduler

    scheduler = DataScheduler(config_path=config_path)
    for job in jobs:
        scheduler.register_job(job)
    return scheduler


def cmd_status(
    config_path: str = DEFAULT_CONFIG,
    jobs: Optional[Sequence[AbstractJob]] = None,
) -> dict:
    """Return the current scheduler status dict.

    Args:
        config_path: Path to YAML config file.
        jobs: Job adapters to register (defaults to lazy default jobs).

    Returns:
        Status dict with per-job last_run, next_run, last_result.
    """
    scheduler = _build_scheduler(config_path, _coerce_jobs(jobs))
    return scheduler.status()


def cmd_run_job(
    job_name: str,
    config_path: str = DEFAULT_CONFIG,
    jobs: Optional[Sequence[AbstractJob]] = None,
) -> JobResult:
    """Manually trigger a single job by name.

    Args:
        job_name: Name of the job to execute.
        config_path: Path to YAML config file.
        jobs: Job adapters to register (defaults to lazy default jobs).

    Returns:
        JobResult from the execution.

    Raises:
        ValueError: If job_name is not among registered jobs.
    """
    scheduler = _build_scheduler(config_path, _coerce_jobs(jobs))
    return scheduler.run_once(job_name)


def cmd_stop(config_path: str = DEFAULT_CONFIG) -> dict:
    """Request scheduler stop (no-op if not running in this process).

    Returns a confirmation dict. For a long-running background process,
    use a PID file or signal; this stub handles the in-process case.

    Args:
        config_path: Path to YAML config file (unused here, for API consistency).

    Returns:
        Dict with confirmation message.
    """
    logger.info("Stop requested via CLI.")
    return {"message": "Scheduler stop signal sent (or not running in this process)."}


def main(argv: Optional[list[str]] = None) -> None:
    """Entry point for CLI invocation.

    Dispatches to cmd_status, cmd_run_job, or cmd_stop based on argv.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args = argv if argv is not None else sys.argv[1:]

    if not args:
        logger.info(
            "Usage:\n"
            "  python -m worldenergydata.scheduler start [--config PATH]\n"
            "  python -m worldenergydata.scheduler stop [--config PATH]\n"
            "  python -m worldenergydata.scheduler status [--config PATH]\n"
            "  python -m worldenergydata.scheduler run-job <name> [--config PATH]\n"
        )
        sys.exit(0)

    command = args[0]
    config_path = DEFAULT_CONFIG

    # Parse --config flag if present
    if "--config" in args:
        idx = args.index("--config")
        if idx + 1 < len(args):
            config_path = args[idx + 1]

    if command == "start":
        logger.info("Starting scheduler with config: %s", config_path)
        scheduler = _build_scheduler(config_path, get_all_jobs())
        scheduler.start()

    elif command == "stop":
        result = cmd_stop(config_path=config_path)
        logger.info(result["message"])

    elif command == "status":
        result = cmd_status(config_path=config_path)
        logger.info(json.dumps(result, indent=2))

    elif command == "run-job":
        if len(args) < 2:
            logger.info("Error: run-job requires a job name argument.")
            sys.exit(1)
        job_name = args[1]
        try:
            result = cmd_run_job(job_name=job_name, config_path=config_path)
            logger.info("Job '%s' completed with status: %s", job_name, result.status)
            logger.info("  records_updated: %s", result.records_updated)
            if result.error_msg:
                logger.info("  error: %s", result.error_msg)
        except ValueError as exc:
            logger.error("Error: %s", exc)
            sys.exit(1)

    else:
        logger.info("Unknown command: '%s'", command)
        sys.exit(1)


if __name__ == "__main__":
    main()
