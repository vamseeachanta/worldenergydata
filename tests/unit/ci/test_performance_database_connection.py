"""Connection setup retry contracts, with an independently advanced clock.

SQLite result-code semantics: https://www.sqlite.org/rescode.html (2026),
sections 2, 5 (ERROR=1, BUSY=5 and LOCKED=6). Python sqlite3 documentation (3.11),
sqlite_errorcode, documents that metadata is unavailable before Python 3.11.
The synthetic clock uses a three-second budget and one-second intervals:
attempts at t=0,1,2 have timeouts 3,2,1; at t=3 no budget remains.
These are hand-calculated test inputs, not production timing requirements.
"""

import sqlite3
import time
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from worldenergydata.testing.performance import database


@pytest.fixture
def setup_retry(monkeypatch, tmp_path):
    """Replace only the setup boundary; never wait on wall-clock timing."""
    db = object.__new__(database.PerformanceDatabase)
    db.db_path = tmp_path / "metrics.db"
    clock = SimpleNamespace(now=0.0)
    connections = []
    timeouts = []
    outcomes = []
    real_connect = sqlite3.connect

    def connect(path, *args, **kwargs):
        if path != str(db.db_path):
            return real_connect(path, *args, **kwargs)
        timeout = kwargs["timeout"]
        timeouts.append(timeout)
        outcome = outcomes.pop(0)
        if isinstance(outcome, tuple):
            raise outcome[0]
        conn = Mock()
        conn.execute.side_effect = outcome
        connections.append(conn)
        return conn

    def sleep(delay):
        assert delay > 0
        assert all(conn.close.called for conn in connections)
        clock.now += delay

    monkeypatch.setattr(database.sqlite3, "connect", connect)
    monkeypatch.setattr(
        database,
        "time",
        SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep),
        raising=False,
    )
    monkeypatch.setattr(database, "_CONNECTION_TIMEOUT", 3.0, raising=False)
    monkeypatch.setattr(database, "_CONNECTION_RETRY_INTERVAL", 1.0, raising=False)
    return SimpleNamespace(
        db=db,
        clock=clock,
        connections=connections,
        timeouts=timeouts,
        outcomes=outcomes,
    )


def _error(code=None, message="synthetic failure"):
    error = sqlite3.OperationalError(message)
    if code is not None:
        error.sqlite_errorcode = code
    return error


@pytest.mark.parametrize(
    "error",
    [
        _error(5),
        _error(6),
        # SQLite rescode.html section 2: low eight bits are the primary code.
        _error(5 | (1 << 8)),
        _error(6 | (1 << 8)),
        _error(message="database is locked"),
        _error(message="database table is locked"),
        _error(message="database schema is locked"),
    ],
)
def test_setup_retries_contention_and_closes_failed_connection(setup_retry, error):
    """One failed attempt + one successful attempt = two connections."""
    state = setup_retry
    state.outcomes[:] = [error, None]
    with state.db._get_connection() as conn:
        assert conn is state.connections[-1]
        assert conn.row_factory is sqlite3.Row
        assert not conn.close.called
    assert state.timeouts == [3.0, 2.0]
    assert all(conn.close.call_count == 1 for conn in state.connections)


def test_setup_retries_connect_failure(setup_retry):
    """A failed open owns no connection; only the successful open is closed."""
    state = setup_retry
    state.outcomes[:] = [(_error(5),), None]
    with state.db._get_connection():
        pass
    assert state.timeouts == [3.0, 2.0]
    assert len(state.connections) == 1
    state.connections[0].close.assert_called_once()


def test_retry_restores_full_transaction_busy_timeout(setup_retry):
    """Three seconds = 3000 ms, even after one second of setup retries.

    SQLite PRAGMA busy_timeout documentation (2026) specifies milliseconds;
    Python sqlite3.connect documentation (3.11) specifies seconds.
    """
    state = setup_retry
    state.outcomes[:] = [_error(5), None]
    with state.db._get_connection() as conn:
        conn.execute.assert_any_call("PRAGMA busy_timeout = 3000")
    assert state.timeouts == [3.0, 2.0]


