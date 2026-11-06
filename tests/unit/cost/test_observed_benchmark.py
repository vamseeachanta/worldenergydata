"""Synthetic hand calculations for observed-cost calibration, never field data.

Metric basis: Forecasting: Principles and Practice, third edition (2021),
section 5.8, scale-dependent errors. All amounts below are arbitrary test
inputs in USD millions, with the arithmetic stated beside each assertion.
"""

from dataclasses import replace

import pytest

from worldenergydata.cost.calibration.observed_benchmark import (
    BenchmarkCell,
    BenchmarkProxy,
    BenchmarkStatus,
    benchmark_observed_costs,
)
from worldenergydata.cost.data_collection.calibration_schema import CostDataPoint


def observation(name="sample_a", cost=8.0, **changes):
    """Return a synthetic observation; no numeric input is a field estimate."""
    values = {
        "project_name": name,
        "operator": "synthetic_operator",
        "region": "synthetic_region",
        "water_depth_m": 1500.0,
        "water_depth_band": "deep",
        "well_depth_m": 5000.0,
        "well_depth_band": "deep",
        "year_sanction": 2020,
        "rig_type": "drillship",
        "activity_type": "drilling",
        "hpht": False,
        "subsea": "subsea",
        "cost_usd_mm": cost,
        "cost_type": "well_cost",
        "source": "Synthetic hand-calculation fixture, not engineering input",
        "confidence": "low",
    }
    return CostDataPoint(**(values | changes))


def compare(records, proxy=10.0, minimum_records=2):
    cell = BenchmarkCell.from_record(records[0])
    proxies = {cell: BenchmarkProxy(proxy, "Synthetic comparator fixture")}
    results = benchmark_observed_costs(
        records, proxies, minimum_records=minimum_records
    )
    return results[0]


def test_observed_mean_bias_and_proxy_rmse():
    """Costs 8,14 vs proxy 10: mean=11; bias=10%; RMSE=sqrt(10)."""
    result = compare([observation(cost=8), observation("sample_b", 14)])
    assert result.observed_mean_usd_mm == pytest.approx(11)
    assert result.bias_pct == pytest.approx(10)
    assert result.rmse_usd_mm == pytest.approx(10**0.5)
    assert result.selected_cost_usd_mm == pytest.approx(11)
    assert result.status == BenchmarkStatus.OBSERVED_MEAN
    assert result.n_records == 2
    assert result.proxy_cost_usd_mm == 10
    assert result.proxy_source == "Synthetic comparator fixture"
    assert result.observation_sources == (observation().source,)


def test_bias_sign_uses_proxy_as_denominator():
    """Costs 6,10 vs proxy 10: mean=8; bias=-20%; RMSE=sqrt(8)."""
    result = compare([observation(cost=6), observation("sample_b", 10)])
    assert result.bias_pct == pytest.approx(-20)
    assert result.rmse_usd_mm == pytest.approx(8**0.5)


def test_sparse_cell_preserves_proxy_and_reports_observed_metrics():
    """One cost 8 vs proxy 10: bias=-20%, RMSE=2, proxy retained."""
    result = compare([observation()], minimum_records=2)
    assert result.status == BenchmarkStatus.PROXY_FALLBACK
    assert result.selected_cost_usd_mm == 10
    assert result.observed_mean_usd_mm == 8
    assert result.bias_pct == pytest.approx(-20)
    assert result.rmse_usd_mm == pytest.approx(2)
    assert result.reason == "insufficient_records"


def test_threshold_is_caller_policy_not_a_confidence_label():
    """A caller threshold of one selects one cost; no confidence is inferred."""
    result = compare([observation()], minimum_records=1)
    assert result.status == BenchmarkStatus.OBSERVED_MEAN
    assert result.selected_cost_usd_mm == 8
    assert result.reason is None


@pytest.mark.parametrize(
    "change",
    [
        {"region": "other_region"},
        {"water_depth_band": "mid"},
        {"well_depth_band": "medium"},
        {"well_depth_band": None},
        {"rig_type": "semi_sub"},
        {"activity_type": "completion"},
        {"cost_type": "total_capex"},
        {"cost_type": "day_rate"},
        {"year_sanction": 2021},
        {"hpht": True},
        {"subsea": "dry_tree"},
    ],
)
def test_incompatible_cells_never_share_observation_counts(change):
    """Each differing basis is a singleton: neither reaches a threshold of two."""
    first = observation()
    second = observation("sample_b", 14, **change)
    proxies = {
        BenchmarkCell.from_record(record): BenchmarkProxy(10, "Synthetic basis")
        for record in [first, second]
    }
    results = benchmark_observed_costs([first, second], proxies, minimum_records=2)
    assert len(results) == 2
    assert all(result.n_records == 1 for result in results)
    assert all(result.status == BenchmarkStatus.PROXY_FALLBACK for result in results)


def test_missing_proxy_is_not_evaluated():
    """An observed cost alone establishes no comparison or calibrated selection."""
    result = benchmark_observed_costs([observation()], {}, minimum_records=1)[0]
    assert result.status == BenchmarkStatus.NOT_EVALUATED
    assert result.reason == "missing_proxy"
    assert result.observed_mean_usd_mm == 8
    assert result.n_records == 1
    assert result.selected_cost_usd_mm is None
    assert result.proxy_cost_usd_mm is None
    assert result.proxy_source is None
    assert result.bias_pct is None
    assert result.rmse_usd_mm is None


