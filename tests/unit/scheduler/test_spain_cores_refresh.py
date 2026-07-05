"""Tests for SpainCoresRefreshJob (scheduler adapter for CORES production)."""

from __future__ import annotations

import json
from pathlib import Path

from worldenergydata.scheduler.jobs.spain_cores_refresh import SpainCoresRefreshJob


class _FakeLoader:
    """No-network stand-in for CoresLiveProductionLoader."""

    instances: list["_FakeLoader"] = []
    row_count = 3

    def __init__(self, *, cache_root):
        self.cache_root = Path(cache_root)
        self.force_refresh = None
        self.refreshed = False
        _FakeLoader.instances.append(self)

    def refresh(self, *, force_refresh=False):
        self.refreshed = True
        self.force_refresh = force_refresh
        return self.metadata()

    def load_all_production(self):
        return [{"row": idx} for idx in range(self.row_count)]

    def load_oil_production(self):
        return [{"field_name": "Ayoluengo", "oil_bbl": 1.0}]

    def metadata(self):
        return {
            "statistics_page": "https://www.cores.es/en/estadisticas",
            "workbooks": {"oil": {"sha256": "abc123"}},
        }


class _BoomLoader(_FakeLoader):
    def refresh(self, *, force_refresh=False):
        raise RuntimeError("cores offline")


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
    assert calls == [
        {
            "oil_frame": [{"field_name": "Ayoluengo", "oil_bbl": 1.0}],
            "metadata": {
                "statistics_page": "https://www.cores.es/en/estadisticas",
                "workbooks": {"oil": {"sha256": "abc123"}},
            },
            "output_dir": fixture_dir,
        }
    ]


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


def test_loader_failure_is_retryable(tmp_path):
    result = _job(loader_cls=_BoomLoader).run({"output_dir": str(tmp_path)})

    assert result.status == "failure"
    assert result.records_updated == 0
    assert result.retryable is True
    assert "CORES refresh failed" in result.error_msg


def test_zero_rows_is_failure(tmp_path):
    _FakeLoader.row_count = 0

    result = _job().run({"output_dir": str(tmp_path)})

    assert result.status == "failure"
    assert result.records_updated == 0
    assert not (tmp_path / "_metadata.json").exists()


def test_registered_in_scheduler_registry():
    from worldenergydata.scheduler.cli import ALL_JOBS

    assert "spain_cores_refresh" in {job.name for job in ALL_JOBS}
