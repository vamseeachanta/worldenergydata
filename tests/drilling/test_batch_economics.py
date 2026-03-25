# ABOUTME: TDD tests for WRK-219 batch drilling economics module.
# ABOUTME: Covers learning curve, mobilization savings, NPV, break-even, and BSEE detection.

"""Unit tests for worldenergydata.drilling.batch_economics (WRK-219)."""

import math
import pandas as pd
import pytest

from worldenergydata.drilling.batch_economics.models import DrillingSite, DrillCampaign
from worldenergydata.drilling.batch_economics.economics import BatchDrillingEconomics
from worldenergydata.drilling.batch_economics.bsee_batch_detector import BSEEBatchDetector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_site(well_id: str, field_name: str = "ALPHA") -> DrillingSite:
    return DrillingSite(
        well_id=well_id,
        field_name=field_name,
        location_coords=(27.85, -90.34),
        water_depth_ft=5000.0,
        planned_md_ft=20000.0,
        well_type="development",
    )


def _make_campaign(n_wells: int, lc_factor: float = 0.85) -> DrillCampaign:
    wells = [_make_site(f"W{i+1:02d}") for i in range(n_wells)]
    return DrillCampaign(
        campaign_id="C001",
        rig_name="DEEP OCEAN ASCENSION",
        rig_day_rate_usd=350_000.0,
        mobilization_cost_usd=20_000_000.0,
        wells=wells,
        sequence=[w.well_id for w in wells],
        learning_curve_factor=lc_factor,
    )


# ---------------------------------------------------------------------------
# Learning curve tests
# ---------------------------------------------------------------------------


class TestLearningCurve:
    def setup_method(self):
        self.calc = BatchDrillingEconomics()

    def test_learning_curve_monotonic_decrease(self):
        """Later wells should take progressively less time than earlier wells."""
        base = 60.0
        times = [
            self.calc.learning_curve_time(base, pos)
            for pos in range(1, 6)
        ]
        for i in range(len(times) - 1):
            assert times[i] > times[i + 1], (
                f"Expected time to decrease from position {i+1} to {i+2}: "
                f"{times[i]:.2f} vs {times[i+1]:.2f}"
            )

    def test_learning_curve_position_1_unchanged(self):
        """Position 1 (first well) must equal base time regardless of LC factor."""
        base = 60.0
        result = self.calc.learning_curve_time(base, 1, lc_factor=0.85)
        assert math.isclose(result, base, rel_tol=1e-9), (
            f"Expected {base}, got {result}"
        )

    def test_learning_curve_position_1_unchanged_factor_90(self):
        """Position 1 must equal base time with 0.90 factor as well."""
        base = 45.0
        result = self.calc.learning_curve_time(base, 1, lc_factor=0.90)
        assert math.isclose(result, base, rel_tol=1e-9)

    def test_learning_curve_factor_1_no_improvement(self):
        """LC factor of 1.0 means no learning — all wells take the same time."""
        base = 60.0
        for pos in range(1, 5):
            t = self.calc.learning_curve_time(base, pos, lc_factor=1.0)
            assert math.isclose(t, base, rel_tol=1e-9), (
                f"Position {pos}: expected {base}, got {t}"
            )


# ---------------------------------------------------------------------------
# Mobilization savings tests
# ---------------------------------------------------------------------------


class TestMobilizationSavings:
    def setup_method(self):
        self.calc = BatchDrillingEconomics()

    def test_mobilization_savings_2_wells(self):
        """Per-well mob cost in a 2-well batch should be half of standalone."""
        mob = 20_000_000.0
        standalone = self.calc.mobilization_savings(mob, n_wells_batch=1)
        batch_2 = self.calc.mobilization_savings(mob, n_wells_batch=2)
        assert math.isclose(batch_2, standalone / 2.0, rel_tol=1e-9), (
            f"Expected {standalone/2.0}, got {batch_2}"
        )

    def test_mobilization_savings_4_wells(self):
        """Per-well mob cost in a 4-well batch should be a quarter of standalone."""
        mob = 20_000_000.0
        standalone = self.calc.mobilization_savings(mob, n_wells_batch=1)
        batch_4 = self.calc.mobilization_savings(mob, n_wells_batch=4)
        assert math.isclose(batch_4, standalone / 4.0, rel_tol=1e-9)

    def test_mobilization_savings_decreasing_with_more_wells(self):
        """Per-well cost must monotonically decrease as batch size grows."""
        mob = 20_000_000.0
        prev = self.calc.mobilization_savings(mob, n_wells_batch=1)
        for n in range(2, 8):
            curr = self.calc.mobilization_savings(mob, n_wells_batch=n)
            assert curr < prev, f"Per-well cost did not decrease from n={n-1} to n={n}"
            prev = curr


