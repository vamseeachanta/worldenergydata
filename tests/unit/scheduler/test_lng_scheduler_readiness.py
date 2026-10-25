"""LNG readiness regressions for the disable-until-implemented option in #458.

Expected results follow directly from the issue's acceptance criteria: an
unimplemented job is disabled, performs no collection or retries, contributes
no freshness row, and creates no success manifest. No engineering equations,
empirical constants, or upstream data values are used by these tests.
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from worldenergydata.scheduler.cli import _JOB_SPECS, _load_job_class, get_all_jobs
from worldenergydata.scheduler.config import load_config
from worldenergydata.scheduler.jobs.lng_terminals_refresh import LngTerminalsRefreshJob
from worldenergydata.scheduler.scheduler import DataScheduler

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "scheduler" / "scheduler_config.yml"


@pytest.fixture
def isolated_config(tmp_path):
    """Use the shipped job settings, routing all runtime output to temporary data."""
    config = yaml.safe_load(CONFIG_PATH.read_text())
    for job in config["jobs"]:
        job["output_dir"] = str(tmp_path / "data" / job["name"])
    config["monitoring"]["log_dir"] = str(tmp_path / "logs")
    config["monitoring"]["status_file"] = str(tmp_path / "status.json")
    config_dir = tmp_path / "config" / "scheduler"
    config_dir.mkdir(parents=True)
    path = config_dir / "scheduler_config.yml"
    path.write_text(yaml.safe_dump(config))
    return path


def test_unimplemented_lng_is_not_enabled_for_freshness():
    """Issue #458 permits disabling LNG until real refresh can report success."""
    config = load_config(str(CONFIG_PATH))
    lng = config.get_job_config(LngTerminalsRefreshJob.name)
    assert lng is not None
    assert lng["enabled"] is False
    assert lng not in config.get_enabled_jobs()
    assert lng["output_dir"] == "data/modules/lng_terminals"


def test_enabled_adapters_are_implemented():
    """Issue #458: every enabled default adapter must declare readiness.

    This checks adapter classes without running collectors or accessing data.
    Unimplemented adapters must opt out via ``implemented = False``.
    """
    config = load_config(str(CONFIG_PATH))
    classes = dict(_JOB_SPECS)
    for job in config.get_enabled_jobs():
        adapter = _load_job_class(classes[job["name"]])
        assert adapter.implemented, f"Disable unimplemented adapter {job['name']}"
    assert LngTerminalsRefreshJob.implemented is False


def test_direct_unimplemented_lng_fails_without_writing(tmp_path):
    """No upstream request implies zero updates and no freshness evidence (#458)."""
    output_dir = tmp_path / "lng"
    result = LngTerminalsRefreshJob().run({"output_dir": str(output_dir)})
    assert result.status == "failure"
    assert result.retryable is False
    assert result.records_updated == 0
    assert "not implemented" in result.error_msg
    assert "enabled: false" in result.error_msg
    assert not output_dir.exists()


