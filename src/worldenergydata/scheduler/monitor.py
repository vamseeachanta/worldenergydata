"""Scheduler monitoring: job execution logging, retry, status reporting, webhook."""
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional

from worldenergydata.scheduler.jobs.base import JobResult

logger = logging.getLogger(__name__)

try:
    import requests as requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]


class JobLogger:
    """Write structured JSON logs for each job run and rotate old logs."""

    def __init__(self, log_dir: str, retention_days: int) -> None:
        self.log_dir = Path(log_dir)
        self.retention_days = retention_days
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_result(self, result: JobResult) -> None:
        """Persist a JobResult as a JSON file.

        File is named: <timestamp>_<job_name>.json
        """
        timestamp = result.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{result.job_name}.json"
        log_path = self.log_dir / filename

        payload = {
            "job_name": result.job_name,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "status": result.status,
            "records_updated": result.records_updated,
            "error_msg": result.error_msg,
        }
        with log_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.debug("Job log written: %s", log_path)

    def rotate_logs(self) -> None:
        """Remove log files older than retention_days."""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = 0
        for log_file in self.log_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                log_file.unlink()
                removed += 1
                logger.debug("Rotated old log: %s", log_file)
        if removed:
            logger.info("Rotated %d old log file(s).", removed)


class RetryManager:
    """Run a callable with retry logic and exponential backoff."""

    def __init__(self, max_retries: int, backoff_seconds: float) -> None:
        self.max_retries = max(max_retries, 1)
        self.backoff_seconds = backoff_seconds

    def backoff_delay(self, attempt: int) -> float:
        """Return delay in seconds for the given attempt index (0-based).

        Delays double each attempt: backoff_seconds * 2^attempt.
        """
        return self.backoff_seconds * (2 ** attempt)

    def run_with_retry(self, job_fn: Callable[[], JobResult]) -> JobResult:
        """Call job_fn up to max_retries times; return last result.

        If job_fn raises an exception it is caught and treated as a failure.
        Retries stop early on success.
        """
        last_result: Optional[JobResult] = None
        for attempt in range(self.max_retries):
            try:
                result = job_fn()
                if result.status == "success":
                    return result
                last_result = result
            except Exception as exc:
                logger.warning(
                    "Job attempt %d/%d raised exception: %s",
                    attempt + 1,
                    self.max_retries,
                    exc,
                )
                from datetime import datetime as _dt

                now = _dt.now()
                last_result = JobResult(
                    job_name="unknown",
                    start_time=now,
                    end_time=now,
                    status="failure",
                    records_updated=0,
                    error_msg=str(exc),
                )

            if attempt < self.max_retries - 1:
                delay = self.backoff_delay(attempt)
                if delay > 0:
                    logger.info(
                        "Retrying in %.1f seconds (attempt %d/%d)...",
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(delay)

        return last_result  # type: ignore[return-value]


class StatusReporter:
    """Build summary reports and write status.json; post to webhook if configured."""

    def __init__(
        self,
        status_file: str,
        webhook_url: Optional[str] = None,
    ) -> None:
        self.status_file = Path(status_file)
        self.webhook_url = webhook_url

    def build_report(self, results: List[JobResult]) -> dict:
        """Compile a summary dict from a list of JobResults."""
        success = sum(1 for r in results if r.status == "success")
        failure = sum(1 for r in results if r.status == "failure")
        skipped = sum(1 for r in results if r.status == "skipped")

        jobs_detail = {}
        for r in results:
            jobs_detail[r.job_name] = {
                "status": r.status,
                "records_updated": r.records_updated,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat(),
                "error_msg": r.error_msg,
            }

        return {
            "total_jobs": len(results),
            "success_count": success,
            "failure_count": failure,
            "skipped_count": skipped,
            "generated_at": datetime.now().isoformat(),
            "jobs": jobs_detail,
        }

    def write_status(self, results: List[JobResult]) -> None:
        """Write status.json and optionally POST to webhook.

        Args:
            results: List of JobResults from the current scheduler cycle.
        """
        report = self.build_report(results)
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        with self.status_file.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Status written to %s", self.status_file)

        if self.webhook_url:
            self._post_webhook(report)

    def _post_webhook(self, report: dict) -> None:
        """POST the status report to the configured webhook URL."""
        if requests is None:  # pragma: no cover
            logger.warning("requests library not available; skipping webhook.")
            return
        try:
            response = requests.post(self.webhook_url, json=report, timeout=10)
            logger.info(
                "Webhook posted to %s, status=%d",
                self.webhook_url,
                response.status_code,
            )
        except Exception as exc:
            logger.warning("Webhook POST failed (non-fatal): %s", exc)
