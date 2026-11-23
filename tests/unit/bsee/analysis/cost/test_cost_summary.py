# ABOUTME: Unit tests for WRK-019 cost summary module.
# ABOUTME: Covers field/lease/region aggregation, FieldCostSummary dataclass,
# ABOUTME: and graceful handling of empty DataFrames (LFS stubs).

"""Unit tests for worldenergydata.bsee.analysis.cost.cost_summary."""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.cost.cost_summary import (
    FieldCostSummary,
    summarize_field_costs,
    summarize_lease_costs,
    summarize_region_costs,
)
from worldenergydata.bsee.analysis.cost.models import (
    ActivityType,
    ConfidenceLevel,
    CostEstimate,
    WaterDepthBand,
    WellDepthBand,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_estimate(
    activity: ActivityType,
    region: str,
    cost_mm: float,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
) -> CostEstimate:
    return CostEstimate(
        activity_type=activity,
        region=region,
        water_depth_band=WaterDepthBand.DEEP,
        well_depth_band=WellDepthBand.MEDIUM,
        cost_usd_mm=cost_mm,
        cost_per_day_usd=400_000.0,
        duration_days=60.0,
        confidence=confidence,
        source="proxy_day_rate",
        year=2022,
    )


# ---------------------------------------------------------------------------
# TestFieldCostSummary
# ---------------------------------------------------------------------------


class TestFieldCostSummary:
    def test_construction_with_all_activities(self):
        drilling = _make_estimate(ActivityType.DRILLING, "gom", 100.0)
        completion = _make_estimate(ActivityType.COMPLETION, "gom", 40.0)
        intervention = _make_estimate(ActivityType.INTERVENTION, "gom", 10.0)
        summary = FieldCostSummary(
            field_name="Atlantis",
            region="gom",
            drilling_estimates=[drilling],
            completion_estimates=[completion],
            intervention_estimates=[intervention],
        )
        assert summary.total_drilling_cost_usd_mm == 100.0
        assert summary.total_completion_cost_usd_mm == 40.0
        assert summary.total_intervention_cost_usd_mm == 10.0

    def test_total_capex_sums_all_activities(self):
        drilling = _make_estimate(ActivityType.DRILLING, "gom", 100.0)
        completion = _make_estimate(ActivityType.COMPLETION, "gom", 40.0)
        intervention = _make_estimate(ActivityType.INTERVENTION, "gom", 10.0)
        summary = FieldCostSummary(
            field_name="Atlantis",
            region="gom",
            drilling_estimates=[drilling],
            completion_estimates=[completion],
            intervention_estimates=[intervention],
        )
        assert abs(summary.total_capex_usd_mm - 150.0) < 0.001

    def test_empty_estimates_returns_zero_totals(self):
        summary = FieldCostSummary(
            field_name="Stub Field",
            region="gom",
            drilling_estimates=[],
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert summary.total_drilling_cost_usd_mm == 0.0
        assert summary.total_completion_cost_usd_mm == 0.0
        assert summary.total_intervention_cost_usd_mm == 0.0
        assert summary.total_capex_usd_mm == 0.0

    def test_multiple_wells_aggregated(self):
        estimates = [
            _make_estimate(ActivityType.DRILLING, "gom", 80.0),
            _make_estimate(ActivityType.DRILLING, "gom", 120.0),
        ]
        summary = FieldCostSummary(
            field_name="Multi Well Field",
            region="gom",
            drilling_estimates=estimates,
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert abs(summary.total_drilling_cost_usd_mm - 200.0) < 0.001

    def test_well_count_tracked(self):
        estimates = [
            _make_estimate(ActivityType.DRILLING, "gom", 80.0),
            _make_estimate(ActivityType.DRILLING, "gom", 100.0),
            _make_estimate(ActivityType.DRILLING, "gom", 90.0),
        ]
        summary = FieldCostSummary(
            field_name="Three Well Field",
            region="gom",
            drilling_estimates=estimates,
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert summary.n_wells == 3

    def test_average_well_cost_computed(self):
        estimates = [
            _make_estimate(ActivityType.DRILLING, "gom", 90.0),
            _make_estimate(ActivityType.DRILLING, "gom", 110.0),
        ]
        summary = FieldCostSummary(
            field_name="Average Well",
            region="gom",
            drilling_estimates=estimates,
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert abs(summary.avg_well_cost_usd_mm - 100.0) < 0.001

    def test_confidence_summary_present(self):
        high = _make_estimate(ActivityType.DRILLING, "gom", 100.0, ConfidenceLevel.HIGH)
        low = _make_estimate(ActivityType.DRILLING, "gom", 80.0, ConfidenceLevel.LOW)
        summary = FieldCostSummary(
            field_name="Mixed Confidence",
            region="gom",
            drilling_estimates=[high, low],
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert summary.confidence_summary is not None
        assert (
            "high" in summary.confidence_summary or "low" in summary.confidence_summary
        )

    def test_to_dict_has_required_keys(self):
        drilling = _make_estimate(ActivityType.DRILLING, "gom", 100.0)
        summary = FieldCostSummary(
            field_name="Test Field",
            region="gom",
            drilling_estimates=[drilling],
            completion_estimates=[],
            intervention_estimates=[],
        )
        d = summary.to_dict()
        required = {
            "field_name",
            "region",
            "total_drilling_cost_usd_mm",
            "total_completion_cost_usd_mm",
            "total_intervention_cost_usd_mm",
            "total_capex_usd_mm",
            "n_wells",
        }
        assert required.issubset(set(d.keys()))


# ---------------------------------------------------------------------------
# TestSummarizeFieldCosts
# ---------------------------------------------------------------------------


class TestSummarizeFieldCosts:
    def test_returns_field_cost_summary(self):
        drilling = _make_estimate(ActivityType.DRILLING, "gom", 100.0)
        result = summarize_field_costs(
            field_name="Atlantis",
            region="gom",
            drilling_estimates=[drilling],
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert isinstance(result, FieldCostSummary)

    def test_empty_input_returns_zero_costs(self):
        result = summarize_field_costs(
            field_name="Empty Field",
            region="gom",
            drilling_estimates=[],
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert result.total_capex_usd_mm == 0.0

    def test_field_name_preserved(self):
        result = summarize_field_costs(
            field_name="Stones",
            region="gom",
            drilling_estimates=[],
            completion_estimates=[],
            intervention_estimates=[],
        )
        assert result.field_name == "Stones"


# ---------------------------------------------------------------------------
# TestSummarizeLeaseCosts
# ---------------------------------------------------------------------------


class TestSummarizeLeaseCosts:
    def test_returns_dict_keyed_by_lease(self):
        estimates_by_lease = {
            "G12345": [_make_estimate(ActivityType.DRILLING, "gom", 80.0)],
            "G67890": [_make_estimate(ActivityType.DRILLING, "gom", 90.0)],
        }
        result = summarize_lease_costs(
            estimates_by_lease=estimates_by_lease, region="gom"
        )
        assert isinstance(result, dict)
        assert "G12345" in result
        assert "G67890" in result

    def test_lease_summary_has_total_cost(self):
        estimates_by_lease = {
            "G12345": [_make_estimate(ActivityType.DRILLING, "gom", 80.0)],
        }
        result = summarize_lease_costs(
            estimates_by_lease=estimates_by_lease, region="gom"
        )
        assert result["G12345"]["total_cost_usd_mm"] == 80.0

    def test_empty_lease_dict_returns_empty_result(self):
        result = summarize_lease_costs(estimates_by_lease={}, region="gom")
        assert result == {}


# ---------------------------------------------------------------------------
# TestSummarizeRegionCosts
# ---------------------------------------------------------------------------


class TestSummarizeRegionCosts:
    def test_returns_dataframe(self):
        summaries = [
            FieldCostSummary(
                field_name="Field A",
                region="gom",
                drilling_estimates=[_make_estimate(ActivityType.DRILLING, "gom", 80.0)],
                completion_estimates=[],
                intervention_estimates=[],
            ),
            FieldCostSummary(
                field_name="Field B",
                region="gom",
                drilling_estimates=[
                    _make_estimate(ActivityType.DRILLING, "gom", 100.0)
                ],
                completion_estimates=[],
                intervention_estimates=[],
            ),
        ]
        result = summarize_region_costs(summaries)
        assert isinstance(result, pd.DataFrame)

    def test_dataframe_has_region_column(self):
        summaries = [
            FieldCostSummary(
                field_name="Field A",
                region="gom",
                drilling_estimates=[_make_estimate(ActivityType.DRILLING, "gom", 80.0)],
                completion_estimates=[],
                intervention_estimates=[],
            ),
        ]
        result = summarize_region_costs(summaries)
        assert "region" in result.columns

    def test_empty_summaries_returns_empty_dataframe(self):
        result = summarize_region_costs([])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
