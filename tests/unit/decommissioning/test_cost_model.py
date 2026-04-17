# ABOUTME: Unit tests for decommissioning cost estimation model.
# ABOUTME: Covers parametric estimates, region multipliers, campaign totals, and cost aggregation.

"""Unit tests for worldenergydata.decommissioning.cost_model."""

import pytest

from worldenergydata.decommissioning.cost_model import (
    DecommissioningCostEstimate,
    DecommissioningCostEstimator,
)


@pytest.fixture()
def estimator() -> DecommissioningCostEstimator:
    return DecommissioningCostEstimator()


# ---------------------------------------------------------------------------
# Basic estimate returns correct type and positive cost
# ---------------------------------------------------------------------------


def test_estimate_returns_dataclass(estimator):
    result = estimator.estimate("jacket", 150, 1000, "gom")
    assert isinstance(result, DecommissioningCostEstimate)


def test_estimate_cost_positive_jacket(estimator):
    result = estimator.estimate("jacket", 150, 1000, "gom")
    assert result.estimated_cost_musd > 0


def test_estimate_cost_positive_well_pa(estimator):
    result = estimator.estimate("well_p_and_a", 200, 0, "gom")
    assert result.estimated_cost_musd > 0


def test_estimate_cost_positive_fpso(estimator):
    result = estimator.estimate("fpso", 500, 50000, "ncs")
    assert result.estimated_cost_musd > 0


def test_estimate_cost_positive_subsea_tree(estimator):
    result = estimator.estimate("subsea_tree", 1200, 0, "gom")
    assert result.estimated_cost_musd > 0


def test_estimate_cost_positive_pipeline(estimator):
    result = estimator.estimate("pipeline_km", 10, 0, "ukcs")
    assert result.estimated_cost_musd > 0


# ---------------------------------------------------------------------------
# Confidence is one of the valid values
# ---------------------------------------------------------------------------


def test_confidence_valid_values(estimator):
    valid = {"low", "medium", "high"}
    for asset_type in ("jacket", "well_p_and_a", "fpso", "subsea_tree", "pipeline_km"):
        result = estimator.estimate(asset_type, 100, 500, "gom")
        assert result.confidence in valid, f"Bad confidence for {asset_type}"


# ---------------------------------------------------------------------------
# Depth sensitivity: deeper water → higher cost (same asset + weight)
# ---------------------------------------------------------------------------


def test_deeper_water_costs_more_jacket(estimator):
    shallow = estimator.estimate("jacket", 100, 1000, "gom")
    deep = estimator.estimate("jacket", 500, 1000, "gom")
    assert deep.estimated_cost_musd > shallow.estimated_cost_musd


def test_deeper_water_costs_more_well_pa(estimator):
    shallow = estimator.estimate("well_p_and_a", 500, 0, "gom")
    deep = estimator.estimate("well_p_and_a", 3000, 0, "gom")
    assert deep.estimated_cost_musd > shallow.estimated_cost_musd


# ---------------------------------------------------------------------------
# Region multipliers
# ---------------------------------------------------------------------------


def test_ukcs_more_expensive_than_gom(estimator):
    gom = estimator.estimate("jacket", 150, 1000, "gom")
    ukcs = estimator.estimate("jacket", 150, 1000, "ukcs")
    assert ukcs.estimated_cost_musd > gom.estimated_cost_musd


def test_ncs_more_expensive_than_gom(estimator):
    gom = estimator.estimate("jacket", 150, 1000, "gom")
    ncs = estimator.estimate("jacket", 150, 1000, "ncs")
    assert ncs.estimated_cost_musd > gom.estimated_cost_musd


def test_brazil_more_expensive_than_gom(estimator):
    gom = estimator.estimate("jacket", 150, 1000, "gom")
    brazil = estimator.estimate("jacket", 150, 1000, "brazil")
    assert brazil.estimated_cost_musd > gom.estimated_cost_musd


def test_west_africa_more_expensive_than_gom(estimator):
    gom = estimator.estimate("jacket", 150, 1000, "gom")
    wa = estimator.estimate("jacket", 150, 1000, "west_africa")
    assert wa.estimated_cost_musd > gom.estimated_cost_musd


# ---------------------------------------------------------------------------
# Realistic cost ranges
# ---------------------------------------------------------------------------