def test_setup_stops_at_deadline(setup_retry):
    """Attempts t=0,1,2 fail; t=3 exhausts the three-second budget."""
    state = setup_retry
    error = _error(5)
    state.outcomes[:] = [error] * 3
    with pytest.raises(sqlite3.OperationalError) as raised, state.db._get_connection():
        pytest.fail("An unconfigured connection must never be yielded")
    assert raised.value is error
    assert state.timeouts == [3.0, 2.0, 1.0]
    assert state.clock.now == 3.0
    assert all(conn.close.call_count == 1 for conn in state.connections)


def test_setup_includes_sqlite_wait_in_deadline(setup_retry):
    """A three-second SQLite wait consumes all three seconds: one attempt."""
    state = setup_retry
    error = _error(5)

    def wait_then_fail(*args):
        state.clock.now += 3.0
        raise error

    state.outcomes[:] = [wait_then_fail]
    with pytest.raises(sqlite3.OperationalError) as raised, state.db._get_connection():
        pytest.fail("The elapsed SQLite wait must consume the retry budget")
    assert raised.value is error
    assert state.timeouts == [3.0]
    state.connections[0].close.assert_called_once()


def test_setup_clips_sleep_to_fractional_remaining_budget(setup_retry):
    """A 2.5 s SQLite wait leaves 3 - 2.5 = 0.5 s for the final sleep.

    Synthetic inputs use the fixture's three-second budget. Python 3.11
    time.monotonic documents elapsed-time differences; no real wait is used.
    After sleeping to t=3, no second connection may be opened.
    """
    state = setup_retry
    error = _error(5)

    def wait_then_fail(*args):
        state.clock.now += 2.5
        raise error

    state.outcomes[:] = [wait_then_fail]
    with pytest.raises(sqlite3.OperationalError) as raised, state.db._get_connection():
        pytest.fail("A final partial sleep must exhaust the setup budget")
    assert raised.value is error
    assert state.timeouts == [3.0]
    assert state.clock.now == 3.0
    state.connections[0].close.assert_called_once()


def test_setup_preserves_fractional_timeout_on_retry(setup_retry):
    """A 1.5 s wait plus a 1 s sleep leaves 3 - 1.5 - 1 = 0.5 s.

    These synthetic inputs verify that the remaining budget is not rounded
    up or reset. Python 3.11 sqlite3.connect specifies timeout in seconds.
    """
    state = setup_retry

    def wait_then_fail(*args):
        state.clock.now += 1.5
        raise _error(5)

    state.outcomes[:] = [wait_then_fail, None]
    with state.db._get_connection() as conn:
        assert conn is state.connections[-1]
    assert state.timeouts == [3.0, 0.5]
    assert state.clock.now == 2.5
    assert all(conn.close.call_count == 1 for conn in state.connections)


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit()])
def test_setup_interruption_closes_connection_without_retry(setup_retry, error):
    """An interruption propagates after one open and one close, with no sleep.

    Python 3.11 exceptions documents both interruptions under BaseException;
    neither is SQLite contention eligible for another setup attempt.
    """
    state = setup_retry
    state.outcomes[:] = [error]
    with pytest.raises(type(error)) as raised, state.db._get_connection():
        pytest.fail("An interrupted setup must never yield a connection")
    assert raised.value is error
    assert state.timeouts == [3.0]
    assert state.clock.now == 0.0
    state.connections[0].close.assert_called_once()


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit()])
def test_body_interruption_closes_connection_without_retry(setup_retry, error):
    """One yielded body interrupted once must close once and never replay.

    Python 3.11 contextlib.contextmanager documents propagation of exceptions
    from the with body back into the generator at its yield.
    """
    state = setup_retry
    state.outcomes[:] = [None]
    with pytest.raises(type(error)) as raised, state.db._get_connection():
        raise error
    assert raised.value is error
    assert state.timeouts == [3.0]
    assert state.clock.now == 0.0
    state.connections[0].close.assert_called_once()


