# Test performance recording under SQLite contention

## Summary

Performance records are diagnostic. SQLite lock contention while recording a
metric emits a warning and drops that metric, preserving the pytest verdict.
The execution row and its statistics are committed together or discarded together.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-20 | Document fail-open recording and lock recovery to prevent diagnostic writes from changing test verdicts. |
| 1 | 2026-10-21 | Keep the lock example immediate after connection setup began restoring the write timeout. |
| 2 | 2026-10-24 | Limit suppression to lock contention so SQL and schema defects remain visible. |

## Storage and failure policy

The repository conftest creates each worker's default database in its own pytest
temporary directory. `--performance-db-path` keeps an explicitly selected path,
which can be shared. Connections retain the existing WAL mode and busy timeout
configured in `src/worldenergydata/testing/performance/database.py`.

WAL allows concurrent readers but still permits only a single writer; see
[SQLite Transaction, sections 2.1 and 2.2](https://sqlite.org/lang_transaction.html).
The [Python 3.11 sqlite3 connection reference](https://docs.python.org/3.11/library/sqlite3.html#sqlite3.connect)
defines `timeout` in seconds and the resulting `OperationalError` when a lock
cannot be acquired. A timeout reduces contention failures but cannot prevent them.

`record_execution` suppresses only lock-related `OperationalError` from connection
setup, insertion, statistics updates and commit, using the same contention
classifier as connection setup. Other operational errors, including SQL and
schema defects, propagate. The warning omits raw exception messages, database
paths and test payloads. Closing an uncommitted connection discards its pending
changes, as described by
[Python 3.11 Connection.close](https://docs.python.org/3.11/library/sqlite3.html#sqlite3.Connection.close).
A later metric can succeed once the competing transaction releases its lock.

Other exception classes remain visible. Database initialization, queries and
session-summary reads retain their existing error behavior. Dropped records make
diagnostic summaries incomplete; no cross-worker merge, retry queue or durable
metric delivery is provided. Test verdicts remain pytest's responsibility.

## Worked example

Inputs are a synthetic passed execution and a competing write transaction. The
example sets the test connection timeout to zero seconds to exercise the failure
immediately, following the `sqlite3.connect(timeout)` API cited above; production
timeout policy is unchanged. The example also overrides the connection budget
used to restore `PRAGMA busy_timeout` during setup. The duration is a chosen
synthetic input, with no timing acceptance limit.

Method: hold `BEGIN IMMEDIATE`, attempt a diagnostic write, roll back the competing
transaction, then record again. The independent row-count calculation is
`initial 0 + locked attempt 0 + successful attempt 1 = final 1`. Statistics must
likewise contain a single run. No elapsed-time measurement determines success.

```python
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from worldenergydata.testing.performance import PerformanceDatabase, TestExecutionRecord

connect = sqlite3.connect


def connect_without_wait(*args, **kwargs):
    # Python 3.11 sqlite3.connect(timeout), seconds: disable waiting in this example.
    # https://docs.python.org/3.11/library/sqlite3.html#sqlite3.connect
    kwargs["timeout"] = 0
    return connect(*args, **kwargs)


with TemporaryDirectory() as directory:
    db = PerformanceDatabase(Path(directory) / "example.db")
    record = TestExecutionRecord(
        test_name="test_example",
        module="test_example.py",
        duration=1.0,  # Chosen synthetic input; no duration threshold is checked.
        status="passed",
        timestamp=datetime.now(),
    )
    with patch("sqlite3.connect", side_effect=connect_without_wait), patch(
        "worldenergydata.testing.performance.database._CONNECTION_TIMEOUT", 0
    ):
        with closing(connect(db.db_path)) as holder:
            holder.execute("BEGIN IMMEDIATE")
            db.record_execution(record)  # Warns and drops the locked metric.
            holder.rollback()
        db.record_execution(record)
    with closing(connect(db.db_path)) as reader:
        rows = reader.execute("SELECT COUNT(*) FROM test_executions").fetchone()[0]
    runs = int(db.get_test_statistics().iloc[0]["total_runs"])
    assert rows == runs == 1  # Independent count calculation above.
    print(f"execution rows={rows}, statistics runs={runs}")
```

Answer: a warning for the locked attempt, followed by
`execution rows=1, statistics runs=1`.

## Regression coverage

`tests/unit/ci/test_performance_tracker_concurrency.py` checks real held locks,
connection and commit contention, rollback after statistics updates, recovery and
visibility of unrelated errors, including missing columns in the execution and
statistics tables. Copied-conftest subprocess tests keep a real lock
across report creation and assert both `pytest.ExitCode.OK` and
`pytest.ExitCode.TESTS_FAILED`, with no `INTERNALERROR`. Existing tests continue to
check worker isolation, WAL, busy timeout and lossless uncontended writes.
