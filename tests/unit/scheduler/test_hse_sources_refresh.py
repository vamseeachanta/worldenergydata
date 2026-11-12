# ABOUTME: Verify the monthly HSE scheduler adapter with an injected runner.
# ABOUTME: Cover explicit destinations, member row totals and terminal failures.

from pathlib import Path
from typing import Any

from worldenergydata.scheduler.jobs.hse_sources_refresh import HseSourcesRefreshJob


def test_skipped_without_output_dir() -> None:
    for config in ({}, {"output_dir": None}, {"output_dir": ""}):
        assert HseSourcesRefreshJob().run(config).status == "skipped"


def test_success(tmp_path: Path) -> None:
    calls = []
    def runner(config: Any, output_root: Path) -> dict:
        calls.append(output_root)
        return {"required_failures": [], "sources": [{"files": [
            {"members": [{"rows": 2}, {"rows": 3}, {"name": "readme"}]},
        ]}]}
    job = HseSourcesRefreshJob()
    job._runner = lambda: runner
    result = job.run({"output_dir": str(tmp_path)})
    assert result.status == "success"
    assert result.records_updated == 5
    assert calls == [tmp_path]


def test_required_failure(tmp_path: Path) -> None:
    job = HseSourcesRefreshJob()
    job._runner = lambda: lambda *args: {"required_failures": ["synthetic"], "sources": []}
    result = job.run({"output_dir": str(tmp_path)})
    assert result.status == "failure"
    assert result.retryable is False
    assert "synthetic" in result.error_msg


def test_registered_and_exported() -> None:
    from worldenergydata.scheduler.cli import ALL_JOBS
    from worldenergydata.scheduler.jobs import HseSourcesRefreshJob as exported

    assert exported is HseSourcesRefreshJob
    assert "hse_sources_refresh" in {job.name for job in ALL_JOBS}