def test_failed_record_rolls_back_metrics_and_statistics(monkeypatch, tmp_path):
    """An aborted insert leaves zero rows; one later success leaves one each.

    Independent calculation: (executions, statistics) starts at (0, 0), an
    uncommitted write followed by connection close rolls back to (0, 0), and
    one committed write gives (1, 1), with total_runs=total_passes=1.
    Source: Python 3.11 sqlite3, Transaction control: closing without commit
    loses pending changes. Timestamp and duration are synthetic record inputs.
    """
    db = database.PerformanceDatabase(tmp_path / "atomic.db")
    record = database.TestExecutionRecord(
        test_name="test_atomic_record",
        module="test_sample.py",
        duration=1.0,
        status="passed",
        timestamp=datetime.fromisoformat("2026-01-01T00:00:00"),
    )
    error = _error(5)
    update_statistics = db._update_statistics
    updates = []

    def update_then_fail(conn, execution):
        update_statistics(conn, execution)
        updates.append(execution)
        raise error

    monkeypatch.setattr(db, "_update_statistics", update_then_fail)
    with pytest.raises(sqlite3.OperationalError) as raised:
        db.record_execution(record)
    assert raised.value is error
    assert updates == [record]
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM test_executions").fetchone() == (0,)
        assert conn.execute("SELECT COUNT(*) FROM test_statistics").fetchone() == (0,)

    monkeypatch.setattr(db, "_update_statistics", update_statistics)
    db.record_execution(record)
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM test_executions").fetchone() == (1,)
        assert conn.execute("SELECT COUNT(*) FROM test_statistics").fetchone() == (1,)
        assert conn.execute(
            "SELECT total_runs, total_passes, total_failures FROM test_statistics"
        ).fetchone() == (1, 1, 0)


@pytest.mark.parametrize(
    "error",
    [
        _error(1, "database is locked"),
        _error(message="unable to open database file"),
        _error(message="disk I/O error"),
        _error(message="database is locked unexpectedly"),
        ValueError("invalid setup"),
    ],
)
def test_setup_does_not_retry_other_errors(setup_retry, error):
    """An unrelated failure consumes one attempt and no retry interval."""
    state = setup_retry
    state.outcomes[:] = [error]
    with pytest.raises(type(error)) as raised, state.db._get_connection():
        pytest.fail("A setup failure must propagate")
    assert raised.value is error
    assert state.timeouts == [3.0]
    assert state.clock.now == 0.0
    state.connections[0].close.assert_called_once()


def test_transaction_body_is_never_replayed(setup_retry):
    """A body failure yields once and closes once, without another open."""
    state = setup_retry
    state.outcomes[:] = [None]
    error = _error(5)
    with pytest.raises(sqlite3.OperationalError) as raised, state.db._get_connection():
        raise error
    assert raised.value is error
    assert state.timeouts == [3.0]
    assert state.clock.now == 0.0
    state.connections[0].close.assert_called_once()


def test_constructor_recovers_after_real_sqlite_lock(monkeypatch, tmp_path):
    """An exclusive lock blocks WAL; releasing it permits schema creation.

    SQLite busy-handler documentation (2026) permits immediate BUSY returns.
    Python sqlite3.connect documentation (3.11), timeout: zero waiting is a
    synthetic input here, forcing contention without a wall-clock race.
    One release callback is expected because the only lock is rolled back.
    """
    path = tmp_path / "locked.db"
    real_connect = sqlite3.connect
    holder = real_connect(path)
    attempts = []
    releases = []

    def connect(db_path, *, timeout):
        attempts.append(db_path)
        return real_connect(db_path, timeout=0.0)

    def release(delay):
        releases.append(delay)
        holder.rollback()

    holder.execute("BEGIN EXCLUSIVE")
    monkeypatch.setattr(database.sqlite3, "connect", connect)
    monkeypatch.setattr(
        database, "time", SimpleNamespace(monotonic=time.monotonic, sleep=release)
    )
    try:
        db = database.PerformanceDatabase(path)
        assert len(attempts) == 2  # One blocked open plus one successful retry.
        assert len(releases) == 1
        with db._get_connection() as conn:
            assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert {
                "test_executions",
                "test_statistics",
                "performance_trends",
            } <= tables
    finally:
        holder.close()
