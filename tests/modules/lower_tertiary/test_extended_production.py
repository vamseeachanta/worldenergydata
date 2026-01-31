"""
ABOUTME: Tests for extended production window beyond V30 baseline (WRK-010)
ABOUTME: Verifies parameterized reproduce_v30_production with end_date through Oct 2025
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

try:
    from worldenergydata.analysis.lower_tertiary.v30_reproducer import (
        reproduce_v30_production,
    )

    REPRODUCER_AVAILABLE = True
except ImportError:
    REPRODUCER_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_BASELINE_PATH = (
    PROJECT_ROOT / "config/analysis/lower_tertiary/golden_baseline_v30.yml"
)

# Golden baseline project IDs mapped to V30 development display names.
PRODUCING_PROJECTS = {
    "jack_st_malo": "Jack St Malo",
    "stones": "Stones",
    "julia": "Julia",
    "big_foot": "Big Foot",
    "cascade_chinook": "Cascade Chinook",
    "anchor": "Anchor",
    "shenandoah": "Shenandoah",
}

# Mature fields: modest delta expected with only 5 new months.
# Big Foot excluded — still producing at significant rates (7-8% growth over 5 months).
MATURE_FIELDS = ["Cascade Chinook", "Jack St Malo", "Stones", "Julia"]


@pytest.fixture(scope="module")
def golden_baseline():
    with GOLDEN_BASELINE_PATH.open("r") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def v30_production():
    """V30 default (no end_date) -- identical to WRK-009."""
    if not REPRODUCER_AVAILABLE:
        pytest.skip("V30 reproducer not available")
    return reproduce_v30_production()


@pytest.fixture(scope="module")
def extended_production():
    """Extended production through Oct 2025."""
    if not REPRODUCER_AVAILABLE:
        pytest.skip("V30 reproducer not available")
    return reproduce_v30_production(end_date="2025-10-31")


class TestExtendedProduction:
    """Verify extended production window beyond V30 baseline."""

    @pytest.mark.parametrize("project_id,dev_name", list(PRODUCING_PROJECTS.items()))
    def test_v30_default_unchanged(
        self, golden_baseline, v30_production, project_id, dev_name
    ):
        """V30 default totals still match golden baseline (regression guard)."""
        baseline = golden_baseline["projects"][project_id]
        expected_oil = baseline["total_oil_bbl"]
        tol = golden_baseline["tolerances"]["production_relative"]

        assert (
            dev_name in v30_production
        ), f"Development '{dev_name}' not found in V30 production"
        actual_oil = v30_production[dev_name]["total_oil_bbl"]
        assert actual_oil == pytest.approx(expected_oil, rel=tol), (
            f"{dev_name}: V30 oil {actual_oil:,.0f} vs baseline "
            f"{expected_oil:,.0f} "
            f"(delta: {(actual_oil - expected_oil) / expected_oil * 100:+.2f}%)"
        )

    def test_extended_includes_new_months(self, extended_production):
        """Extended window includes data in Jun-Oct 2025 for at least one field."""
        import pandas as pd

        cutoff = pd.Timestamp("2025-06-01")
        has_new_data = any(
            dev["last_date"] >= cutoff for dev in extended_production.values()
        )
        assert (
            has_new_data
        ), "No development has last_date >= 2025-06-01 in extended window"

    def test_all_7_producing_found(self, extended_production):
        """All 7 producing developments present in extended production."""
        for dev_name in PRODUCING_PROJECTS.values():
            assert (
                dev_name in extended_production
            ), f"Development '{dev_name}' missing from extended production"

    def test_anchor_production_increases(self, golden_baseline, extended_production):
        """Anchor total increases beyond V30 baseline (ramping since Aug 2024)."""
        v30_val = golden_baseline["projects"]["anchor"]["total_oil_bbl"]
        ext_val = extended_production["Anchor"]["total_oil_bbl"]
        assert (
            ext_val > v30_val
        ), f"Anchor extended {ext_val:,.0f} should exceed V30 {v30_val:,.0f}"

    def test_shenandoah_production_increases(
        self, golden_baseline, extended_production
    ):
        """Shenandoah total increases beyond V30 baseline (FO Feb 2025)."""
        v30_val = golden_baseline["projects"]["shenandoah"]["total_oil_bbl"]
        ext_val = extended_production["Shenandoah"]["total_oil_bbl"]
        assert (
            ext_val > v30_val
        ), f"Shenandoah extended {ext_val:,.0f} should exceed V30 {v30_val:,.0f}"

    @pytest.mark.parametrize("dev_name", MATURE_FIELDS)
    def test_mature_fields_stable(self, golden_baseline, extended_production, dev_name):
        """Mature fields have < 5% delta with only 5 new months added."""
        project_id = next(k for k, v in PRODUCING_PROJECTS.items() if v == dev_name)
        v30_total = golden_baseline["projects"][project_id]["total_oil_bbl"]
        extended_total = extended_production[dev_name]["total_oil_bbl"]
        delta_pct = abs(extended_total - v30_total) / v30_total
        assert delta_pct < 0.05, (
            f"{dev_name}: delta {delta_pct:.2%} exceeds 5% threshold "
            f"(V30: {v30_total:,.0f}, extended: {extended_total:,.0f})"
        )

    @pytest.mark.parametrize("dev_name", list(PRODUCING_PROJECTS.values()))
    def test_extended_production_geq_v30(
        self, v30_production, extended_production, dev_name
    ):
        """Extended window total >= V30 total for all producing developments."""
        v30_total = v30_production[dev_name]["total_oil_bbl"]
        ext_total = extended_production[dev_name]["total_oil_bbl"]
        assert ext_total >= v30_total, (
            f"{dev_name}: extended {ext_total:,.0f} < V30 {v30_total:,.0f} "
            f"-- wider window should never reduce production"
        )