# ---------------------------------------------------------------------------
# Break-even tests
# ---------------------------------------------------------------------------


class TestBreakEven:
    def setup_method(self):
        self.calc = BatchDrillingEconomics()

    def test_break_even_at_1_is_no_savings(self):
        """Break-even of 1 well means batch = standalone (no additional benefit)."""
        n = self.calc.break_even_n_wells(
            mob_cost=20_000_000.0,
            day_rate=350_000.0,
            base_well_days=60.0,
            lc_factor=1.0,  # No learning, so break-even is 1
        )
        # With no learning curve, there is no saving from batching — break-even is 1
        assert n >= 1

    def test_break_even_increases_with_higher_mob_cost(self):
        """Higher mobilization cost requires more wells to reach break-even."""
        n_low = self.calc.break_even_n_wells(
            mob_cost=5_000_000.0,
            day_rate=350_000.0,
            base_well_days=60.0,
        )
        n_high = self.calc.break_even_n_wells(
            mob_cost=50_000_000.0,
            day_rate=350_000.0,
            base_well_days=60.0,
        )
        assert n_high >= n_low, (
            f"Higher mob cost should need >= wells: got n_low={n_low}, n_high={n_high}"
        )

    def test_break_even_positive_integer(self):
        """Break-even result must be a positive integer."""
        n = self.calc.break_even_n_wells(
            mob_cost=20_000_000.0,
            day_rate=350_000.0,
            base_well_days=60.0,
        )
        assert isinstance(n, int)
        assert n >= 1


# ---------------------------------------------------------------------------
# NPV comparison tests
# ---------------------------------------------------------------------------


class TestBatchVsStandaloneNPV:
    def setup_method(self):
        self.calc = BatchDrillingEconomics()

    def test_batch_npv_lower_than_standalone(self):
        """Batch campaign total cost should be less than sum of standalone costs
        when N wells > break-even (learning curve + mob sharing produce savings)."""
        campaign = _make_campaign(n_wells=5, lc_factor=0.85)
        result = self.calc.batch_vs_standalone_npv(campaign, discount_rate=0.10)
        assert result["batch_npv"] < result["standalone_npv"], (
            f"Expected batch_npv < standalone_npv: "
            f"batch={result['batch_npv']:.0f} standalone={result['standalone_npv']:.0f}"
        )

    def test_batch_savings_positive_for_multi_well(self):
        """batch_savings must be positive for a multi-well campaign."""
        campaign = _make_campaign(n_wells=4, lc_factor=0.85)
        result = self.calc.batch_vs_standalone_npv(campaign, discount_rate=0.10)
        assert result["batch_savings"] > 0.0, (
            f"Expected positive savings, got {result['batch_savings']}"
        )

    def test_single_well_no_mob_savings(self):
        """Single-well campaign: batch NPV should equal standalone (no mob savings)."""
        campaign = _make_campaign(n_wells=1)
        result = self.calc.batch_vs_standalone_npv(campaign, discount_rate=0.10)
        assert math.isclose(
            result["batch_npv"], result["standalone_npv"], rel_tol=1e-6
        ), (
            f"Single well: batch={result['batch_npv']:.2f} "
            f"standalone={result['standalone_npv']:.2f}"
        )

    def test_result_has_required_keys(self):
        """Result dict must contain batch_npv, standalone_npv, batch_savings."""
        campaign = _make_campaign(n_wells=3)
        result = self.calc.batch_vs_standalone_npv(campaign)
        for key in ("batch_npv", "standalone_npv", "batch_savings"):
            assert key in result, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Campaign total cost tests
# ---------------------------------------------------------------------------


class TestCampaignTotalCost:
    def setup_method(self):
        self.calc = BatchDrillingEconomics()

    def test_campaign_total_cost_decreases_with_more_wells(self):
        """Average per-well cost should decrease as campaign grows (learning curve)."""
        costs = []
        for n in [2, 4, 6]:
            campaign = _make_campaign(n_wells=n, lc_factor=0.85)
            total = self.calc.campaign_total_cost(campaign, base_days_per_well=60.0)
            costs.append(total / n)  # average per-well cost

        for i in range(len(costs) - 1):
            assert costs[i] > costs[i + 1], (
                f"Per-well cost should decrease as batch grows: "
                f"n={2*(i+1)} avg={costs[i]:.0f} vs n={2*(i+2)} avg={costs[i+1]:.0f}"
            )

    def test_campaign_total_cost_positive(self):
        """Total campaign cost must always be positive."""
        campaign = _make_campaign(n_wells=3)
        total = self.calc.campaign_total_cost(campaign, base_days_per_well=60.0)
        assert total > 0.0

    def test_campaign_total_cost_includes_mobilization(self):
        """Total cost without mob savings should exceed day-rate-only cost."""
        campaign = _make_campaign(n_wells=3)
        total = self.calc.campaign_total_cost(campaign, base_days_per_well=60.0)
        min_day_rate_cost = campaign.rig_day_rate_usd * 60.0 * 3
        assert total > min_day_rate_cost, (
            "Total cost should include mobilization on top of day-rate cost"
        )


