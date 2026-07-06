"""Spain CORES production refresh job.

This adapter keeps the official CORES oil/gas production cache fresh while
preserving scheduler startup as a cheap path. Spain package imports stay inside
runtime methods so CLI no-op paths do not import live-source clients.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, cast

from worldenergydata.scheduler.jobs.base import AbstractJob, JobResult

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR = Path("data/spain/cores")
_DEFAULT_FIXTURE_OUTPUT_DIR = Path(
    "packages/worldenergydata-spain/src/worldenergydata/spain/data/cores"
)


class SpainCoresConfigError(ValueError):
    """Raised for deterministic Spain CORES scheduler configuration errors."""


class SpainCoresRefreshJob(AbstractJob):
    """Refresh official Spain CORES monthly oil/gas production workbooks."""

    name = "spain_cores_refresh"
    default_output_dir = _DEFAULT_OUTPUT_DIR

    def _loader_class(self) -> type[Any]:
        """Return the live CORES loader class (overridden in tests)."""
        from worldenergydata.spain.production import CoresLiveProductionLoader

        return cast(type[Any], CoresLiveProductionLoader)

    def _fixture_refresher(self) -> Callable[..., Any]:
        """Return the Ayoluengo fixture refresher (overridden in tests)."""
        from worldenergydata.spain.production import refresh_ayoluengo_fixture

        return cast(Callable[..., Any], refresh_ayoluengo_fixture)

    def _is_retryable_exception(self, exc: Exception) -> bool:
        """Classify deterministic CORES source-contract failures."""
        if isinstance(exc, SpainCoresConfigError):
            return False
        deterministic_errors: list[type[Exception]] = []
        try:
            from worldenergydata.spain.production import CoresSourceError

            deterministic_errors.append(CoresSourceError)
        except Exception:
            pass
        try:
            from worldenergydata.spain.production.cores_density import (
                CoresDensityCoverageError,
            )

            deterministic_errors.append(CoresDensityCoverageError)
        except Exception:
            pass
        if not deterministic_errors:
            return True
        return not isinstance(exc, tuple(deterministic_errors))

    @staticmethod
    def _resolve_path(value: str | Path, repo_root: str | Path | None) -> Path:
        path = Path(value)
        if path.is_absolute() or repo_root is None:
            return path
        return Path(repo_root) / path

    def run(self, config: dict[str, Any]) -> JobResult:
        start = datetime.now()
        if "output_dir" not in config:
            return self._skipped_result(start)

        repo_root = config.get("_scheduler_repo_root")
        output_dir = self._resolve_path(config["output_dir"], repo_root)
        force_refresh = bool(config.get("force_refresh", False))

        try:
            loader = self._loader_class()(**self._loader_kwargs(config, output_dir))
            loader.refresh(force_refresh=force_refresh)
            production = loader.load_all_production()
            records_updated = len(production)

            if records_updated <= 0:
                error_msg = "CORES refresh produced 0 rows (download incomplete)"
                logger.error(error_msg)
                return self._failure_result(start, error_msg, retryable=True)

            if config.get("refresh_fixture", False):
                self._refresh_fixture(loader, config, repo_root)
        except Exception as exc:
            error_msg = f"CORES refresh failed: {exc}"
            logger.error(error_msg)
            return self._failure_result(
                start,
                error_msg,
                retryable=self._is_retryable_exception(exc),
            )

        self._write_refresh_metadata(output_dir, records_updated)
        logger.info(
            "Spain CORES refresh wrote %d production rows to %s",
            records_updated,
            output_dir,
        )
        return self._success_result(start, records_updated)

    def _loader_kwargs(
        self, config: dict[str, Any], output_dir: Path
    ) -> dict[str, Any]:
        repo_root = config.get("_scheduler_repo_root")
        kwargs: dict[str, Any] = {"cache_root": output_dir}
        registry_path = self._density_registry_path(config)
        if registry_path is not None:
            kwargs["oil_density_registry_path"] = self._resolve_path(
                registry_path,
                repo_root,
            )
        if "allow_default_density" in config:
            allow_default_density = config["allow_default_density"]
            if not isinstance(allow_default_density, bool):
                raise SpainCoresConfigError("allow_default_density must be boolean")
            kwargs["allow_default_density"] = allow_default_density
        return kwargs

    @staticmethod
    def _density_registry_path(config: dict[str, Any]) -> Any:
        primary = config.get("density_registry_path")
        legacy = config.get("oil_density_registry_path")
        if primary is not None and legacy is not None and str(primary) != str(legacy):
            raise SpainCoresConfigError(
                "density_registry_path conflicts with oil_density_registry_path"
            )
        return primary if primary is not None else legacy

    def _refresh_fixture(
        self,
        loader: Any,
        config: dict[str, Any],
        repo_root: str | Path | None,
    ) -> None:
        fixture_output_dir = self._resolve_path(
            config.get("fixture_output_dir", _DEFAULT_FIXTURE_OUTPUT_DIR),
            repo_root,
        )
        fixture_kwargs = {
            "oil_frame": loader.load_oil_production(),
            "metadata": loader.metadata(),
            "output_dir": fixture_output_dir,
        }
        oil_conversion_audit = getattr(loader, "oil_conversion_audit", None)
        if oil_conversion_audit is not None:
            fixture_kwargs["oil_conversion_audit"] = oil_conversion_audit
        self._fixture_refresher()(**fixture_kwargs)

    def _skipped_result(self, start: datetime) -> JobResult:
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="skipped",
            records_updated=0,
            error_msg="Spain CORES refresh requires an explicit output_dir",
        )

    def _success_result(self, start: datetime, records_updated: int) -> JobResult:
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="success",
            records_updated=records_updated,
            error_msg=None,
        )

    def _failure_result(
        self,
        start: datetime,
        error_msg: str,
        *,
        retryable: bool,
    ) -> JobResult:
        return JobResult(
            job_name=self.name,
            start_time=start,
            end_time=datetime.now(),
            status="failure",
            records_updated=0,
            error_msg=error_msg,
            retryable=retryable,
        )

    @staticmethod
    def _write_refresh_metadata(output_dir: Path, records_updated: int) -> None:
        """Write Spain CORES freshness metadata with the correct CSV format."""
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_files = sorted(
            p
            for p in output_dir.rglob("*")
            if p.is_file() and p.suffix.lower() == ".csv"
        )
        sidecar_files = sorted(
            p
            for p in output_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() == ".json"
            and p.name not in {"_metadata.json", "manifest.json"}
        )
        metadata = {
            "module": "spain_cores",
            "last_refresh": datetime.now(tz=timezone.utc).isoformat(),
            "record_count": records_updated,
            "file_count": len(csv_files),
            "sidecar_file_count": len(sidecar_files),
            "total_size_bytes": sum(
                p.stat().st_size for p in [*csv_files, *sidecar_files]
            ),
            "source_url": "https://www.cores.es/en/estadisticas",
            "format": "csv",
            "files": [str(p.relative_to(output_dir)) for p in csv_files],
            "sidecar_files": [str(p.relative_to(output_dir)) for p in sidecar_files],
        }
        (output_dir / "_metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n",
            encoding="utf-8",
        )
