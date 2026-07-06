"""Tests for SpainCoresRefreshJob (scheduler adapter for CORES production)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from worldenergydata.scheduler.jobs.spain_cores_refresh import SpainCoresRefreshJob


class _FakeLoader:
    """No-network stand-in for CoresLiveProductionLoader."""

    instances: list["_FakeLoader"] = []
    row_count = 3

    def __init__(
        self,
        *,
        cache_root,
        oil_density_registry_path=None,
        allow_default_density=True,
    ):
        self.cache_root = Path(cache_root)
        self.oil_density_registry_path = (
            Path(oil_density_registry_path)
            if oil_density_registry_path is not None
            else None
        )
        self.allow_default_density = allow_default_density
        self.force_refresh = None
        self.refreshed = False
        _FakeLoader.instances.append(self)

    def refresh(self, *, force_refresh=False):
        self.refreshed = True
        self.force_refresh = force_refresh
        return self.metadata()

    def load_all_production(self):
        return pd.DataFrame({"row": list(range(self.row_count))})

    def load_oil_production(self):
        return pd.DataFrame([{"field_name": "Ayoluengo", "oil_bbl": 1.0}])

    def metadata(self):
        return {
            "statistics_page": "https://www.cores.es/en/estadisticas",
            "workbooks": {"oil": {"sha256": "abc123"}},
        }


class _BoomLoader(_FakeLoader):
    def refresh(self, *, force_refresh=False):
        raise RuntimeError("cores offline")


class _SourceErrorLoader(_FakeLoader):
    def refresh(self, *, force_refresh=False):
        from worldenergydata.spain.production import CoresSourceError

        raise CoresSourceError("statistics page missing workbook link")


class _DensityCoverageErrorLoader(_FakeLoader):
    def refresh(self, *, force_refresh=False):
        from worldenergydata.spain.production.cores_density import (
            CoresDensityCoverageError,
        )

        raise CoresDensityCoverageError("missing density factor for Casablanca")


class _AuditLoader(_FakeLoader):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.oil_conversion_audit = {"coverage_status": "complete"}


class _SidecarFileLoader(_FakeLoader):
    def load_all_production(self):
        normalized = self.cache_root / "normalized"
        normalized.mkdir(parents=True, exist_ok=True)
        (normalized / "cores_all_production.csv").write_text("field_name\nAyoluengo\n")
        (normalized / "cores_oil_density_factors.json").write_text(
            '{"coverage_status":"defaulted"}\n'
        )
        return super().load_all_production()


def _job(loader_cls=_FakeLoader, fixture_refresher=None):
    job = SpainCoresRefreshJob()
    job._loader_class = lambda: loader_cls
    if fixture_refresher is not None:
        job._fixture_refresher = lambda: fixture_refresher
    return job


def setup_function():
    _FakeLoader.instances.clear()
    _FakeLoader.row_count = 3


def test_missing_output_dir_is_skipped():
    result = SpainCoresRefreshJob().run({})

    assert result.status == "skipped"
    assert result.records_updated == 0


def test_success_refreshes_cores_and_writes_metadata(tmp_path):
    result = _job().run({"output_dir": str(tmp_path), "force_refresh": True})

    assert result.status == "success"
    assert result.records_updated == 3
    assert _FakeLoader.instances[0].cache_root == tmp_path
    assert _FakeLoader.instances[0].force_refresh is True

    metadata = json.loads((tmp_path / "_metadata.json").read_text())
    assert metadata["module"] == "spain_cores"
    assert metadata["record_count"] == 3
    assert metadata["format"] == "csv"


def test_refresh_metadata_separates_csv_files_from_sidecars(tmp_path):
    result = _job(loader_cls=_SidecarFileLoader).run({"output_dir": str(tmp_path)})

    assert result.status == "success"
    metadata = json.loads((tmp_path / "_metadata.json").read_text())
    assert metadata["files"] == ["normalized/cores_all_production.csv"]
    assert metadata["sidecar_files"] == ["normalized/cores_oil_density_factors.json"]
    assert metadata["file_count"] == 1
    assert metadata["sidecar_file_count"] == 1


def test_fixture_refresh_writes_to_configured_fixture_output(tmp_path):
    calls = []

    def fixture_refresher(*, oil_frame, metadata, output_dir):
        calls.append(
            {
                "oil_frame": oil_frame,
                "metadata": metadata,
                "output_dir": Path(output_dir),
            }
        )
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return object()

    fixture_dir = tmp_path / "fixtures" / "cores"

    result = _job(fixture_refresher=fixture_refresher).run(
        {
            "output_dir": str(tmp_path / "out"),
            "refresh_fixture": True,
            "fixture_output_dir": str(fixture_dir),
        }
    )

    assert result.status == "success"
    assert len(calls) == 1
    assert calls[0]["oil_frame"].to_dict("records") == [
        {"field_name": "Ayoluengo", "oil_bbl": 1.0}
    ]
    assert calls[0]["metadata"] == {
        "statistics_page": "https://www.cores.es/en/estadisticas",
        "workbooks": {"oil": {"sha256": "abc123"}},
    }
    assert calls[0]["output_dir"] == fixture_dir


def test_relative_fixture_output_resolves_from_scheduler_repo_root(tmp_path):
    calls = []

    def fixture_refresher(*, oil_frame, metadata, output_dir):
        calls.append(Path(output_dir))
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return object()

    repo_root = tmp_path / "repo"

    result = _job(fixture_refresher=fixture_refresher).run(
        {
            "output_dir": str(tmp_path / "out"),
            "refresh_fixture": True,
            "fixture_output_dir": "packages/worldenergydata-spain/src/worldenergydata/spain/data/cores",
            "_scheduler_repo_root": str(repo_root),
        }
    )

    assert result.status == "success"
    assert calls == [
        repo_root
        / "packages"
        / "worldenergydata-spain"
        / "src"
        / "worldenergydata"
        / "spain"
        / "data"
        / "cores"
    ]


def test_density_options_pass_to_loader_and_registry_path_resolves_from_repo_root(
    tmp_path,
):
    repo_root = tmp_path / "repo"
    registry_path = (
        "packages/worldenergydata-spain/src/worldenergydata/spain/data/cores/"
        "crude_density_factors.json"
    )

    result = _job().run(
        {
            "output_dir": str(tmp_path / "out"),
            "oil_density_registry_path": registry_path,
            "allow_default_density": False,
            "_scheduler_repo_root": str(repo_root),
        }
    )

    assert result.status == "success"
    loader = _FakeLoader.instances[0]
    assert loader.oil_density_registry_path == repo_root / registry_path
    assert loader.allow_default_density is False


def test_density_default_opt_in_must_be_boolean(tmp_path):
    result = _job().run(
        {
            "output_dir": str(tmp_path / "out"),
            "allow_default_density": "false",
        }
    )

    assert result.status == "failure"
    assert "allow_default_density" in result.error_msg


def test_refresh_fixture_false_disables_fixture_refresh(tmp_path):
    calls = []

    def fixture_refresher(*, oil_frame, metadata, output_dir):  # pragma: no cover
        calls.append(output_dir)
        return object()

    result = _job(fixture_refresher=fixture_refresher).run(
        {
            "output_dir": str(tmp_path),
            "refresh_fixture": False,
            "fixture_output_dir": str(tmp_path / "fixtures"),
        }
    )

    assert result.status == "success"
    assert calls == []


def test_fixture_refresh_receives_loader_oil_conversion_audit(tmp_path):
    calls = []

    def fixture_refresher(
        *, oil_frame, metadata, output_dir, oil_conversion_audit=None
    ):
        calls.append(oil_conversion_audit)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return object()

    result = _job(
        loader_cls=_AuditLoader,
        fixture_refresher=fixture_refresher,
    ).run(
        {
            "output_dir": str(tmp_path / "out"),
            "refresh_fixture": True,
            "fixture_output_dir": str(tmp_path / "fixtures"),
        }
    )

    assert result.status == "success"
    assert calls == [{"coverage_status": "complete"}]


def test_fixture_refresh_failure_is_reported_as_retryable_failure(tmp_path):
    def fixture_refresher(*, oil_frame, metadata, output_dir):
        raise RuntimeError("fixture write failed")

    result = _job(fixture_refresher=fixture_refresher).run(
        {
            "output_dir": str(tmp_path / "out"),
            "refresh_fixture": True,
            "fixture_output_dir": str(tmp_path / "fixtures"),
        }
    )

    assert result.status == "failure"
    assert result.records_updated == 0
    assert result.retryable is True
    assert "CORES refresh failed" in result.error_msg


def test_loader_failure_is_retryable(tmp_path):
    result = _job(loader_cls=_BoomLoader).run({"output_dir": str(tmp_path)})

    assert result.status == "failure"
    assert result.records_updated == 0
    assert result.retryable is True
    assert "CORES refresh failed" in result.error_msg


def test_source_validation_failure_is_not_retryable(tmp_path):
    result = _job(loader_cls=_SourceErrorLoader).run({"output_dir": str(tmp_path)})

    assert result.status == "failure"
    assert result.records_updated == 0
    assert result.retryable is False
    assert "statistics page missing workbook link" in result.error_msg


def test_density_coverage_failure_is_not_retryable(tmp_path):
    result = _job(loader_cls=_DensityCoverageErrorLoader).run(
        {"output_dir": str(tmp_path)}
    )

    assert result.status == "failure"
    assert result.records_updated == 0
    assert result.retryable is False
    assert "missing density factor for Casablanca" in result.error_msg


def test_zero_rows_is_failure(tmp_path):
    _FakeLoader.row_count = 0

    result = _job().run({"output_dir": str(tmp_path)})

    assert result.status == "failure"
    assert result.records_updated == 0
    assert not (tmp_path / "_metadata.json").exists()


def test_registered_in_scheduler_registry():
    from worldenergydata.scheduler.cli import ALL_JOBS

    assert "spain_cores_refresh" in {job.name for job in ALL_JOBS}
