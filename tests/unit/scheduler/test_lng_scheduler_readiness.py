"""LNG readiness regressions for the disable-until-implemented option in #458.

Expected results follow directly from the issue's acceptance criteria: an
unimplemented job is disabled, performs no collection or retries, contributes
no freshness row, and creates no success manifest. No engineering equations,
empirical constants, or upstream data values are used by these tests.
"""

import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

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
