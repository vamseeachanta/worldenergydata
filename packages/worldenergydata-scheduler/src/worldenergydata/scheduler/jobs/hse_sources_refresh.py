# ABOUTME: Schedule configuration-driven monthly collection of public HSE sources.
# ABOUTME: Count archive rows and report required failures without automatic retries.

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult


class HseSourcesRefreshJob(AbstractJob):
    """Collect public HSE sources into an explicitly configured destination."""

    name = "hse_sources_refresh"

    def _runner(self) -> Callable[..., dict]:
        """Build the runner lazily; tests replace this hook without network IO."""
        from worldenergydata.hse.monthly_refresh import run_refresh

        return run_refresh

    def _config_path(self, config: dict) -> Path:
        if config.get("sources_config"):
            return Path(config["sources_config"])
        for parent in Path(__file__).resolve().parents:
            candidate = parent / "config/hse/monthly_sources.yml"
            if candidate.is_file():
                return candidate
        raise ValueError("supply sources_config for an installed distribution")

    def run(self, config: dict) -> JobResult:
        start = datetime.now()
        if not config.get("output_dir"):
            return JobResult(self.name, start, datetime.now(), "skipped", 0,
                             "HSE source refresh requires an explicit output_dir")
        try:
            from worldenergydata.hse.monthly_refresh import load_config

            summary = self._runner()(load_config(self._config_path(config)),
                                     Path(config["output_dir"]))
            rows = sum(member.get("rows", 0) for source in summary["sources"]
                       for file in source.get("files", []) for member in file.get("members", []))
            failures = summary["required_failures"]
            error = "Required HSE sources failed: " + ", ".join(failures) if failures else None
            return JobResult(self.name, start, datetime.now(), "failure" if failures else "success",
                             rows, error, retryable=False)
        except Exception as exc:
            return JobResult(self.name, start, datetime.now(), "failure", 0,
                             f"HSE source refresh failed: {exc}", retryable=False)
