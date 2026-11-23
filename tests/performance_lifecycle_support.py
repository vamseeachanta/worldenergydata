"""Subprocess assertions for the repository-level performance tracker."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SAMPLE_TEST = (
    "tests/unit/test_performance_tracking.py::"
    "TestPerformanceTrackerClass::test_tracker_initialization"
)


def _run_pytest(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    source_paths = [
        str(repo_root / "src"),
        str(repo_root.parent / "assetutilities/src"),
    ]
    if env.get("PYTHONPATH"):
        source_paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(source_paths)
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def assert_performance_tracker_lifecycle(tmp_path: Path, repo_root: Path) -> None:
    collect_db = tmp_path / "collect-only.db"
    collected = _run_pytest(
        repo_root,
        "--collect-only",
        "-q",
        "--performance-db-path",
        str(collect_db),
        SAMPLE_TEST,
    )
    assert collected.returncode == 0, collected.stdout + collected.stderr
    assert not collect_db.exists()

    deselected_db = tmp_path / "deselected.db"
    deselected = _run_pytest(
        repo_root,
        "-q",
        "-k",
        "no_test_can_match_this_expression",
        "--performance-db-path",
        str(deselected_db),
        SAMPLE_TEST,
    )
    assert deselected.returncode == 5, deselected.stdout + deselected.stderr
    assert not deselected_db.exists()

    session_db = tmp_path / "real-session.db"
    executed = _run_pytest(
        repo_root,
        "-q",
        "--performance-db-path",
        str(session_db),
        SAMPLE_TEST,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr
    assert session_db.exists()
    assert "Test Performance Summary" in executed.stdout
