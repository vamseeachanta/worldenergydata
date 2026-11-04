# ABOUTME: TDD tests for WRK-219 batch drilling economics module.
# ABOUTME: Covers learning curve, mobilization savings, NPV, break-even, and BSEE detection.

"""Unit tests for worldenergydata.drilling.batch_economics (WRK-219)."""

import math

import pandas as pd
import pytest

from worldenergydata.drilling.batch_economics.bsee_batch_detector import (
    BSEEBatchDetector,
)
from worldenergydata.drilling.batch_economics.economics import BatchDrillingEconomics
from worldenergydata.drilling.batch_economics.models import DrillCampaign, DrillingSite

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
        times = [self.calc.learning_curve_time(base, pos) for pos in range(1, 6)]
        for i in range(len(times) - 1):
            assert times[i] > times[i + 1], (
                f"Expected time to decrease from position {i+1} to {i+2}: "
                f"{times[i]:.2f} vs {times[i+1]:.2f}"
            )

    def test_learning_curve_position_1_unchanged(self):
        """Position 1 (first well) must equal base time regardless of LC factor."""
        base = 60.0
        result = self.calc.learning_curve_time(base, 1, lc_factor=0.85)
        assert math.isclose(
            result, base, rel_tol=1e-9
        ), f"Expected {base}, got {result}"

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
            assert math.isclose(
                t, base, rel_tol=1e-9
            ), f"Position {pos}: expected {base}, got {t}"


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
        assert standalone == 20_000_000.0
        assert batch_2 == 10_000_000.0

    def test_mobilization_savings_4_wells(self):
        """Per-well mob cost in a 4-well batch should be a quarter of standalone."""
        mob = 20_000_000.0
        batch_4 = self.calc.mobilization_savings(mob, n_wells_batch=4)
        assert batch_4 == 5_000_000.0

    @pytest.mark.parametrize("standalone_count", [0, 1, 3, 99])
    def test_legacy_standalone_count_is_ignored(self, standalone_count):
        """Compatibility: the result is allocated cost, not a savings difference."""
        assert self.calc.mobilization_savings(1200.0, 3, standalone_count) == 400.0

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

    def test_no_learning_saves_one_mobilization_at_two_wells(self):
        """Hand calculation: M=100, R=10, T=20, LC=1 (synthetic inputs).

        Source: drilling/docs/agent-pack.md, revision 2 (2026), section 3.
        At N=1: B=S=100+10*20=300. At N=2: B=100+10*40=500,
        S=2*(100+10*20)=600. Strict savings first occur at two wells.
        """
        assert self.calc.break_even_n_wells(100.0, 10.0, 20.0, 1.0) == 2

    @pytest.mark.parametrize("mobilization", [100.0, 1000.0])
    def test_higher_mobilization_still_saves_at_two_wells(self, mobilization):
        """Hand calculation with synthetic R=10, T=20, LC=0.5.

        Source: drilling/docs/agent-pack.md, revision 2 (2026), section 3.
        At N=1 both costs are M+200. At N=2, T_2=10, B=M+300,
        S=2*M+400, so savings=M+100: 200 for M=100, 1100 for M=1000.
        Both cases first save at two wells; greater M increases the saving.
        """
        campaign = _make_campaign(n_wells=2, lc_factor=0.5).model_copy(
            update={"mobilization_cost_usd": mobilization, "rig_day_rate_usd": 10.0}
        )
        batch = self.calc.campaign_total_cost(campaign, base_days_per_well=20.0)
        standalone = 2 * (mobilization + 200.0)
        expected = {100.0: (400.0, 600.0, 200.0), 1000.0: (1300.0, 2400.0, 1100.0)}
        assert (batch, standalone, standalone - batch) == pytest.approx(
            expected[mobilization], abs=0.01, rel=0
        )
        assert self.calc.break_even_n_wells(mobilization, 10.0, 20.0, 0.5) == 2

    def test_learning_alone_saves_at_two_wells(self):
        """Hand calculation: M=0, R=10, T=20, LC=0.5 (synthetic inputs).

        Source: drilling/docs/agent-pack.md, revision 2 (2026), section 3.
        At N=1: B=S=200. At N=2: B=10*(20+10)=300, S=2*200=400.
        The exact integer threshold is two wells even without mobilization.
        """
        n = self.calc.break_even_n_wells(0.0, 10.0, 20.0, 0.5)
        assert isinstance(n, int)
        assert n == 2

    @pytest.mark.parametrize("n_wells", [1, 2, 200])
    def test_legacy_no_savings_sentinel_is_not_break_even(self, n_wells):
        """Zero mobilization and no learning tie; 1 means no strict saving.

        Synthetic depths give 20000/400 + 5000/2000 + 10 = 62.5 days.
        Each well costs 350000 * 62.5 = 21875000 USD in either scenario.
        """
        campaign = _make_campaign(n_wells, lc_factor=1.0).model_copy(
            update={"mobilization_cost_usd": 0.0}
        )
        result = self.calc.batch_vs_standalone_npv(campaign)
        assert result == {
            "batch_npv": n_wells * 21_875_000.0,
            "standalone_npv": n_wells * 21_875_000.0,
            "batch_savings": 0.0,
        }
        assert self.calc.break_even_n_wells(0.0, 350_000.0, 62.5, 1.0) == 1


