"""Spain CORES production refresh job.

This adapter keeps the official CORES oil/gas production cache fresh while
preserving scheduler startup as a cheap path. Spain package imports stay inside
runtime methods so CLI no-op paths do not import live-source clients.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from worldenergydata.scheduler.jobs.base import (
    AbstractJob,
    JobResult,
    write_refresh_metadata,
)

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path("data/spain/cores")
_DEFAULT_FIXTURE_OUTPUT_DIR = Path(
    "packages/worldenergydata-spain/src/worldenergydata/spain/data/cores"
)


class SpainCoresRefreshJob(AbstractJob):
    """Refresh official Spain CORES monthly oil/gas production workbooks."""

    name = "spain_cores_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def _loader_class(self):
        """Return the live CORES loader class (overridden in tests)."""
        from worldenergydata.spain.production import CoresLiveProductionLoader

        return CoresLiveProductionLoader

    def _fixture_refresher(self) -> Callable[..., Any]:
        """Return the Ayoluengo fixture refresher (overridden in tests)."""
        from worldenergydata.spain.production import refresh_ayoluengo_fixture

        return refresh_ayoluengo_fixture

    @staticmethod
    def _resolve_path(value: str | Path, repo_root: str | Path | None) -> Path:
        path = Path(value)
        if path.is_absolute() or repo_root is None:
            return path
        return Path(repo_root) / path

    def run(self, config: dict) -> JobResult:
        start = datetime.now()
        if "output_dir" not in config:
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="skipped",
                records_updated=0,
                error_msg="Spain CORES refresh requires an explicit output_dir",
            )

        repo_root = config.get("_scheduler_repo_root")
        output_dir = self._resolve_path(config["output_dir"], repo_root)
        force_refresh = bool(config.get("force_refresh", False))

        try:
            loader = self._loader_class()(cache_root=output_dir)
            loader.refresh(force_refresh=force_refresh)
            production = loader.load_all_production()
            records_updated = len(production)
        except Exception as exc:
            error_msg = f"CORES refresh failed: {exc}"
            logger.error(error_msg)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=error_msg,
                retryable=True,
            )

        if records_updated <= 0:
            error_msg = "CORES refresh produced 0 rows (download incomplete)"
            logger.error(error_msg)
            return JobResult(
                job_name=self.name,
                start_time=start,
                end_time=datetime.now(),
                status="failure",
                records_updated=0,
                error_msg=error_msg,
                retryable=True,
            )

        if config.get("refresh_fixture", False):
            fixture_output_dir = self._resolve_path(
                config.get("fixture_output_dir", _DEFAULT_FIXTURE_OUTPUT_DIR),
                repo_root,
            )
            self._fixture_refresher()(
                oil_frame=loader.load_oil_production(),
                metadata=loader.metadata(),
                output_dir=fixture_output_dir,
            )

        write_refresh_metadata("spain_cores", output_dir, records_updated)
        logger.info(
            "Spain CORES refresh wrote %d production rows to %s",
            records_updated,
            output_dir,
        )
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="success",
            records_updated=records_updated,
            error_msg=None,
        )
