"""
Performance database for storing test execution metrics.
"""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class TestExecutionRecord:
    """Record of a single test execution."""

    test_name: str
    module: str
    duration: float
    status: str  # passed, failed, skipped
    timestamp: datetime
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None
    error_message: Optional[str] = None
    test_size: Optional[str] = None  # small, medium, large
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.tags:
            data["tags"] = json.dumps(self.tags)
        return data


class PerformanceDatabase:
    """SQLite database for test performance metrics."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize performance database.

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path(".test_performance.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    module TEXT NOT NULL,
                    duration REAL NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    memory_usage REAL,
                    cpu_usage REAL,
                    error_message TEXT,
                    test_size TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for common queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_test_name
                ON test_executions(test_name)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON test_executions(timestamp)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_module
                ON test_executions(module)
            """
            )

            # Create summary statistics table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT UNIQUE NOT NULL,
                    total_runs INTEGER DEFAULT 0,
                    total_passes INTEGER DEFAULT 0,
                    total_failures INTEGER DEFAULT 0,
                    avg_duration REAL,
                    min_duration REAL,
                    max_duration REAL,
                    std_duration REAL,
                    last_run_timestamp TEXT,
                    last_run_status TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create performance trends table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_tests INTEGER,
                    total_duration REAL,
                    avg_duration REAL,
                    passed_tests INTEGER,
                    failed_tests INTEGER,
                    skipped_tests INTEGER,
                    slowest_test TEXT,
                    slowest_duration REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            """
            )

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get database connection context manager."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def record_execution(self, record: TestExecutionRecord):
        """
        Record a test execution.

        Args:
            record: Test execution record
        """
        with self._get_connection() as conn:
            data = record.to_dict()

            conn.execute(
                """
                INSERT INTO test_executions (
                    test_name, module, duration, status, timestamp,
                    memory_usage, cpu_usage, error_message, test_size, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data["test_name"],
                    data["module"],
                    data["duration"],
                    data["status"],
                    data["timestamp"],
                    data.get("memory_usage"),
                    data.get("cpu_usage"),
                    data.get("error_message"),
                    data.get("test_size"),
                    data.get("tags"),
                ),
            )

            # Update statistics
            self._update_statistics(conn, record)

            conn.commit()

    def _update_statistics(self, conn: sqlite3.Connection, record: TestExecutionRecord):
        """Update test statistics."""
        # Check if statistics exist for this test
        result = conn.execute(
            """
            SELECT * FROM test_statistics WHERE test_name = ?
        """,
            (record.test_name,),
        ).fetchone()

        if result:
            # Update existing statistics
            conn.execute(
                """
                UPDATE test_statistics
                SET total_runs = total_runs + 1,
                    total_passes = total_passes + ?,
                    total_failures = total_failures + ?,
                    last_run_timestamp = ?,
                    last_run_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE test_name = ?
            """,
                (
                    1 if record.status == "passed" else 0,
                    1 if record.status == "failed" else 0,
                    record.timestamp.isoformat(),
                    record.status,
                    record.test_name,
                ),
            )
        else:
            # Create new statistics entry
            conn.execute(
                """
                INSERT INTO test_statistics (
                    test_name, total_runs, total_passes, total_failures,
                    avg_duration, min_duration, max_duration,
                    last_run_timestamp, last_run_status
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.test_name,
                    1 if record.status == "passed" else 0,
                    1 if record.status == "failed" else 0,
                    record.duration,
                    record.duration,
                    record.duration,
                    record.timestamp.isoformat(),
                    record.status,
                ),
            )

        # Update duration statistics
        self._update_duration_stats(conn, record.test_name)

    def _update_duration_stats(self, conn: sqlite3.Connection, test_name: str):
        """Update duration statistics for a test."""
        result = conn.execute(
            """
            SELECT
                AVG(duration) as avg_duration,
                MIN(duration) as min_duration,
                MAX(duration) as max_duration,
                AVG(duration * duration) - AVG(duration) * AVG(duration) as variance
            FROM test_executions
            WHERE test_name = ? AND status != 'skipped'
        """,
            (test_name,),
        ).fetchone()

        if result:
            variance = result["variance"] or 0.0
            std_duration = float(max(variance, 0.0) ** 0.5)

            conn.execute(
                """
                UPDATE test_statistics
                SET avg_duration = ?,
                    min_duration = ?,
                    max_duration = ?,
                    std_duration = ?
                WHERE test_name = ?
            """,
                (
                    result["avg_duration"],
                    result["min_duration"],
                    result["max_duration"],
                    std_duration,
                    test_name,
                ),
            )

    def get_test_history(self, test_name: str, limit: int = 100) -> pd.DataFrame:
        """
        Get execution history for a test.

        Args:
            test_name: Name of the test
            limit: Maximum number of records to return

        Returns:
            DataFrame with test execution history
        """
        with self._get_connection() as conn:
            query = """
                SELECT * FROM test_executions
                WHERE test_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """

            df = pd.read_sql_query(query, conn, params=(test_name, limit))

            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            return df

    def get_slowest_tests(
        self, limit: int = 10, time_window: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get slowest tests.

        Args:
            limit: Number of tests to return
            time_window: Time window in days (None for all time)

        Returns:
            DataFrame with slowest tests
        """
        with self._get_connection() as conn:
            if time_window:
                query = """
                    SELECT
                        test_name,
                        module,
                        AVG(duration) as avg_duration,
                        MAX(duration) as max_duration,
                        COUNT(*) as execution_count
                    FROM test_executions
                    WHERE datetime(timestamp) > datetime('now', ? || ' days')
                        AND status != 'skipped'
                    GROUP BY test_name, module
                    ORDER BY avg_duration DESC
                    LIMIT ?
                """
                params = (-time_window, limit)
            else:
                query = """
                    SELECT
                        test_name,
                        module,
                        AVG(duration) as avg_duration,
                        MAX(duration) as max_duration,
                        COUNT(*) as execution_count
                    FROM test_executions
                    WHERE status != 'skipped'
                    GROUP BY test_name, module
                    ORDER BY avg_duration DESC
                    LIMIT ?
                """
                params = (limit,)

            return pd.read_sql_query(query, conn, params=params)

    def get_performance_trends(self, days: int = 30) -> pd.DataFrame:
        """
        Get performance trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            DataFrame with daily performance metrics
        """
        with self._get_connection() as conn:
            query = """
                SELECT
                    DATE(timestamp) as date,
                    COUNT(*) as total_tests,
                    SUM(duration) as total_duration,
                    AVG(duration) as avg_duration,
                    SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed_tests,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tests,
                    SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END) as skipped_tests,
                    MAX(duration) as max_duration
                FROM test_executions
                WHERE datetime(timestamp) > datetime('now', ? || ' days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """

            df = pd.read_sql_query(query, conn, params=(-days,))

            if not df.empty:
                df["date"] = pd.to_datetime(df["date"])
                df["success_rate"] = df["passed_tests"] / df["total_tests"] * 100

            return df

    def get_test_statistics(self) -> pd.DataFrame:
        """
        Get overall test statistics.

        Returns:
            DataFrame with test statistics
        """
        with self._get_connection() as conn:
            query = """
                SELECT * FROM test_statistics
                ORDER BY avg_duration DESC
            """

            df = pd.read_sql_query(query, conn)

            if not df.empty:
                df["success_rate"] = (
                    df["total_passes"] / df["total_runs"] * 100
                ).round(2)
                df["last_run_timestamp"] = pd.to_datetime(df["last_run_timestamp"])

            return df

    def detect_performance_regression(
        self, test_name: str, threshold: float = 1.5
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if a test has regressed in performance.

        Args:
            test_name: Name of the test
            threshold: Multiplier for standard deviation (default 1.5)

        Returns:
            Regression details if detected, None otherwise
        """
        with self._get_connection() as conn:
            # Compare the latest execution against prior history only. The
            # aggregate statistics table includes the latest run, which dilutes
            # large regressions and can hide exactly the slowdown being tested.
            rows = conn.execute(
                """
                SELECT duration, timestamp
                FROM test_executions
                WHERE test_name = ? AND status != 'skipped'
                ORDER BY timestamp DESC
            """,
                (test_name,),
            ).fetchall()

            if len(rows) < 2:
                return None

            recent = rows[0]
            historical_durations = [row["duration"] for row in rows[1:]]
            avg_duration = float(np.mean(historical_durations))
            std_duration = float(np.std(historical_durations, ddof=1))

            # A zero-variance history is still useful: any latest duration above
            # the mean by the configured multiplier is a regression when the
            # threshold is effectively the historical mean.
            upper_bound = avg_duration + (threshold * std_duration)

            if recent["duration"] > upper_bound:
                return {
                    "test_name": test_name,
                    "current_duration": recent["duration"],
                    "avg_duration": avg_duration,
                    "std_duration": std_duration,
                    "threshold": upper_bound,
                    "regression_factor": recent["duration"] / avg_duration,
                    "timestamp": recent["timestamp"],
                }

            return None

    def cleanup_old_records(self, days: int = 90):
        """
        Clean up old test execution records.

        Args:
            days: Number of days of history to keep
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                DELETE FROM test_executions
                WHERE datetime(timestamp) < datetime('now', ? || ' days')
            """,
                (-days,),
            )

            conn.commit()

            # Vacuum to reclaim space
            conn.execute("VACUUM")
