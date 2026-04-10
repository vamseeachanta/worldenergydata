"""CLI for the worldenergydata data collection scheduler.

Usage:
    python -m worldenergydata.scheduler start
    python -m worldenergydata.scheduler stop
    python -m worldenergydata.scheduler status
    python -m worldenergydata.scheduler run-job bsee_refresh
"""
import json
import logging
import sys
from typing import List, Optional

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.jobs.bsee_refresh import BseeRefreshJob
from worldenergydata.scheduler.jobs.sodir_refresh import SodirRefreshJob
from worldenergydata.scheduler.jobs.eia_us_refresh import EiaUsRefreshJob
from worldenergydata.scheduler.jobs.brazil_anp_refresh import BrazilAnpRefreshJob
from worldenergydata.scheduler.jobs.ukcs_refresh import UkcsRefreshJob
from worldenergydata.scheduler.jobs.metocean_refresh import MetoceanRefreshJob
from worldenergydata.scheduler.jobs.lng_terminals_refresh import LngTerminalsRefreshJob
from worldenergydata.scheduler.scheduler import DataScheduler

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = "config/scheduler/scheduler_config.yml"

ALL_JOBS: List[AbstractJob] = [
    BseeRefreshJob(),
    SodirRefreshJob(),
    EiaUsRefreshJob(),
    BrazilAnpRefreshJob(),
    UkcsRefreshJob(),
    MetoceanRefreshJob(),
    LngTerminalsRefreshJob(),
]


def _build_scheduler(config_path: str, jobs: List[AbstractJob]) -> DataScheduler:
    """Construct and register all jobs on a DataScheduler."""
    scheduler = DataScheduler(config_path=config_path)
    for job in jobs:
        scheduler.register_job(job)
    return scheduler


def cmd_status(
    config_path: str = DEFAULT_CONFIG,
    jobs: Optional[List[AbstractJob]] = None,
) -> dict:
    """Return the current scheduler status dict.

    Args:
        config_path: Path to YAML config file.
        jobs: Job adapters to register (defaults to ALL_JOBS).

    Returns:
        Status dict with per-job last_run, next_run, last_result.
    """
    if jobs is None:
        jobs = ALL_JOBS
    scheduler = _build_scheduler(config_path, jobs)
    return scheduler.status()


def cmd_run_job(
    job_name: str,
    config_path: str = DEFAULT_CONFIG,
    jobs: Optional[List[AbstractJob]] = None,
) -> JobResult:
    """Manually trigger a single job by name.

    Args:
        job_name: Name of the job to execute.
        config_path: Path to YAML config file.
        jobs: Job adapters to register (defaults to ALL_JOBS).

    Returns:
        JobResult from the execution.

    Raises:
        ValueError: If job_name is not among registered jobs.
    """
    if jobs is None:
        jobs = ALL_JOBS
    scheduler = _build_scheduler(config_path, jobs)
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


def main(argv: Optional[List[str]] = None) -> None:
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
        logger.info(f"Starting scheduler with config: {config_path}")
        scheduler = _build_scheduler(config_path, ALL_JOBS)
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
            logger.info(f"Job '{job_name}' completed with status: {result.status}")
            logger.info(f"  records_updated: {result.records_updated}")
            if result.error_msg:
                logger.info(f"  error: {result.error_msg}")
        except ValueError as exc:
            logger.error(f"Error: {exc}")
            sys.exit(1)

    else:
        logger.info(f"Unknown command: '{command}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
