"""
ABOUTME: Phase B V30 repeatability tests for lower tertiary BSEE field analysis
ABOUTME: Verifies OGOR production totals match Roy's V30 golden baseline (WRK-009)

Phase B: V30 Repeatability Tests

Verify that production totals from BSEE OGOR data match Roy's V30 golden baseline.
This is the first stage of repeatability -- production agreement is prerequisite
for financial calculation agreement.

WRK-009: Reproduce rev30 lower tertiary BSEE field results for repeatability
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

try:
    from worldenergydata.lower_tertiary.v30_reproducer import (
        load_ogor_production,
        load_v30_leases,
        reproduce_v30_production,
    )

    REPRODUCER_AVAILABLE = True
except ImportError:
    REPRODUCER_AVAILABLE = False


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_BASELINE_PATH = (
    PROJECT_ROOT / "config/analysis/lower_tertiary/golden_baseline_v30.yml"
)


@pytest.fixture(scope="module")
def golden_baseline():
    """Load golden baseline reference values."""
    with GOLDEN_BASELINE_PATH.open("r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def reproduced_production():
    """Run the V30 reproducer to get production from BSEE OGOR."""
    if not REPRODUCER_AVAILABLE:
        pytest.skip("V30 reproducer not available")
    return reproduce_v30_production()


# Golden baseline project IDs mapped to V30 development display names.
# Only developments with actual production (total_oil_bbl > 0) are listed.
PRODUCING_PROJECTS = {
    "jack_st_malo": "Jack St Malo",
    "stones": "Stones",
    "julia": "Julia",
    "big_foot": "Big Foot",
    "cascade_chinook": "Cascade Chinook",
    "anchor": "Anchor",
    "shenandoah": "Shenandoah",
}


class TestProductionReproducibility:
    """Compare BSEE OGOR production totals against V30 golden baseline."""

    @pytest.mark.parametrize("project_id,dev_name", list(PRODUCING_PROJECTS.items()))
    def test_total_oil_production_matches(
        self,
        golden_baseline,
        reproduced_production,
        project_id,
        dev_name,
    ):
        """Total oil production from OGOR matches V30 within tolerance."""
        baseline = golden_baseline["projects"][project_id]
        expected_oil = baseline["total_oil_bbl"]
        tol = golden_baseline["tolerances"]["production_relative"]

        if dev_name not in reproduced_production:
            pytest.fail(f"Development '{dev_name}' not found in OGOR data")

        actual_oil = reproduced_production[dev_name]["total_oil_bbl"]

        assert actual_oil == pytest.approx(expected_oil, rel=tol), (
            f"{dev_name}: OGOR oil {actual_oil:,.0f} vs V30 baseline "
            f"{expected_oil:,.0f} "
            f"(delta: {(actual_oil - expected_oil) / expected_oil * 100:+.2f}%)"
        )

    def test_all_producing_developments_found(self, reproduced_production):
        """All V30 producing developments found in OGOR data."""
        for dev_name in PRODUCING_PROJECTS.values():
            assert (
                dev_name in reproduced_production
            ), f"Development '{dev_name}' not found in OGOR data"


class TestProductionDiagnostics:
    """Diagnostic tests to help debug production mismatches."""

    def test_ogor_data_loads(self):
        """BSEE OGOR data can be loaded for a sample year range."""
        if not REPRODUCER_AVAILABLE:
            pytest.skip("V30 reproducer not available")
        ogor_df = load_ogor_production(start_year=2014, end_year=2015)
        assert len(ogor_df) > 0, "No OGOR data loaded"

    def test_v30_leases_load(self):
        """V30 leases.xlsx can be loaded with expected columns."""
        if not REPRODUCER_AVAILABLE:
            pytest.skip("V30 reproducer not available")
        leases_df = load_v30_leases()
        assert len(leases_df) > 0, "No leases loaded"
        assert "LEASE_NUM" in leases_df.columns
        assert "DEV_NAME" in leases_df.columns

    def test_lease_numbers_match_ogor(self):
        """V30 lease numbers exist in OGOR data."""
        if not REPRODUCER_AVAILABLE:
            pytest.skip("V30 reproducer not available")
        leases_df = load_v30_leases()
        ogor_df = load_ogor_production(start_year=2014, end_year=2015)

        v30_leases = set(leases_df["LEASE_NUM"])
        ogor_leases = set(ogor_df["LEASE_NUMBER"].unique())

        matched = v30_leases & ogor_leases
        assert len(matched) > 0, (
            f"No V30 leases found in OGOR data. "
            f"V30 sample: {sorted(v30_leases)[:5]}, "
            f"OGOR sample: {sorted(ogor_leases)[:5]}"
        )

    def test_golden_baseline_loads(self):
        """Golden baseline YAML loads with expected structure."""
        with GOLDEN_BASELINE_PATH.open("r") as f:
            baseline = yaml.safe_load(f)
        assert "projects" in baseline
        assert "tolerances" in baseline
        assert "production_relative" in baseline["tolerances"]
        for proj_id in PRODUCING_PROJECTS:
            assert (
                proj_id in baseline["projects"]
            ), f"Project '{proj_id}' missing from golden baseline"
