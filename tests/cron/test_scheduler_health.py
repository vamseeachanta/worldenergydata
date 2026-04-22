"""Tests for scripts/cron/scheduler-health.sh — TDD per wed#309 plan."""

import json
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cron" / "scheduler-health.sh"


def _mk_manifest(path: Path, last_success_days_ago: int | None, refresh_days: int = 7):
    path.parent.mkdir(parents=True, exist_ok=True)
    if last_success_days_ago is None:
        data = {"refresh_interval_days": refresh_days}
    else:
        ts = time.time() - last_success_days_ago * 86400
        data = {
            "last_success_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts)),
            "refresh_interval_days": refresh_days,
        }
    path.write_text(json.dumps(data))


def _run(tmp_path: Path, jobs: dict[str, dict], env_extra: dict | None = None):
    """jobs: {name: {age: int_days_ago_or_None, interval: int_days}}."""
    out_dir = tmp_path / "out"
    jobs_root = tmp_path / "jobs"
    jobs_root.mkdir(parents=True, exist_ok=True)
    job_specs = []
    for name, spec in jobs.items():
        mpath = jobs_root / name / "manifest.json"
        _mk_manifest(mpath, spec.get("age"), spec.get("interval", 7))
        job_specs.append(f"{name}:{mpath}")

    env = os.environ.copy()
    env["SCHEDULER_HEALTH_OUT_DIR"] = str(out_dir)
    env["SCHEDULER_HEALTH_WEEK"] = "2026-W16"
    env["SCHEDULER_HEALTH_JOBS"] = ",".join(job_specs)
    env["REPO_ROOT"] = str(tmp_path)
    if env_extra:
        env.update(env_extra)
    r = subprocess.run(
        ["bash", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return r, out_dir / "scheduler-health-2026-W16.md"


def test_scheduler_green_when_all_fresh(tmp_path):
    r, report = _run(
        tmp_path,
        {
            "eia_weekly": {"age": 2, "interval": 7},
            "bsee_incidents": {"age": 1, "interval": 7},
        },
    )
    assert r.returncode == 0, r.stderr
    body = report.read_text()
    assert "Status:** GREEN" in body


def test_scheduler_yellow_on_one_stale(tmp_path):
    r, report = _run(
        tmp_path,
        {
            "eia_weekly": {"age": 2, "interval": 7},
            "bsee_incidents": {"age": 10, "interval": 7},  # 10d > 7d interval
        },
    )
    assert r.returncode == 0, r.stderr
    body = report.read_text()
    assert "Status:** YELLOW" in body
    assert "bsee_incidents" in body


def test_scheduler_red_on_multiple_stale(tmp_path):
    r, report = _run(
        tmp_path, {f"job_{i}": {"age": 20, "interval": 7} for i in range(4)}
    )
    assert r.returncode == 0, r.stderr
    body = report.read_text()
    assert "Status:** RED" in body


def test_scheduler_parses_manifest(tmp_path):
    r, report = _run(tmp_path, {"eia_weekly": {"age": 3, "interval": 7}})
    assert r.returncode == 0, r.stderr
    body = report.read_text()
    assert "eia_weekly" in body
    # The interval should appear in the row
    assert "7" in body


def test_scheduler_handles_missing_manifest(tmp_path):
    r, report = _run(tmp_path, {"never_ran": {"age": None, "interval": 7}})
    assert r.returncode == 0, r.stderr
    body = report.read_text()
    assert "never_ran" in body
    assert "never ran" in body.lower() or "never" in body.lower()


def test_scheduler_handles_first_run(tmp_path):
    """First run (no baseline) → cadence renders and exits 0."""
    r, report = _run(tmp_path, {"eia_weekly": {"age": 1, "interval": 7}})
    assert r.returncode == 0, r.stderr
    assert report.exists()
