"""Per-run tracker placement and lossless concurrent SQLite writes."""

import os
import shutil
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from worldenergydata.testing.performance import PerformanceDatabase

REPO_ROOT = Path(__file__).resolve().parents[3]


def _child_environment():
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "PYTEST_ADDOPTS"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")]
    )
    return env


def _run_session(tmp_path, *args):
    case = tmp_path / "case"
    case.mkdir()
    shutil.copyfile(REPO_ROOT / "tests/conftest.py", case / "conftest.py")
    (case / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (case / "test_sample.py").write_text(
        "import pytest\n@pytest.mark.parametrize('value', range(4))\n"
        "def test_sample(value):\n    assert value >= 0\n",
        encoding="utf-8",
    )
    run_temp = tmp_path / "run-temp"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            "pytest.ini",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={run_temp}",
            *args,
        ],
        cwd=case,
        env=_child_environment(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return case, run_temp


def _record_count(path):
    with sqlite3.connect(path) as conn:
        return conn.execute("SELECT COUNT(*) FROM test_executions").fetchone()[0]


def test_default_session_database_is_temporary(tmp_path):
    case, run_temp = _run_session(tmp_path)
    assert not list(case.glob(".test_performance.db*"))
    databases = list(run_temp.rglob(".test_performance.db"))
    assert len(databases) == 1
    assert sum(_record_count(path) for path in databases) == 4


def test_xdist_workers_use_separate_temporary_databases(tmp_path):
    pytest.importorskip("xdist", reason="Two-worker integration requires pytest-xdist")
    case, run_temp = _run_session(tmp_path, "-n", "2", "--dist=each")
    assert not list(case.glob(".test_performance.db*"))
    databases = list(run_temp.rglob(".test_performance.db"))
    assert len(databases) == 2
    assert len({path.parent for path in databases}) == 2
    assert sorted(_record_count(path) for path in databases) == [4, 4]


def test_explicit_database_path_is_preserved(tmp_path):
    case, run_temp = _run_session(tmp_path, "--performance-db-path=chosen.db")
    assert _record_count(case / "chosen.db") == 4
    assert not list(run_temp.rglob(".test_performance.db"))


def test_explicit_database_uses_wal(tmp_path):
    db = PerformanceDatabase(tmp_path / "explicit.db")
    with db._get_connection() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_explicit_database_has_busy_timeout(tmp_path):
    db = PerformanceDatabase(tmp_path / "explicit.db")
    with db._get_connection() as conn:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 30000


def test_unavailable_wal_keeps_effective_mode():
    db = PerformanceDatabase(Path(":memory:"))
    with db._get_connection() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "memory"


WRITER = """
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from worldenergydata.testing.performance import TestPerformanceTracker

root, worker = Path(sys.argv[1]), sys.argv[2]
(root / f'ready-{worker}').touch()
deadline = time.monotonic() + 30
while len(list(root.glob('ready-*'))) != 2:
    if time.monotonic() >= deadline:
        raise TimeoutError('Writer rendezvous exceeded 30 seconds')
    time.sleep(0.01)
tracker = TestPerformanceTracker(root / 'shared.db')
report = SimpleNamespace(passed=True, failed=False, skipped=False, keywords=["sample"], longrepr=None)
for number in range(12):
    nodeid = f'test_sample.py::test_{worker}_{number}'
    tracker.start_test(nodeid)
    tracker.end_test(nodeid, report)
"""


def test_two_process_trackers_preserve_every_record(tmp_path):
    """Both subprocesses must finish within 120 seconds and retain all 24 rows."""

    def write(worker):
        return subprocess.run(
            [sys.executable, "-c", WRITER, str(tmp_path), worker],
            cwd=tmp_path,
            env=_child_environment(),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, ("a", "b")))
    for result in results:
        assert result.returncode == 0, result.stdout + result.stderr
    assert _record_count(tmp_path / "shared.db") == 24
