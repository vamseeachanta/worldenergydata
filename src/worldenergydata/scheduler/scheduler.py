"""Main DataScheduler: job registration, loop, start/stop, status, manual trigger."""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

import schedule

from worldenergydata.scheduler.alerting import AlertSender
from worldenergydata.scheduler.config import (
    SchedulerConfig,
    load_config,
    validate_config,
)
from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult
from worldenergydata.scheduler.monitor import JobLogger, RetryManager, StatusReporter
from worldenergydata.scheduler.status_enricher import enrich_status

logger = logging.getLogger(__name__)


class DataScheduler:
    """Persistent data collection scheduler using the `schedule` library.

    Responsibilities:
    - Register job adapters.
    - Start/stop a blocking run loop.
    - Provide per-job status (last_run, next_run, last_result).
    - Allow manual one-off job triggers.
    """

    def __init__(self, config_path: str) -> None:
        self._config: SchedulerConfig = load_config(config_path)
        validate_config(self._config)
        self._jobs: Dict[str, AbstractJob] = {}
        self._job_state: Dict[str, dict] = {}
        self._running: bool = False
        self._schedule = schedule.Scheduler()

        mon = self._config.monitoring
        self._job_logger = JobLogger(
            log_dir=mon.get("log_dir", "logs/scheduler/"),
            retention_days=mon.get("log_retention_days", 30),
        )
        self._retry_manager = RetryManager(
            max_retries=max(mon.get("retry_max", 3), 1),
            backoff_seconds=mon.get("retry_backoff_seconds", 60),
        )
        self._status_reporter = StatusReporter(
            status_file=mon.get("status_file", "logs/scheduler/status.json"),
            webhook_url=mon.get("webhook_url"),
        )
        self._alert_sender = AlertSender(
            smtp_host=mon.get("smtp_host"),
            smtp_user=mon.get("smtp_user"),
            smtp_pass=mon.get("smtp_pass"),
            smtp_port=mon.get("smtp_port", 587),
            recipients=mon.get("alert_recipients", []),
        )

    def register_job(self, job: AbstractJob) -> None:
        """Register a job adapter.

        Args:
            job: An AbstractJob subclass instance.

        Raises:
            ValueError: If a job with the same name is already registered.
        """
        if job.name in self._jobs:
            raise ValueError(
                f"Job '{job.name}' is already registered. " "Use a unique name per job."
            )
        self._jobs[job.name] = job
        self._job_state[job.name] = {
            "last_run": None,
            "last_result": None,
            "next_run": self._compute_next_run(job.name),
        }
        logger.info("Registered job: %s", job.name)

    def _compute_next_run(self, job_name: str) -> Optional[str]:
        """Estimate next run time based on job config interval."""
        job_cfg = self._config.get_job_config(job_name)
        if job_cfg is None:
            return None
        scheduled_time = job_cfg.get("time", "00:00")
        return f"next {job_cfg.get('interval', 'daily')} at {scheduled_time}"

    def _is_job_enabled(self, job_name: str) -> bool:
        """Return True if the job is enabled in config."""
        job_cfg = self._config.get_job_config(job_name)
        if job_cfg is None:
            return True
        return job_cfg.get("enabled", True)

    def run_once(self, job_name: str) -> JobResult:
        """Manually trigger a single job execution.

        Args:
            job_name: Name of the registered job to run.

        Returns:
            JobResult from the execution.

        Raises:
            ValueError: If the job is not registered.
        """
        if job_name not in self._jobs:
            raise ValueError(
                f"Job '{job_name}' is not registered. "
                f"Available jobs: {list(self._jobs.keys())}"
            )

        job = self._jobs[job_name]

        if not self._is_job_enabled(job_name):
            logger.info("Job '%s' is disabled; skipping.", job_name)
            now = datetime.now()
            skipped = JobResult(
                job_name=job_name,
                start_time=now,
                end_time=now,
                status="skipped",
                records_updated=0,
                error_msg=None,
            )
            self._record_result(job_name, skipped)
            return skipped

        job_cfg = self._config.get_job_config(job_name) or {}

        def _run() -> JobResult:
            return job.run(config=job_cfg)

        result = self._retry_manager.run_with_retry(_run)
        self._record_result(job_name, result)
        self._job_logger.log_result(result)
        # Trigger alerting and enriched status write
        self._status_reporter.check_and_alert([result], self._alert_sender)
        logger.info(
            "Job '%s' finished with status=%s records=%d",
            job_name,
            result.status,
            result.records_updated,
        )
        return result

    def _record_result(self, job_name: str, result: JobResult) -> None:
        """Update in-memory state with job result."""
        self._job_state[job_name]["last_run"] = result.start_time.isoformat()
        self._job_state[job_name]["last_result"] = result.status

    def status(self) -> dict:
        """Return per-job status summary enriched with staleness details.

        Returns:
            Dict with 'jobs', 'staleness', and 'alerts' keys.
        """
        jobs_status = {}
        for name, state in self._job_state.items():
            jobs_status[name] = {
                "last_run": state["last_run"],
                "last_result": state["last_result"],
                "next_run": state["next_run"],
            }
        base = {"jobs": jobs_status}
        return enrich_status(base)

    def _schedule_jobs(self) -> None:
        """Register enabled jobs with the schedule library."""
        enabled_jobs = {j["name"] for j in self._config.get_enabled_jobs()}

        for job_name, job in self._jobs.items():
            if job_name not in enabled_jobs:
                logger.info("Job '%s' is disabled; not scheduling.", job_name)
                continue

            job_cfg = self._config.get_job_config(job_name) or {}
            interval = job_cfg.get("interval", "daily")
            run_time = job_cfg.get("time", "00:00")

            def make_task(name: str) -> callable:
                def _task():
                    self.run_once(name)

                return _task

            task = make_task(job_name)
            if interval == "daily":
                self._schedule.every().day.at(run_time).do(task)
            elif interval == "weekly":
                self._schedule.every().week.at(run_time).do(task)
            elif interval == "monthly":
                self._schedule.every(30).days.at(run_time).do(task)
            else:
                logger.warning(
                    "Unknown interval '%s' for job '%s'; defaulting to daily.",
                    interval,
                    job_name,
                )
                self._schedule.every().day.at(run_time).do(task)

            logger.info(
                "Scheduled job '%s' with interval='%s' at '%s'.",
                job_name,
                interval,
                run_time,
            )

    def start(self, tick_interval: float = 1.0) -> None:
        """Start the blocking scheduler loop.

        Registers all jobs with the schedule library and then runs
        schedule.run_pending() every tick_interval seconds until stop() is
        called.

        Args:
            tick_interval: Seconds between schedule ticks (default 1.0).
        """
        logger.info("DataScheduler starting.")
        self._schedule_jobs()
        self._running = True
        try:
            while self._running:
                self._schedule.run_pending()
                time.sleep(tick_interval)
        finally:
            self._running = False
            logger.info("DataScheduler stopped.")

    def stop(self) -> None:
        """Signal the scheduler loop to stop after the current tick."""
        logger.info("DataScheduler stop requested.")
        self._running = False
