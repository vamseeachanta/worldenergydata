# Performance database concurrency

The performance tracker retries SQLite connection and WAL setup when concurrent
constructors encounter contention. The retry already exists in `database.py`;
the additional regression tests cover fractional deadlines, interruption cleanup
and rollback after recording fails. The original concurrent-writer assertions
remain unchanged.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| Initial | 2026-10-21 | Document retry boundaries and worked examples for the database-lock regression. |

## Retry contract

`PerformanceDatabase._get_connection()` retries only setup failures identified as
SQLite BUSY or LOCKED. Failed connections close before waiting. SQLite documents
that its busy handler can be bypassed, so setting a connection timeout alone
does not cover every contention failure [1]. Extended error codes retain the
primary result code in their low eight bits [2].

The existing connection budget and polling interval come from
`tests/unit/ci/test_performance_tracker_concurrency.py`: its busy-timeout assertion
and writer rendezvous define scheduling policies, rather than database
correctness limits. No new production timing policy is introduced here.

Setup uses a monotonic deadline [3]:

```text
deadline = starting_time + connection_budget
remaining = deadline - current_time
sleep_duration = min(polling_interval, remaining)
next_connection_timeout = deadline - time_after_sleep
```

Elapsed SQLite waiting and connection cleanup consume the same setup budget.
Exhaustion re-raises the last contention error. Successful setup restores the
full transaction busy timeout. Once a connection has been yielded, exceptions
from its body propagate and the connection closes; that body is never replayed.
`KeyboardInterrupt` and `SystemExit` also propagate after cleanup [4, 5].

## Worked examples

The following timing inputs are synthetic, chosen for direct hand calculation;
they are not acceptance limits or measurements. Expected values use elapsed-time
subtraction [3] and seconds as the SQLite connection-timeout unit [6]. These cases
are executable in `tests/unit/ci/test_performance_database_connection.py`.

| Input | Method | Expected answer |
| --- | --- | --- |
| Budget 3.0 s, polling interval 1.0 s, first SQLite attempt waits 2.5 s and fails | Remaining = 3.0 - 2.5 = 0.5 s; sleep the smaller of 1.0 s and 0.5 s | Sleep reaches the deadline; propagate the original error without another connection. |
| Same budget and interval; first attempt waits 1.5 s and fails | Remaining after sleep = 3.0 - 1.5 - 1.0 = 0.5 s | The next connection receives a 0.5 s timeout; successful setup yields once. |
| Setup or body raises an interruption | An interruption is not SQLite contention [4]; the context unwinds [5] | Close the opened connection once and propagate the original interruption without retry. |

The transaction example uses a synthetic passed execution with duration 1.0 s
and timestamp `2026-01-01T00:00:00`. Starting with an empty database, inject an
error after inserting both the execution and its statistics but before commit.
Connection close loses the pending changes [6]:

```text
Initially:                         executions = 0, statistics = 0
Failed uncommitted write + close:  executions = 0, statistics = 0
One subsequent committed write:   executions = 1, statistics = 1
Summary after that commit:        total_runs = 1, passes = 1, failures = 0
```

These independently counted outcomes verify that a recording failure does not
leave partial metrics or cause an implicit replay. The explicit subsequent call
is made by the test after checking the rollback.

## Regression checks

Run the connection test file, the collecting `tests/unit/ci` shard, and the
performance module tests with the normal repository fixtures enabled. When
working on an edited tree, `--allow-existing-tree-changes` records its initial
content and checks that testing preserves it. Send temporary output outside the
repository; `-o addopts=` avoids the default coverage report output for focused
runs. The test environment needs the performance package dependencies and
`pytest-xdist` so that the worker-isolation case runs.

Issue #1198 specifies 30 consecutive standalone passes of
`test_two_process_trackers_preserve_every_record` and 30 passes while collecting
the `unit-ci` shard. Use separate temporary bases for each invocation. The
unchanged test expects two writers each to record twelve executions:
`2 * 12 = 24` retained rows, with successful subprocess completion within the
issue's 120 s limit. Passing repetitions provide regression evidence; they do
not prove that every possible interleaving has been exercised.

Permanent contention can still exhaust the budget. Retrying transaction bodies,
dropping metrics, changing journal-mode fallback, and changing test assertions
are outside this regression coverage.

## Sources

1. SQLite, *Busy Handler*, retrieved 2026: [busy-handler behavior](https://www.sqlite.org/c3ref/busy_handler.html).
2. SQLite, *Result and Error Codes*, sections 2 and 5, retrieved 2026: [primary and extended codes](https://www.sqlite.org/rescode.html).
3. Python 3.11, *time*, `time.monotonic`: [elapsed-time differences](https://docs.python.org/3.11/library/time.html#time.monotonic).
4. Python 3.11, *Built-in Exceptions*, `KeyboardInterrupt` and `SystemExit`: [exception hierarchy](https://docs.python.org/3.11/library/exceptions.html).
5. Python 3.11, *contextlib*, `contextmanager`: [body exception propagation](https://docs.python.org/3.11/library/contextlib.html#contextlib.contextmanager).
6. Python 3.11, *sqlite3*, `connect`, `Connection.close` and *Transaction control*: [connection and transaction contracts](https://docs.python.org/3.11/library/sqlite3.html).