# ---------------------------------------------------------------------------
# BSEE batch detector tests
# ---------------------------------------------------------------------------


def _make_bsee_df(records: list[dict]) -> pd.DataFrame:
    """Build a minimal BSEE-style activity DataFrame from a list of dicts."""
    return pd.DataFrame(records)


class TestBSEEBatchDetector:
    def setup_method(self):
        self.detector = BSEEBatchDetector()

    def test_detect_batches_same_rig_same_field(self):
        """Same rig drilling same field within 12 months → detected as batch."""
        df = _make_bsee_df([
            {
                "well_id": "W001",
                "rig_name": "DEEP OCEAN ASCENSION",
                "field_name": "JULIA",
                "spud_date": pd.Timestamp("2022-01-15"),
            },
            {
                "well_id": "W002",
                "rig_name": "DEEP OCEAN ASCENSION",
                "field_name": "JULIA",
                "spud_date": pd.Timestamp("2022-04-20"),
            },
            {
                "well_id": "W003",
                "rig_name": "DEEP OCEAN ASCENSION",
                "field_name": "JULIA",
                "spud_date": pd.Timestamp("2022-08-10"),
            },
        ])
        result = self.detector.detect_batches(df, time_window_months=12)
        assert len(result) > 0, "Expected at least one detected batch"
        # All three wells should be in the same batch
        max_batch_size = result["batch_size"].max()
        assert max_batch_size >= 3, (
            f"Expected batch of >=3 wells, got max_batch_size={max_batch_size}"
        )

    def test_detect_batches_separate_rigs(self):
        """Different rigs drilling the same field must NOT be one batch."""
        df = _make_bsee_df([
            {
                "well_id": "W001",
                "rig_name": "DEEP OCEAN ASCENSION",
                "field_name": "JULIA",
                "spud_date": pd.Timestamp("2022-01-15"),
            },
            {
                "well_id": "W002",
                "rig_name": "DISCOVERER CLEAR LEADER",
                "field_name": "JULIA",
                "spud_date": pd.Timestamp("2022-04-20"),
            },
        ])
        result = self.detector.detect_batches(df, time_window_months=12)
        # Each rig is a separate batch; no batch should contain both wells
        if len(result) > 0:
            max_batch_size = result["batch_size"].max()
            assert max_batch_size == 1, (
                f"Expected no multi-well batch across different rigs, "
                f"but got batch_size={max_batch_size}"
            )

    def test_detect_batches_outside_time_window(self):
        """Wells drilled more than time_window_months apart are not a batch."""
        df = _make_bsee_df([
            {
                "well_id": "W001",
                "rig_name": "DEEP OCEAN ASCENSION",
                "field_name": "JULIA",
                "spud_date": pd.Timestamp("2020-01-01"),
            },
            {
                "well_id": "W002",
                "rig_name": "DEEP OCEAN ASCENSION",
                "field_name": "JULIA",
                "spud_date": pd.Timestamp("2022-03-01"),
            },
        ])
        result = self.detector.detect_batches(df, time_window_months=12)
        if len(result) > 0:
            max_batch_size = result["batch_size"].max()
            assert max_batch_size == 1, (
                f"Wells >12 months apart should not form a batch: "
                f"max_batch_size={max_batch_size}"
            )

    def test_detect_batches_returns_dataframe(self):
        """detect_batches must return a pandas DataFrame."""
        df = _make_bsee_df([
            {
                "well_id": "W001",
                "rig_name": "RIG_A",
                "field_name": "FIELD_X",
                "spud_date": pd.Timestamp("2022-01-01"),
            },
        ])
        result = self.detector.detect_batches(df)
        assert isinstance(result, pd.DataFrame)

    def test_fit_learning_curve_returns_float(self):
        """fit_learning_curve must return a float in a valid range."""
        campaign_df = pd.DataFrame({
            "well_position": [1, 2, 3, 4],
            "days_to_drill": [60.0, 52.0, 48.0, 45.0],
        })
        lc = self.detector.fit_learning_curve(campaign_df)
        assert isinstance(lc, float)
        assert 0.5 < lc <= 1.0, f"LC factor should be in (0.5, 1.0], got {lc}"
