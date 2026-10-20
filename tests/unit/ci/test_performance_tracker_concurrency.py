"""Per-run tracker placement and lossless concurrent SQLite writes."""

import os
import shutil
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
from pathlib import Path

import pytest

from worldenergydata.testing.performance import PerformanceDatabase
from worldenergydata.testing.performance.database import (
    TestExecutionRecord as ExecutionRecord,
)

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


def _run_session(tmp_path, *args, source=None, expected_returncode=0):
    case = tmp_path / "case"
    case.mkdir()
    shutil.copyfile(REPO_ROOT / "tests/conftest.py", case / "conftest.py")
    (case / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (case / "test_sample.py").write_text(
        source
        or "import pytest\n"
        "@pytest.mark.parametrize('value', range(4))\n"
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
    assert result.returncode == expected_returncode, result.stdout + result.stderr
    assert "INTERNALERROR" not in result.stdout + result.stderr
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


def _sample_record():
    # Synthetic input; only row counts and transaction atomicity are asserted.
    return ExecutionRecord(
        test_name="test_sample",
        module="test_sample.py",
        duration=1.0,
        status="passed",
        timestamp=datetime.now(),
    )


def _disable_busy_wait(monkeypatch):
    connect = sqlite3.connect

    def immediate_connect(*args, **kwargs):
        # Python 3.11 sqlite3.connect(timeout), seconds: no wait for this test.
        # https://docs.python.org/3.11/library/sqlite3.html#sqlite3.connect
        kwargs["timeout"] = 0
        return connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", immediate_connect)


def test_locked_metric_is_dropped_and_next_write_recovers(
    tmp_path, monkeypatch, caplog
):
    """Hand calculation: 0 initial rows + 0 locked writes + 1 recovery = 1.

    SQLite Transaction, section 2.2 (https://sqlite.org/lang_transaction.html):
    BEGIN IMMEDIATE holds the sole writer slot, including in WAL mode.
    The holder remains open throughout the call; no sleep or timing race.
    """
    db = PerformanceDatabase(tmp_path / "locked.db")
    _disable_busy_wait(monkeypatch)
    with closing(sqlite3.connect(db.db_path)) as holder:
        holder.execute("BEGIN IMMEDIATE")
        try:
            db.record_execution(_sample_record())
            assert _record_count(db.db_path) == 0
        finally:
            holder.rollback()
    assert "Performance metric was not recorded" in caplog.text
    db.record_execution(_sample_record())
    assert _record_count(db.db_path) == 1
    assert db.get_test_statistics().iloc[0]["total_runs"] == 1


def test_failed_statistics_update_rolls_back_entire_metric(tmp_path, monkeypatch):
    """Hand calculation: 1 committed row + 0 aborted rows + 1 retry = 2.

    The injected error follows both INSERT and statistics UPDATE. Python 3.11
    sqlite3 Connection.close / transaction control documents that closing an
    uncommitted connection discards pending changes:
    https://docs.python.org/3.11/library/sqlite3.html#transaction-control
    """
    db = PerformanceDatabase(tmp_path / "atomic.db")
    record = _sample_record()
    db.record_execution(record)
    update = db._update_statistics

    def fail_after_update(conn, record):
        update(conn, record)
        raise sqlite3.OperationalError("injected statistics failure")

    with monkeypatch.context() as patch:
        patch.setattr(db, "_update_statistics", fail_after_update)
        db.record_execution(record)
    assert _record_count(db.db_path) == 1
    assert db.get_test_statistics().iloc[0]["total_runs"] == 1
    db.record_execution(record)
    assert _record_count(db.db_path) == 2
    assert db.get_test_statistics().iloc[0]["total_runs"] == 2


def test_commit_failure_discards_pending_metric(tmp_path, monkeypatch):
    """Hand calculation: initial 0 + aborted commit 0 + recovery 1 = 1.

    Connection.close discards pending changes without commit (Python 3.11):
    https://docs.python.org/3.11/library/sqlite3.html#sqlite3.Connection.close
    """
    db = PerformanceDatabase(tmp_path / "commit.db")
    connect = sqlite3.connect

    class FailedCommit(sqlite3.Connection):
        def commit(self):
            raise sqlite3.OperationalError("injected commit failure")

    def failing_connect(*args, **kwargs):
        return connect(*args, factory=FailedCommit, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", failing_connect)
        db.record_execution(_sample_record())
    assert _record_count(db.db_path) == 0
    assert db.get_test_statistics().empty
    db.record_execution(_sample_record())
    assert _record_count(db.db_path) == 1


def test_connection_operational_error_does_not_escape(tmp_path, monkeypatch, caplog):
    """An unavailable connection cannot insert any rows: initial 0 remains 0."""
    db = PerformanceDatabase(tmp_path / "connection.db")

    def unavailable(*args, **kwargs):
        raise sqlite3.OperationalError("injected connection failure")

    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, "connect", unavailable)
        db.record_execution(_sample_record())
    assert _record_count(db.db_path) == 0
    assert "Performance metric was not recorded" in caplog.text
    assert "injected connection failure" not in caplog.text


@pytest.mark.parametrize("error_type", [sqlite3.IntegrityError, ValueError])
def test_unexpected_errors_remain_visible(tmp_path, monkeypatch, error_type):
    """Only OperationalError is diagnostic; unrelated defects still raise."""
    db = PerformanceDatabase(tmp_path / "unexpected.db")

    def fail(conn, record):
        raise error_type("injected defect")

    monkeypatch.setattr(db, "_update_statistics", fail)
    with pytest.raises(error_type, match="injected defect"):
        db.record_execution(_sample_record())
    assert _record_count(db.db_path) == 0


LOCKED_TEST = """
import sqlite3
import pytest
import conftest

@pytest.fixture
def locked_tracker(request, monkeypatch):
    tracker = conftest._get_performance_tracker(request.config)
    connect = sqlite3.connect
    def immediate_connect(*args, **kwargs):
        # No wait: Python 3.11 sqlite3.connect(timeout), seconds.
        # https://docs.python.org/3.11/library/sqlite3.html#sqlite3.connect
        kwargs['timeout'] = 0
        return connect(*args, **kwargs)
    monkeypatch.setattr(sqlite3, 'connect', immediate_connect)
    holder = connect(tracker.db.db_path)
    holder.execute('BEGIN IMMEDIATE')
    try:
        yield
    finally:
        holder.rollback()
        holder.close()

def test_sample(locked_tracker):
    assert VERDICT
"""


@pytest.mark.parametrize("passed", [True, False])
def test_locked_metric_preserves_pytest_verdict(tmp_path, passed):
    """Pytest exit codes: OK=0, TESTS_FAILED=1 (pytest.ExitCode).

    Each subprocess holds a real writer lock across pytest's report hook.
    Both verdicts must survive; the locked diagnostic row count is zero.
    """
    expected = pytest.ExitCode.OK if passed else pytest.ExitCode.TESTS_FAILED
    _, run_temp = _run_session(
        tmp_path,
        source=LOCKED_TEST.replace("VERDICT", repr(passed)),
        expected_returncode=expected,
    )
    databases = list(run_temp.rglob(".test_performance.db"))
    assert len(databases) == 1
    assert _record_count(databases[0]) == 0