@pytest.mark.parametrize("existing_manifest", [False, True])
@pytest.mark.parametrize("lazy", [False, True])
def test_enabled_unimplemented_lng_reports_failure_without_backoff(
    isolated_config, existing_manifest, lazy
):
    """An accidental enable must be visible as failure, never successful freshness.

    Independent trace: one adapter call, no sleeps, zero updated records;
    existing success evidence is unchanged (issue #458, linked issue #360).
    """
    config = yaml.safe_load(isolated_config.read_text())
    lng = next(j for j in config["jobs"] if j["name"] == LngTerminalsRefreshJob.name)
    lng["enabled"] = True
    isolated_config.write_text(yaml.safe_dump(config))
    output_dir = Path(lng["output_dir"])
    manifest = output_dir / "manifest.json"
    sentinel = '{"status": "success", "last_success_ts": "unchanged"}\n'
    if existing_manifest:
        output_dir.mkdir(parents=True)
        manifest.write_text(sentinel)

    scheduler = DataScheduler(str(isolated_config))
    job = (
        next(j for j in get_all_jobs() if j.name == LngTerminalsRefreshJob.name)
        if lazy
        else LngTerminalsRefreshJob()
    )
    scheduler.register_job(job)
    with (
        patch.object(job, "run", wraps=job.run) as run,
        patch("worldenergydata.scheduler.monitor.time.sleep") as sleep,
    ):
        result = scheduler.run_once(job.name)
    run.assert_called_once()
    sleep.assert_not_called()
    assert result.status == "failure"
    assert result.retryable is False
    assert result.records_updated == 0
    assert scheduler.status()["jobs"][job.name]["last_result"] == "failure"
    reported = json.loads(Path(config["monitoring"]["status_file"]).read_text())
    detail = reported["jobs"][job.name]
    assert detail["status"] == "failure"
    assert detail["retryable"] is False
    assert detail["error_msg"] == result.error_msg
    if existing_manifest:
        assert manifest.read_text() == sentinel
    else:
        assert not output_dir.exists()


def test_unimplemented_lng_is_not_scheduled(isolated_config):
    scheduler = DataScheduler(str(isolated_config))
    scheduler.register_job(LngTerminalsRefreshJob())

    scheduler._schedule_jobs()

    assert not scheduler._schedule.jobs


@pytest.mark.parametrize("existing_manifest", [False, True])
def test_disabled_lng_does_not_collect_retry_or_refresh_manifest(
    isolated_config, existing_manifest
):
    """No fetched records means zero updates; a previous manifest stays identical.

    The expected zero is the cardinality of the empty collection, independent
    of adapter implementation. The sentinel is deliberately not a timestamp.
    """
    scheduler = DataScheduler(str(isolated_config))
    job = LngTerminalsRefreshJob()
    scheduler.register_job(job)
    output_dir = Path(scheduler._config.get_job_config(job.name)["output_dir"])
    manifest = output_dir / "manifest.json"
    sentinel = '{"status": "success", "last_success_ts": "unchanged"}\n'
    if existing_manifest:
        output_dir.mkdir(parents=True)
        manifest.write_text(sentinel)

    with (
        patch.object(job, "run") as collect,
        patch.object(scheduler._retry_manager, "run_with_retry") as retry,
    ):
        result = scheduler.run_once(job.name)

    collect.assert_not_called()
    retry.assert_not_called()
    assert result.status == "skipped"
    assert result.records_updated == 0
    if existing_manifest:
        assert manifest.read_text() == sentinel
    else:
        assert not output_dir.exists()


def test_health_excludes_disabled_lng_with_no_manifest(isolated_config, tmp_path):
    """All enabled jobs lack manifests; LNG must not add a missing-manifest row.

    The expected stale count is hand counted as one missing manifest per enabled
    config entry, with no contribution from disabled entries (issue #458).
    """
    config = load_config(str(isolated_config))
    enabled_names = {job["name"] for job in config.get_enabled_jobs()}
    out_dir = tmp_path / "reports"
    env = os.environ.copy()
    env["REPO_ROOT"] = str(tmp_path)
    env["SCHEDULER_HEALTH_OUT_DIR"] = str(out_dir)
    env.pop("SCHEDULER_HEALTH_JOBS", None)
    result = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "cron" / "scheduler-health.sh")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        # Use the existing health-test subprocess guard; not a freshness limit.
        # Source: tests/cron/test_scheduler_health.py::_run (repository version).
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    (report,) = out_dir.glob("scheduler-health-*.md")
    body = report.read_text()
    assert LngTerminalsRefreshJob.name not in body
    for name in enabled_names:
        assert name in body
    count = len(enabled_names)
    assert f"{count} stale of {count} scheduler jobs" in body
    assert not Path(
        config.get_job_config(LngTerminalsRefreshJob.name)["output_dir"]
    ).exists()
