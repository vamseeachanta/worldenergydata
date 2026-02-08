"""
ABOUTME: End-to-end tests for the latest analysis runner (WRK-010)
ABOUTME: Verifies full pipeline, comparisons, deviation flagging, and revenue
"""

import pytest

try:
    from worldenergydata.lower_tertiary.latest_runner import (
        compare_against_v30,
        run_classified_analysis,
        run_latest_analysis,
    )

    RUNNER_AVAILABLE = True
except ImportError:
    RUNNER_AVAILABLE = False

skip_no_runner = pytest.mark.skipif(
    not RUNNER_AVAILABLE, reason="latest_runner not importable"
)

V30_BASELINES = {
    "Jack St Malo": 406_571_771,
    "Stones": 83_657_789,
    "Julia": 70_936_158,
    "Big Foot": 66_870_656,
    "Cascade Chinook": 34_322_807,
    "Anchor": 6_912_846,
    "Shenandoah": 3_784,
}


@pytest.fixture(scope="module")
def latest_results():
    if not RUNNER_AVAILABLE:
        pytest.skip("latest_runner not available")
    return run_latest_analysis(end_date="2025-10-31")


@pytest.fixture(scope="module")
def comparison(latest_results):
    return compare_against_v30(latest_results)


@skip_no_runner
def test_end_to_end_runs(latest_results):
    assert "metadata" in latest_results
    assert "developments" in latest_results
    developments = latest_results["developments"]
    assert (
        len(developments) == 7
    ), f"Expected 7 producing fields, got {len(developments)}"
    assert "wti_source_summary" in latest_results["metadata"]


@skip_no_runner
def test_production_geq_v30(latest_results):
    devs = latest_results["developments"]
    for name, v30_total in V30_BASELINES.items():
        assert name in devs, f"{name} missing from latest results"
        actual = devs[name]["total_oil_bbl"]
        assert (
            actual >= v30_total
        ), f"{name}: {actual:,} BBL < V30 baseline {v30_total:,} BBL"


@skip_no_runner
def test_anchor_significant_increase(comparison):
    anchor = comparison["developments"]["Anchor"]
    assert anchor["is_significant"]
    assert anchor["delta_oil_pct"] > 50


@skip_no_runner
def test_shenandoah_significant_increase(comparison):
    shenandoah = comparison["developments"]["Shenandoah"]
    assert shenandoah["is_significant"]
    assert shenandoah["delta_oil_pct"] > 100


@skip_no_runner
def test_exploration_projects_unchanged(comparison):
    unchanged = comparison["exploration_unchanged"]
    for project in ("North Platte", "Kaskida", "Tiber"):
        assert project in unchanged, f"{project} not in exploration_unchanged"


@skip_no_runner
def test_deviation_flagging(comparison):
    deviations = comparison["deviations"]
    assert isinstance(deviations, list)
    assert len(deviations) >= 2, "Expected at least Anchor and Shenandoah deviations"
    required_keys = {"development", "delta_oil_pct", "explanation"}
    for entry in deviations:
        missing = required_keys - entry.keys()
        assert not missing, f"Deviation entry missing keys: {missing}"


@skip_no_runner
def test_revenue_uses_historical_wti(latest_results):
    devs = latest_results["developments"]
    assert devs["Anchor"]["total_revenue_usd"] > 0
    assert devs["Shenandoah"]["total_revenue_usd"] > 0
    assert (
        devs["Jack St Malo"]["total_revenue_usd"] > 25_000_000_000
    ), "Jack St Malo revenue should exceed V30 baseline of ~$25.6B"


@skip_no_runner
def test_metadata_completeness(latest_results):
    metadata = latest_results["metadata"]
    assert metadata["end_date"] == "2025-10-31"
    assert metadata["wti_source_summary"]["v30_xlsx"] > 470
    assert "time_period" in metadata


@skip_no_runner
def test_cascade_chinook_first_oil_correction(latest_results):
    """Cascade Chinook should reflect corrected first_oil=2012-09-01."""
    cc = latest_results["developments"]["Cascade Chinook"]
    assert cc["first_date"] == "2012-09-01"
    # Corrected total should be ~38.6M (vs V30 golden baseline 34.3M)
    assert cc["total_oil_bbl"] > 37_000_000
    assert cc["total_oil_bbl"] < 40_000_000


@pytest.fixture(scope="module")
def classified_results():
    if not RUNNER_AVAILABLE:
        pytest.skip("latest_runner not available")
    return run_classified_analysis(end_date="2025-10-31")


@skip_no_runner
def test_classified_analysis_structure(classified_results):
    """run_classified_analysis returns enriched results with classification data."""
    assert "metadata" in classified_results
    assert "classification" in classified_results["metadata"]
    devs = classified_results["developments"]
    assert len(devs) == 7
    for dev_name, dev_data in devs.items():
        assert "well_test_oil_bbl" in dev_data, f"{dev_name} missing well_test_oil_bbl"
        assert (
            "classification_summary" in dev_data
        ), f"{dev_name} missing classification_summary"


@skip_no_runner
def test_jsm_well_test_oil_detected(classified_results):
    """Jack St Malo should have non-zero well_test_oil_bbl."""
    jsm = classified_results["developments"]["Jack St Malo"]
    assert jsm["well_test_oil_bbl"] > 0
