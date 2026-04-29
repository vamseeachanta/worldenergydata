"""
Performance analysis for test execution metrics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .database import PerformanceDatabase


class PerformanceAnalyzer:
    """Analyze test performance metrics and trends."""

    def __init__(self, db: Optional[PerformanceDatabase] = None):
        """
        Initialize performance analyzer.

        Args:
            db: Performance database instance
        """
        self.db = db or PerformanceDatabase()

    def analyze_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze performance trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend analysis
        """
        trends = self.db.get_performance_trends(days)

        if trends.empty:
            return {"status": "no_data", "message": "No test execution data available"}

        # Calculate trend metrics
        trends = trends.sort_values("date")

        if len(trends) < 2:
            duration_trend = 0.0
            success_trend = 0.0
        else:
            # Duration trend
            duration_trend = np.polyfit(
                range(len(trends)), trends["avg_duration"].values, 1
            )[0]

            # Success rate trend
            success_trend = np.polyfit(
                range(len(trends)), trends["success_rate"].values, 1
            )[0]

        # Identify performance changes
        recent_avg = trends.tail(7)["avg_duration"].mean()
        historical_avg = (
            trends.head(len(trends) - 7)["avg_duration"].mean()
            if len(trends) > 7
            else recent_avg
        )

        performance_change = (
            ((recent_avg - historical_avg) / historical_avg * 100)
            if historical_avg > 0
            else 0
        )

        return {
            "status": "analyzed",
            "total_days": len(trends),
            "total_tests_run": int(trends["total_tests"].sum()),
            "avg_daily_tests": float(trends["total_tests"].mean()),
            "avg_test_duration": float(trends["avg_duration"].mean()),
            "duration_trend": "increasing" if duration_trend > 0 else "decreasing",
            "duration_trend_rate": float(duration_trend),
            "success_rate_trend": "improving" if success_trend > 0 else "declining",
            "success_rate_trend_rate": float(success_trend),
            "recent_performance_change": float(performance_change),
            "recent_avg_duration": float(recent_avg),
            "historical_avg_duration": float(historical_avg),
        }

    def identify_slow_tests(self, percentile: float = 90) -> pd.DataFrame:
        """
        Identify tests that are consistently slow.

        Args:
            percentile: Percentile threshold for slow tests

        Returns:
            DataFrame with slow test details
        """
        stats = self.db.get_test_statistics()

        if stats.empty:
            return pd.DataFrame()

        # Calculate percentile threshold
        threshold = stats["avg_duration"].quantile(percentile / 100)

        # Filter slow tests
        slow_tests = stats[stats["avg_duration"] > threshold].copy()

        # Add additional metrics
        slow_tests["slowness_factor"] = (
            slow_tests["avg_duration"] / stats["avg_duration"].median()
        )
        slow_tests["variability"] = (
            slow_tests["std_duration"] / slow_tests["avg_duration"]
        )

        # Sort by average duration
        slow_tests = slow_tests.sort_values("avg_duration", ascending=False)

        return slow_tests[
            [
                "test_name",
                "avg_duration",
                "std_duration",
                "slowness_factor",
                "variability",
                "total_runs",
            ]
        ]

    def detect_regressions(
        self, threshold_std: float = 2.0, lookback_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Detect tests with performance regressions.

        Args:
            threshold_std: Number of standard deviations for regression detection
            lookback_days: Days to look back for recent tests

        Returns:
            List of regression details
        """
        regressions = []

        # Get all test statistics
        stats = self.db.get_test_statistics()

        for _, test_stat in stats.iterrows():
            test_name = test_stat["test_name"]

            # Get recent history
            history = self.db.get_test_history(test_name, limit=50)

            if len(history) < 10:  # Need enough data for statistics
                continue

            # Filter to recent executions
            cutoff_date = datetime.now() - timedelta(days=lookback_days)
            recent = history[history["timestamp"] > cutoff_date]

            if recent.empty:
                continue

            # Calculate if recent performance is worse
            historical = history[history["timestamp"] <= cutoff_date]

            if not historical.empty:
                historical_mean = historical["duration"].mean()
                historical_std = historical["duration"].std()
                recent_mean = recent["duration"].mean()

                if recent_mean > historical_mean + (threshold_std * historical_std):
                    regressions.append(
                        {
                            "test_name": test_name,
                            "recent_avg": float(recent_mean),
                            "historical_avg": float(historical_mean),
                            "historical_std": float(historical_std),
                            "regression_factor": float(recent_mean / historical_mean),
                            "std_deviations": float(
                                (recent_mean - historical_mean) / historical_std
                            ),
                            "recent_runs": len(recent),
                            "historical_runs": len(historical),
                        }
                    )

        # Sort by regression factor
        regressions.sort(key=lambda x: x["regression_factor"], reverse=True)

        return regressions

    def analyze_test_stability(self, test_name: str) -> Dict[str, Any]:
        """
        Analyze stability of a specific test.

        Args:
            test_name: Name of the test

        Returns:
            Dictionary with stability metrics
        """
        history = self.db.get_test_history(test_name, limit=100)

        if history.empty:
            return {"status": "no_data", "test_name": test_name}

        # Calculate stability metrics
        durations = history[history["status"] != "skipped"]["duration"]

        if durations.empty:
            return {"status": "no_valid_runs", "test_name": test_name}

        # Coefficient of variation (lower is more stable)
        cv = durations.std() / durations.mean() if durations.mean() > 0 else 0

        # Failure rate
        total_runs = len(history)
        failures = len(history[history["status"] == "failed"])
        failure_rate = failures / total_runs * 100 if total_runs > 0 else 0

        # Recent trend
        recent_10 = durations.head(10)
        older = (
            durations.tail(len(durations) - 10) if len(durations) > 10 else durations
        )

        trend = "stable"
        if len(recent_10) > 0 and len(older) > 0:
            recent_mean = recent_10.mean()
            older_mean = older.mean()

            if recent_mean > older_mean * 1.2:
                trend = "degrading"
            elif recent_mean < older_mean * 0.8:
                trend = "improving"

        return {
            "status": "analyzed",
            "test_name": test_name,
            "total_runs": total_runs,
            "avg_duration": float(durations.mean()),
            "std_duration": float(durations.std()),
            "min_duration": float(durations.min()),
            "max_duration": float(durations.max()),
            "coefficient_of_variation": float(cv),
            "stability_score": max(0, 100 - (cv * 100)),  # Higher is better
            "failure_rate": float(failure_rate),
            "recent_trend": trend,
            "last_run": (
                history.iloc[0]["timestamp"].isoformat() if not history.empty else None
            ),
        }

    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for test suite optimization.

        Returns:
            List of optimization recommendations
        """
        recommendations = []

        # 1. Identify very slow tests
        slow_tests = self.identify_slow_tests(percentile=95)

        if not slow_tests.empty:
            top_slow = slow_tests.head(5)
            recommendations.append(
                {
                    "type": "slow_tests",
                    "priority": "high",
                    "title": "Optimize Slow Tests",
                    "description": f"Found {len(slow_tests)} tests in the 95th percentile for duration",  # noqa: E501
                    "tests": top_slow["test_name"].tolist(),
                    "potential_time_saved": float(
                        top_slow["avg_duration"].sum() * 0.3
                    ),  # Assume 30% improvement
                }
            )

        # 2. Identify flaky tests
        stats = self.db.get_test_statistics()
        if not stats.empty:
            flaky = stats[
                (stats["total_runs"] > 10)
                & (stats["success_rate"] < 95)
                & (stats["success_rate"] > 5)
            ]

            if not flaky.empty:
                recommendations.append(
                    {
                        "type": "flaky_tests",
                        "priority": "high",
                        "title": "Fix Flaky Tests",
                        "description": f"Found {len(flaky)} tests with inconsistent pass rates",
                        "tests": flaky["test_name"].tolist()[:5],
                        "impact": "Improving reliability and reducing false positives",
                    }
                )

        # 3. Identify candidates for parallelization
        if not stats.empty:
            independent_tests = stats[
                (stats["avg_duration"] > 0.1) & (stats["avg_duration"] < 1.0)
            ]

            if len(independent_tests) > 10:
                recommendations.append(
                    {
                        "type": "parallelization",
                        "priority": "medium",
                        "title": "Enable Parallel Execution",
                        "description": f"Found {len(independent_tests)} medium-duration tests suitable for parallelization",  # noqa: E501
                        "potential_time_saved": float(
                            independent_tests["avg_duration"].sum() * 0.5
                        ),  # Assume 50% improvement
                    }
                )

        # 4. Detect performance regressions
        regressions = self.detect_regressions()

        if regressions:
            recommendations.append(
                {
                    "type": "regressions",
                    "priority": "high",
                    "title": "Address Performance Regressions",
                    "description": f"Found {len(regressions)} tests with performance degradation",
                    "tests": [r["test_name"] for r in regressions[:5]],
                    "impact": "Recent changes may have introduced performance issues",
                }
            )

        # 5. Suggest test categorization
        if not stats.empty:
            total_duration = stats["avg_duration"].sum()

            if total_duration > 60:  # More than 1 minute total
                recommendations.append(
                    {
                        "type": "categorization",
                        "priority": "low",
                        "title": "Implement Test Categories",
                        "description": "Consider categorizing tests into smoke, integration, and full suites",  # noqa: E501
                        "impact": "Faster feedback loops for developers",
                    }
                )

        return recommendations

    def calculate_parallel_efficiency(self, num_workers: int = 4) -> Dict[str, Any]:
        """
        Calculate potential efficiency gains from parallelization.

        Args:
            num_workers: Number of parallel workers

        Returns:
            Dictionary with parallelization metrics
        """
        stats = self.db.get_test_statistics()

        if stats.empty:
            return {"status": "no_data"}

        # Current serial execution time
        serial_time = stats["avg_duration"].sum()

        # Simulate parallel execution
        # Sort tests by duration (longest first for better load balancing)
        sorted_tests = stats.sort_values("avg_duration", ascending=False)

        # Distribute tests across workers
        worker_loads = [0] * num_workers

        for _, test in sorted_tests.iterrows():
            # Assign to worker with minimum load
            min_worker = np.argmin(worker_loads)
            worker_loads[min_worker] += test["avg_duration"]

        # Parallel time is the maximum worker load
        parallel_time = max(worker_loads)

        # Calculate efficiency
        speedup = serial_time / parallel_time if parallel_time > 0 else 1
        efficiency = speedup / num_workers * 100

        return {
            "status": "calculated",
            "serial_execution_time": float(serial_time),
            "parallel_execution_time": float(parallel_time),
            "num_workers": num_workers,
            "speedup_factor": float(speedup),
            "efficiency_percentage": float(efficiency),
            "time_saved": float(serial_time - parallel_time),
            "worker_loads": [float(load) for load in worker_loads],
            "load_balance_ratio": (
                float(min(worker_loads) / max(worker_loads))
                if max(worker_loads) > 0
                else 1
            ),
        }
