"""Clock-independence of performance-database timestamp parsing.

``datetime.isoformat()`` omits the fractional part when ``microsecond == 0``.
A run whose ``datetime.now()`` lands on a whole second therefore stores
``2026-10-07T21:30:15`` beside rows such as ``2026-10-07T21:30:14.123456``.
``pd.to_datetime`` infers one format from the first row and raised
``ValueError`` on the other, failing ``pytest_sessionfinish`` in CI at random.

These tests inject both timestamp shapes instead of reading the clock, so the
failure reproduces deterministically.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from worldenergydata.testing.performance import (
    PerformanceDatabase,
    TestExecutionRecord,
)

WHOLE_SECOND = datetime(2026, 10, 7, 21, 30, 15)  # microsecond == 0
FRACTIONAL = datetime(2026, 10, 7, 21, 30, 16, 123456)


def _record(name: str, ts: datetime, duration: float) -> TestExecutionRecord:
    return TestExecutionRecord(
        test_name=name,
        module="tests/test_example.py",
        duration=duration,
        status="passed",
        timestamp=ts,
    )


def test_to_dict_keeps_fraction_for_whole_second_timestamp():
    stored = _record("t", WHOLE_SECOND, 1.0).to_dict()["timestamp"]
    assert stored == "2026-10-07T21:30:15.000000"


def test_statistics_parse_mixed_legacy_timestamp_shapes(tmp_path: Path):
    db = PerformanceDatabase(tmp_path / "perf.db")
    # Slower test sorts first (ORDER BY avg_duration DESC) and fixes the
    # inferred format to the fractional shape.
    db.record_execution(_record("test_slow", FRACTIONAL, 2.0))
    db.record_execution(_record("test_fast", FRACTIONAL, 1.0))
    # Simulate a row written by the pre-fix serializer (no fraction).
    with db._get_connection() as conn:
        conn.execute(
            "UPDATE test_statistics SET last_run_timestamp = ? WHERE test_name = ?",
            ("2026-10-07T21:30:15", "test_fast"),
        )
        conn.commit()

    stats = db.get_test_statistics()

    parsed = dict(zip(stats["test_name"], stats["last_run_timestamp"]))
    assert parsed["test_fast"] == pd.Timestamp(WHOLE_SECOND)
    assert parsed["test_slow"] == pd.Timestamp(FRACTIONAL)


def test_history_parses_mixed_legacy_timestamp_shapes(tmp_path: Path):
    db = PerformanceDatabase(tmp_path / "perf.db")
    db.record_execution(_record("test_x", FRACTIONAL, 1.0))
    db.record_execution(_record("test_x", WHOLE_SECOND, 1.0))
    with db._get_connection() as conn:
        conn.execute(
            "UPDATE test_executions SET timestamp = ? WHERE timestamp LIKE ?",
            ("2026-10-07T21:30:15", "2026-10-07T21:30:15%"),
        )
        conn.commit()

    history = db.get_test_history("test_x")

    assert set(history["timestamp"]) == {
        pd.Timestamp(WHOLE_SECOND),
        pd.Timestamp(FRACTIONAL),
    }