# ---------------------------------------------------------------------------
# NPV comparison tests
# ---------------------------------------------------------------------------


class TestBatchVsStandaloneNPV:
    def setup_method(self):
        self.calc = BatchDrillingEconomics()

    def test_batch_npv_lower_than_standalone(self):
        """Synthetic 62.5-day base, LC=0.85; independent USD totals to cents.

        The summed per-position drilling cost plus one 20M mobilization
        is compared with five full 41.875M wells.
        """
        campaign = _make_campaign(n_wells=5, lc_factor=0.85)
        result = self.calc.batch_vs_standalone_npv(campaign, discount_rate=0.10)
        assert result == pytest.approx(
            {
                "batch_npv": 108_180_004.02,
                "standalone_npv": 209_375_000.0,
                "batch_savings": 101_194_995.98,
            },
            abs=0.01,
            rel=0,
        )

    def test_batch_savings_positive_for_multi_well(self):
        """Four synthetic wells use a 62.5-day base and LC=0.85; totals to cents."""
        campaign = _make_campaign(n_wells=4, lc_factor=0.85)
        result = self.calc.batch_vs_standalone_npv(campaign, discount_rate=0.10)
        assert result == pytest.approx(
            {
                "batch_npv": 93_180_949.55,
                "standalone_npv": 167_500_000.0,
                "batch_savings": 74_319_050.45,
            },
            abs=0.01,
            rel=0,
        )

    def test_single_well_no_mob_savings(self):
        """One well costs 20M + 350000 * 62.5 = 41.875M USD in both cases."""
        campaign = _make_campaign(n_wells=1)
        result = self.calc.batch_vs_standalone_npv(campaign, discount_rate=0.10)
        assert result == {
            "batch_npv": 41_875_000.0,
            "standalone_npv": 41_875_000.0,
            "batch_savings": 0.0,
        }

    def test_result_has_required_keys(self):
        """Legacy keys/default rate retain undiscounted costs with no learning."""
        campaign = _make_campaign(n_wells=3, lc_factor=1.0)
        result = self.calc.batch_vs_standalone_npv(campaign)
        assert result == {
            "batch_npv": 85_625_000.0,
            "standalone_npv": 125_625_000.0,
            "batch_savings": 40_000_000.0,
        }

    @pytest.mark.parametrize("discount_rate", [0.0, 0.10, 0.75])
    def test_legacy_discount_rate_is_ignored(self, discount_rate):
        """Compatibility: 62.5 + 31.25 days, one mobilization, no discounting."""
        campaign = _make_campaign(n_wells=2, lc_factor=0.5)
        result = self.calc.batch_vs_standalone_npv(campaign, discount_rate)
        assert result == pytest.approx(
            {
                "batch_npv": 52_812_500.0,
                "standalone_npv": 83_750_000.0,
                "batch_savings": 30_937_500.0,
            },
            abs=0.01,
            rel=0,
        )
        assert self.calc.campaign_total_cost(campaign, 62.5) == result["batch_npv"]


