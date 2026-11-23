"""Tests for marine_safety cause_statistics dataclasses and container methods."""

from datetime import date
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as scipy_stats

from worldenergydata.marine_safety.analysis.cause_statistics import (
    CrossTabulation,
    FrequencyDistribution,
    StatisticalSummary,
    TemporalTrend,
)
from worldenergydata.marine_safety.constants import CauseCategory, SeverityLevel

# ---------------------------------------------------------------------------
# FrequencyDistribution
# ---------------------------------------------------------------------------


class TestFrequencyDistribution:
    def test_init(self):
        df = pd.DataFrame(
            {"count": [10, 5], "percentage": [66.7, 33.3]},
            index=["human_error", "mechanical"],
        )
        dist = FrequencyDistribution(data=df, total_count=15)
        assert dist.total_count == 15
        assert dist.categories == []
        assert dist.metadata == {}

    def test_to_dict(self):
        df = pd.DataFrame(
            {"count": [10], "percentage": [100.0]},
            index=["human_error"],
        )
        dist = FrequencyDistribution(data=df, total_count=10)
        result = dist.to_dict()
        assert result["total_count"] == 10
        assert "human_error" in result["data"]
        assert result["categories"] == []

    def test_to_dict_with_categories(self):
        df = pd.DataFrame({"count": [5]}, index=["fire"])
        dist = FrequencyDistribution(
            data=df,
            total_count=5,
            categories=[CauseCategory.HUMAN_ERROR],
        )
        result = dist.to_dict()
        assert len(result["categories"]) == 1

    def test_to_csv(self, tmp_path):
        df = pd.DataFrame(
            {"count": [10, 5], "percentage": [66.7, 33.3]},
            index=["human_error", "mechanical"],
        )
        dist = FrequencyDistribution(data=df, total_count=15)
        filepath = tmp_path / "dist.csv"
        dist.to_csv(filepath)
        assert filepath.exists()
        content = filepath.read_text()
        assert "human_error" in content


# ---------------------------------------------------------------------------
# TemporalTrend
# ---------------------------------------------------------------------------


class TestTemporalTrend:
    def test_init(self):
        df = pd.DataFrame({"period": [202401], "count_fire": [3]})
        trend = TemporalTrend(
            data=df,
            period_type="month",
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        )
        assert trend.period_type == "month"
        assert trend.date_range[0] == date(2024, 1, 1)

    def test_to_dict(self):
        df = pd.DataFrame({"period": [2024], "count_fire": [5]})
        trend = TemporalTrend(
            data=df,
            period_type="year",
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        )
        result = trend.to_dict()
        assert result["period_type"] == "year"
        assert len(result["date_range"]) == 2

    def test_to_csv(self, tmp_path):
        df = pd.DataFrame({"period": [2024], "count_fire": [5]})
        trend = TemporalTrend(
            data=df,
            period_type="year",
            date_range=(date(2024, 1, 1), date(2024, 12, 31)),
        )
        filepath = tmp_path / "trend.csv"
        trend.to_csv(filepath)
        assert filepath.exists()


# ---------------------------------------------------------------------------
# CrossTabulation
# ---------------------------------------------------------------------------


class TestCrossTabulation:
    def _make_crosstab(self):
        data = pd.DataFrame(
            {1: [5, 3], 2: [10, 8], 3: [2, 1]},
            index=["human_error", "mechanical"],
        )
        row_totals = data.sum(axis=1)
        col_totals = data.sum(axis=0)
        grand_total = int(data.values.sum())
        return CrossTabulation(
            data=data,
            row_totals=row_totals,
            column_totals=col_totals,
            grand_total=grand_total,
        )

    def test_init(self):
        ct = self._make_crosstab()
        assert ct.grand_total == 29
        assert ct.row_totals["human_error"] == 17

    def test_to_dict(self):
        ct = self._make_crosstab()
        result = ct.to_dict()
        assert result["grand_total"] == 29
        assert "human_error" in result["row_totals"]
        assert "data" in result

    def test_to_csv(self, tmp_path):
        ct = self._make_crosstab()
        filepath = tmp_path / "crosstab.csv"
        ct.to_csv(filepath)
        assert filepath.exists()

    def test_chi_square_test(self):
        ct = self._make_crosstab()
        result = ct.chi_square_test()
        assert "chi2_statistic" in result
        assert "p_value" in result
        assert "degrees_of_freedom" in result
        assert "significant" in result
        assert isinstance(result["chi2_statistic"], float)
        assert isinstance(result["p_value"], float)
        assert result["degrees_of_freedom"] == 2


# ---------------------------------------------------------------------------
# StatisticalSummary
# ---------------------------------------------------------------------------


class TestStatisticalSummary:
    def _make_summary(self):
        return StatisticalSummary(
            total_incidents=100,
            total_causes=150,
            most_common_cause=CauseCategory.HUMAN_ERROR,
            least_common_cause=CauseCategory.UNKNOWN,
            date_range=(date(2020, 1, 1), date(2024, 12, 31)),
            severity_distribution={SeverityLevel.MINOR: 40, SeverityLevel.SERIOUS: 60},
            cause_distribution={
                CauseCategory.HUMAN_ERROR: 100,
                CauseCategory.UNKNOWN: 50,
            },
        )

    def test_init(self):
        summary = self._make_summary()
        assert summary.total_incidents == 100
        assert summary.total_causes == 150
        assert summary.most_common_cause == CauseCategory.HUMAN_ERROR

    def test_to_dict(self):
        summary = self._make_summary()
        result = summary.to_dict()
        assert result["total_incidents"] == 100
        assert result["total_causes"] == 150
        assert len(result["date_range"]) == 2
        assert len(result["severity_distribution"]) == 2
        assert len(result["cause_distribution"]) == 2

    def test_print_report(self, capsys):
        summary = self._make_summary()
        summary.print_report()
        captured = capsys.readouterr()
        assert "MARINE SAFETY INCIDENT CAUSE STATISTICAL SUMMARY" in captured.out
        assert "Total Incidents: 100" in captured.out
        assert "Total Cause Records: 150" in captured.out