def test_well_pa_realistic_range(estimator):
    # P&A cost should be $5–30M for a 1000m well
    result = estimator.estimate("well_p_and_a", 1000, 0, "gom")
    assert 5.0 <= result.estimated_cost_musd <= 30.0


def test_fpso_base_cost_exceeds_jacket(estimator):
    fpso = estimator.estimate("fpso", 200, 0, "gom")
    jacket = estimator.estimate("jacket", 200, 0, "gom")
    assert fpso.estimated_cost_musd > jacket.estimated_cost_musd


def test_subsea_tree_flat_cost(estimator):
    # Subsea tree has no depth or weight factor — cost is flat
    r1 = estimator.estimate("subsea_tree", 100, 0, "gom")
    r2 = estimator.estimate("subsea_tree", 2000, 500, "gom")
    assert r1.estimated_cost_musd == pytest.approx(r2.estimated_cost_musd, rel=0.01)


# ---------------------------------------------------------------------------
# Campaign and aggregation
# ---------------------------------------------------------------------------


def test_estimate_campaign_same_length(estimator):
    assets = [
        {
            "asset_type": "jacket",
            "water_depth_m": 100,
            "weight_tonnes": 800,
            "region": "gom",
        },
        {"asset_type": "well_p_and_a", "water_depth_m": 2000, "region": "gom"},
        {"asset_type": "pipeline_km", "water_depth_m": 15, "region": "ukcs"},
    ]
    results = estimator.estimate_campaign(assets)
    assert len(results) == len(assets)


def test_estimate_campaign_returns_estimates(estimator):
    assets = [
        {
            "asset_type": "fpso",
            "water_depth_m": 800,
            "weight_tonnes": 30000,
            "region": "brazil",
        },
    ]
    results = estimator.estimate_campaign(assets)
    assert isinstance(results[0], DecommissioningCostEstimate)


def test_total_cost_musd_equals_sum(estimator):
    assets = [
        {
            "asset_type": "jacket",
            "water_depth_m": 100,
            "weight_tonnes": 1000,
            "region": "gom",
        },
        {"asset_type": "well_p_and_a", "water_depth_m": 1500, "region": "ncs"},
    ]
    estimates = estimator.estimate_campaign(assets)
    expected = sum(e.estimated_cost_musd for e in estimates)
    assert estimator.total_cost_musd(estimates) == pytest.approx(expected, rel=1e-6)


def test_cost_by_region_returns_dict(estimator):
    assets = [
        {
            "asset_type": "jacket",
            "water_depth_m": 100,
            "weight_tonnes": 1000,
            "region": "gom",
        },
        {
            "asset_type": "jacket",
            "water_depth_m": 100,
            "weight_tonnes": 1000,
            "region": "ukcs",
        },
    ]
    estimates = estimator.estimate_campaign(assets)
    breakdown = estimator.cost_by_region(estimates)
    assert isinstance(breakdown, dict)
    assert "gom" in breakdown
    assert "ukcs" in breakdown


def test_cost_by_region_values_match_sum(estimator):
    assets = [
        {
            "asset_type": "jacket",
            "water_depth_m": 100,
            "weight_tonnes": 1000,
            "region": "gom",
        },
        {
            "asset_type": "jacket",
            "water_depth_m": 100,
            "weight_tonnes": 1000,
            "region": "gom",
        },
        {"asset_type": "well_p_and_a", "water_depth_m": 2000, "region": "ukcs"},
    ]
    estimates = estimator.estimate_campaign(assets)
    breakdown = estimator.cost_by_region(estimates)
    total_from_regions = sum(breakdown.values())
    assert total_from_regions == pytest.approx(
        estimator.total_cost_musd(estimates), rel=1e-5
    )


def test_invalid_asset_type_raises(estimator):
    with pytest.raises(ValueError):
        estimator.estimate("unknown_platform", 100, 500, "gom")


def test_invalid_region_raises(estimator):
    with pytest.raises(ValueError):
        estimator.estimate("jacket", 100, 500, "mars")


def test_data_source_is_parametric(estimator):
    result = estimator.estimate("jacket", 150, 1000, "gom")
    assert result.data_source == "parametric_estimate"


def test_year_is_stored(estimator):
    result = estimator.estimate("jacket", 150, 1000, "gom", year=2030)
    assert result.year == 2030