# ---------------------------------------------------------------------------
# Campaign total cost tests
# ---------------------------------------------------------------------------


class TestCampaignTotalCost:
    def setup_method(self):
        self.calc = BatchDrillingEconomics()

    def test_campaign_total_cost_decreases_with_more_wells(self):
        """Average per-well cost should decrease as campaign grows (learning curve)."""
        costs = []
        # LC=0.5 gives per-position days 60, 30, 20, 15, 12, 10.
        for n, expected in [(2, 51_500_000), (4, 63_750_000), (6, 71_450_000)]:
            campaign = _make_campaign(n_wells=n, lc_factor=0.5)
            total = self.calc.campaign_total_cost(campaign, base_days_per_well=60.0)
            assert total == pytest.approx(expected, abs=0.01, rel=0)
            costs.append(total / n)  # average per-well cost

        for i in range(len(costs) - 1):
            assert costs[i] > costs[i + 1], (
                f"Per-well cost should decrease as batch grows: "
                f"n={2*(i+1)} avg={costs[i]:.0f} vs n={2*(i+2)} avg={costs[i+1]:.0f}"
            )

    def test_campaign_total_cost_positive(self):
        """Three 60-day wells plus one mobilization cost 83M USD, LC=1."""
        campaign = _make_campaign(n_wells=3, lc_factor=1.0)
        total = self.calc.campaign_total_cost(campaign, base_days_per_well=60.0)
        assert total == 83_000_000.0

    def test_campaign_total_cost_includes_mobilization(self):
        """With no learning, 83M total minus 63M drilling is exactly 20M mob."""
        campaign = _make_campaign(n_wells=3, lc_factor=1.0)
        total = self.calc.campaign_total_cost(campaign, base_days_per_well=60.0)
        zero_mob = campaign.model_copy(update={"mobilization_cost_usd": 0.0})
        drilling_only = self.calc.campaign_total_cost(zero_mob, base_days_per_well=60.0)
        assert drilling_only == 63_000_000.0
        assert total - drilling_only == 20_000_000.0


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
        df = _make_bsee_df(
            [
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
            ]
        )
        result = self.detector.detect_batches(df, time_window_months=12)
        assert len(result) > 0, "Expected at least one detected batch"
        # All three wells should be in the same batch
        max_batch_size = result["batch_size"].max()
        assert (
            max_batch_size >= 3
        ), f"Expected batch of >=3 wells, got max_batch_size={max_batch_size}"

    def test_detect_batches_separate_rigs(self):
        """Different rigs drilling the same field must NOT be one batch."""
        df = _make_bsee_df(
            [
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
            ]
        )
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
        df = _make_bsee_df(
            [
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
            ]
        )
        result = self.detector.detect_batches(df, time_window_months=12)
        if len(result) > 0:
            max_batch_size = result["batch_size"].max()
            assert max_batch_size == 1, (
                f"Wells >12 months apart should not form a batch: "
                f"max_batch_size={max_batch_size}"
            )

    def test_detect_batches_returns_dataframe(self):
        """detect_batches must return a pandas DataFrame."""
        df = _make_bsee_df(
            [
                {
                    "well_id": "W001",
                    "rig_name": "RIG_A",
                    "field_name": "FIELD_X",
                    "spud_date": pd.Timestamp("2022-01-01"),
                },
            ]
        )
        result = self.detector.detect_batches(df)
        assert isinstance(result, pd.DataFrame)

    def test_fit_learning_curve_returns_float(self):
        """fit_learning_curve must return a float in a valid range."""
        campaign_df = pd.DataFrame(
            {
                "well_position": [1, 2, 3, 4],
                "days_to_drill": [60.0, 52.0, 48.0, 45.0],
            }
        )
        lc = self.detector.fit_learning_curve(campaign_df)
        assert isinstance(lc, float)
        assert 0.5 < lc <= 1.0, f"LC factor should be in (0.5, 1.0], got {lc}"