def test_proxy_only_cell_has_missing_metrics_instead_of_zero_error():
    """Zero observations retains the proxy; unknown error is distinct from zero."""
    cell = BenchmarkCell.from_record(observation())
    result = benchmark_observed_costs(
        [], {cell: BenchmarkProxy(10, "Synthetic basis")}, minimum_records=2
    )[0]
    assert result.status == BenchmarkStatus.PROXY_FALLBACK
    assert result.reason == "no_observations"
    assert result.n_records == 0
    assert result.selected_cost_usd_mm == 10
    assert result.observed_mean_usd_mm is None
    assert result.bias_pct is None
    assert result.rmse_usd_mm is None
    assert result.observation_sources == ()


def test_empty_inputs_return_empty_results():
    assert benchmark_observed_costs([], {}, minimum_records=1) == []


def test_sources_are_preserved_without_conferring_verification():
    """Two source references remain traceable; the fixture confidence stays low."""
    first = observation(source="Synthetic source A")
    second = observation("sample_b", 14, source="Synthetic source B")
    result = compare([first, second])
    assert result.observation_sources == ("Synthetic source A", "Synthetic source B")
    assert first.confidence == "low"


@pytest.mark.parametrize("minimum", [0, -1, 1.5, True, None])
def test_invalid_minimum_records_is_rejected(minimum):
    with pytest.raises(ValueError, match="minimum_records"):
        benchmark_observed_costs([], {}, minimum_records=minimum)


@pytest.mark.parametrize("cost", [0, -1, float("inf"), float("nan")])
def test_invalid_proxy_amounts_are_rejected(cost):
    with pytest.raises(ValueError, match="positive and finite"):
        BenchmarkProxy(cost, "Synthetic basis")


@pytest.mark.parametrize("source", ["", "   "])
def test_proxy_source_is_required(source):
    with pytest.raises(ValueError, match="source"):
        BenchmarkProxy(10, source)


@pytest.mark.parametrize("source", ["", "   "])
def test_observation_source_is_required_even_after_mutation(source):
    record = observation()
    record.source = source
    with pytest.raises(ValueError):
        benchmark_observed_costs([record], {}, minimum_records=1)


@pytest.mark.parametrize("cost", [0, -1, float("inf"), float("nan")])
def test_nonfinite_or_mutated_observation_is_rejected(cost):
    record = observation()
    record.cost_usd_mm = cost
    with pytest.raises(ValueError):
        benchmark_observed_costs([record], {}, minimum_records=1)


def test_duplicate_project_observations_cannot_inflate_cell_count():
    """Two citations for the same observation must not count as two projects."""
    first = observation()
    second = observation(source="Another citation for the same synthetic observation")
    with pytest.raises(ValueError, match="Duplicate"):
        compare([first, second])


def test_same_project_in_distinct_cost_basis_is_not_a_duplicate():
    first = observation()
    second = observation(cost_type="total_capex")
    results = benchmark_observed_costs([first, second], {}, minimum_records=1)
    assert len(results) == 2


def test_proxy_lookup_is_exact_and_inputs_are_not_modified():
    """Case and band differences are not aliases or inferred proxy matches."""
    record = observation()
    original = record.model_dump()
    other_cell = replace(BenchmarkCell.from_record(record), region="SYNTHETIC_REGION")
    proxies = {other_cell: BenchmarkProxy(10, "Synthetic basis")}
    results = benchmark_observed_costs([record], proxies, minimum_records=1)
    assert {result.reason for result in results} == {"missing_proxy", "no_observations"}
    assert record.model_dump() == original
    assert len(proxies) == 1


def test_large_finite_values_do_not_overflow_intermediate_sums():
    """Two equal costs at 1e308 have mean 1e308 and zero error against 1e308."""
    result = compare(
        [observation(cost=1e308), observation("sample_b", 1e308)], proxy=1e308
    )
    assert result.observed_mean_usd_mm == 1e308
    assert result.bias_pct == 0
    assert result.rmse_usd_mm == 0


def test_large_finite_rmse_avoids_overflow_before_normalization():
    """Four costs 1.5e308 vs 5e307: mean=1.5e308, bias=200%, RMSE=1e308."""
    records = [observation(f"sample_{index}", 1.5e308) for index in range(4)]
    result = compare(records, proxy=5e307)
    assert result.observed_mean_usd_mm == 1.5e308
    assert result.bias_pct == pytest.approx(200)
    assert result.rmse_usd_mm == pytest.approx(1e308)


@pytest.mark.parametrize("field", ["region", "operator", "project_name"])
def test_blank_observation_identity_is_rejected(field):
    with pytest.raises(ValueError, match="blank"):
        benchmark_observed_costs([observation(**{field: " "})], {}, minimum_records=1)


@pytest.mark.parametrize("value", [None, 10])
def test_untyped_proxy_values_are_rejected(value):
    cell = BenchmarkCell.from_record(observation())
    with pytest.raises(ValueError, match="BenchmarkProxy"):
        benchmark_observed_costs([], {cell: value}, minimum_records=1)
