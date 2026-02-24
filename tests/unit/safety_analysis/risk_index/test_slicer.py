"""Tests for HSE Risk Index multi-dimensional slicer."""

import pandas as pd
import pytest

from worldenergydata.safety_analysis.risk_index.slicer import RiskSlicer


def _make_incidents(n: int, **overrides) -> pd.DataFrame:
    """Create a minimal incident DataFrame for testing."""
    base = {
        "incident_date": pd.date_range("2020-01-01", periods=n, freq="ME"),
        "severity": ["minor"] * n,
        "incident_type": ["violation"] * n,
        "description": ["test incident"] * n,
        "field_name": ["Field A"] * n,
        "water_depth_ft": [1000.0] * n,
        "fatalities": [0] * n,
        "injuries": [0] * n,
    }
    base.update(overrides)
    return pd.DataFrame(base)


class TestSliceByField:
    """Group incidents by field and compute per-field risk metrics."""

    def test_single_field_returns_one_row(self):
        df = _make_incidents(10, field_name=["Alpha"] * 10)
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        assert len(result) == 1
        assert result.iloc[0]["group_key"] == "Alpha"

    def test_two_fields_returns_two_rows(self):
        df = _make_incidents(10, field_name=["Alpha"] * 5 + ["Beta"] * 5)
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        assert len(result) == 2
        keys = set(result["group_key"])
        assert keys == {"Alpha", "Beta"}

    def test_incident_count_per_field(self):
        df = _make_incidents(15, field_name=["Alpha"] * 10 + ["Beta"] * 5)
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        alpha = result[result["group_key"] == "Alpha"].iloc[0]
        beta = result[result["group_key"] == "Beta"].iloc[0]
        assert alpha["total_incidents"] == 10
        assert beta["total_incidents"] == 5

    def test_empty_input_returns_empty(self):
        df = pd.DataFrame(columns=["field_name", "severity", "fatalities", "injuries"])
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        assert len(result) == 0

    def test_missing_field_name_grouped_as_unknown(self):
        df = _make_incidents(5, field_name=[None, "Alpha", None, "Alpha", None])
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        assert "Unknown" in result["group_key"].values


class TestSliceByWaterDepth:
    """Group incidents by water depth band."""

    def test_three_bands(self):
        depths = [200, 300, 1000, 2000, 6000, 8000]
        df = _make_incidents(6, water_depth_ft=depths)
        slicer = RiskSlicer()
        result = slicer.slice_by_water_depth(df)
        keys = set(result["group_key"])
        assert "shallow" in keys
        assert "mid" in keys
        assert "deep" in keys

    def test_shallow_boundary_at_500(self):
        df = _make_incidents(2, water_depth_ft=[500, 501])
        slicer = RiskSlicer()
        result = slicer.slice_by_water_depth(df)
        shallow = result[result["group_key"] == "shallow"]
        mid = result[result["group_key"] == "mid"]
        assert len(shallow) == 1
        assert shallow.iloc[0]["total_incidents"] == 1
        assert len(mid) == 1

    def test_missing_depth_classified_as_unknown(self):
        df = _make_incidents(3, water_depth_ft=[None, 1000, None])
        slicer = RiskSlicer()
        result = slicer.slice_by_water_depth(df)
        assert "unknown" in result["group_key"].values


class TestSliceByEra:
    """Group incidents by geological era."""

    def test_groups_by_era(self):
        df = _make_incidents(
            6,
            geological_era=["Oligocene", "Oligocene", "Eocene", "Eocene", "Paleocene", "Paleocene"],
        )
        slicer = RiskSlicer()
        result = slicer.slice_by_era(df)
        assert len(result) == 3

    def test_missing_era_classified_as_unknown(self):
        df = _make_incidents(3, geological_era=[None, "Eocene", None])
        slicer = RiskSlicer()
        result = slicer.slice_by_era(df)
        assert "Unknown" in result["group_key"].values

    def test_incident_count_per_era(self):
        df = _make_incidents(
            5,
            geological_era=["Oligocene", "Oligocene", "Oligocene", "Eocene", "Eocene"],
        )
        slicer = RiskSlicer()
        result = slicer.slice_by_era(df)
        oligo = result[result["group_key"] == "Oligocene"].iloc[0]
        eocene = result[result["group_key"] == "Eocene"].iloc[0]
        assert oligo["total_incidents"] == 3
        assert eocene["total_incidents"] == 2


class TestSliceMetrics:
    """Verify that sliced results contain required metric columns."""

    def test_has_required_columns(self):
        df = _make_incidents(10)
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        required = {"group_key", "group_type", "total_incidents", "fatalities",
                     "injuries", "fatality_rate", "injury_rate"}
        assert required.issubset(set(result.columns))

    def test_fatality_rate_computed(self):
        df = _make_incidents(10, fatalities=[1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        assert result.iloc[0]["fatality_rate"] == pytest.approx(0.1)

    def test_injury_rate_computed(self):
        df = _make_incidents(5, injuries=[1, 1, 0, 0, 0])
        slicer = RiskSlicer()
        result = slicer.slice_by_field(df)
        assert result.iloc[0]["injury_rate"] == pytest.approx(0.4)
