"""Tests for incident aggregation."""

import pandas as pd
import pytest

from worldenergydata.modules.safety_analysis.analysis.incident_aggregation import (
    aggregate_by_group,
    aggregate_by_severity,
    aggregate_by_time,
    compute_hurt_index,
    compute_time_series_hurt_index,
)


@pytest.fixture
def incidents_df():
    return pd.DataFrame(
        {
            "asset_id": ["RIG-001", "RIG-001", "RIG-002", "RIG-002", "RIG-001"],
            "occurred_at": pd.to_datetime(
                [
                    "2024-01-01",
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-03",
                    "2024-01-03",
                ]
            ),
            "actual_severity": ["no_hurt", "minor", "moderate", "minor", "severe"],
            "potential_severity": [
                "minor",
                "moderate",
                "severe",
                "moderate",
                "fatality",
            ],
            "work_activity": [
                "Drilling",
                "Pipe handling",
                "Drilling",
                "Lifting",
                "Drilling",
            ],
        }
    )


class TestAggregation:
    def test_aggregate_by_severity(self, incidents_df):
        result = aggregate_by_severity(incidents_df)
        assert "actual_severity" in result.columns
        assert "count" in result.columns
        assert result["count"].sum() == 5

    def test_aggregate_by_time(self, incidents_df):
        result = aggregate_by_time(incidents_df, freq="D")
        assert "occurred_at" in result.columns
        assert "count" in result.columns

    def test_aggregate_by_group(self, incidents_df):
        result = aggregate_by_group(incidents_df, ["work_activity"])
        assert result[result["work_activity"] == "Drilling"]["count"].iloc[0] == 3

    def test_compute_hurt_index(self, incidents_df):
        result = compute_hurt_index(incidents_df, "work_activity")
        assert "hurt_index" in result.columns
        drilling_idx = result[result["work_activity"] == "Drilling"]["hurt_index"].iloc[
            0
        ]
        # Drilling: no_hurt(0) + moderate(2) + severe(3) = 5
        assert drilling_idx == 5.0

    def test_compute_time_series_hurt_index(self, incidents_df):
        result = compute_time_series_hurt_index(incidents_df, freq="D")
        assert "actual_hurt_index" in result.columns
        assert "potential_hurt_index" in result.columns
        assert len(result) == 3  # 3 unique dates
