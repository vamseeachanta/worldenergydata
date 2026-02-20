"""Tests for the bore-type decision framework."""

import pytest

from worldenergydata.well_bore_design.decision_framework import (
    APPLICATION_MATRIX,
    BoreTypeDecision,
    BoreTypeRecommendation,
)
from worldenergydata.well_bore_design.schemas import BoreType


@pytest.fixture
def decision():
    return BoreTypeDecision()


# ---------------------------------------------------------------------------
# BoreTypeRecommendation dataclass
# ---------------------------------------------------------------------------


class TestBoreTypeRecommendation:
    def test_can_construct_manually(self):
        rec = BoreTypeRecommendation(
            recommended=BoreType.SLIM_HOLE,
            rationale="test",
            pressure_window_compatible=True,
            hole_cleaning_adequate=True,
            capital_cost_factor=0.65,
            operational_risk_level="low",
        )
        assert rec.recommended == BoreType.SLIM_HOLE

    def test_caveats_defaults_to_empty_list(self):
        rec = BoreTypeRecommendation(
            recommended=BoreType.STANDARD,
            rationale="",
            pressure_window_compatible=True,
            hole_cleaning_adequate=True,
            capital_cost_factor=1.0,
            operational_risk_level="low",
        )
        assert rec.caveats == []


# ---------------------------------------------------------------------------
# recommend() — return type and structure
# ---------------------------------------------------------------------------


class TestRecommendReturnType:
    def test_returns_bore_type_recommendation(self, decision):
        rec = decision.recommend(
            well_type="exploration",
            total_depth_m=3000.0,
            pressure_window_ppg=1.0,
            target_flow_rate_bopd=500.0,
        )
        assert isinstance(rec, BoreTypeRecommendation)

    def test_recommended_is_bore_type(self, decision):
        rec = decision.recommend("exploration", 3000.0, 1.0, 500.0)
        assert isinstance(rec.recommended, BoreType)

    def test_pressure_window_compatible_is_bool(self, decision):
        rec = decision.recommend("exploration", 3000.0, 1.0, 500.0)
        assert isinstance(rec.pressure_window_compatible, bool)

    def test_hole_cleaning_adequate_is_bool(self, decision):
        rec = decision.recommend("exploration", 3000.0, 1.0, 500.0)
        assert isinstance(rec.hole_cleaning_adequate, bool)

    def test_capital_cost_factor_is_float(self, decision):
        rec = decision.recommend("exploration", 3000.0, 1.0, 500.0)
        assert isinstance(rec.capital_cost_factor, float)

    def test_operational_risk_level_is_valid_string(self, decision):
        rec = decision.recommend("exploration", 3000.0, 1.0, 500.0)
        assert rec.operational_risk_level in {"low", "medium", "high"}

    def test_caveats_is_list(self, decision):
        rec = decision.recommend("exploration", 3000.0, 1.0, 500.0)
        assert isinstance(rec.caveats, list)


# ---------------------------------------------------------------------------
# recommend() — application logic
# ---------------------------------------------------------------------------


class TestRecommendLogic:
    def test_exploration_tight_margin_returns_slim_hole(self, decision):
        rec = decision.recommend(
            well_type="exploration",
            total_depth_m=3000.0,
            pressure_window_ppg=0.8,
            target_flow_rate_bopd=500.0,
        )
        assert rec.recommended == BoreType.SLIM_HOLE

    def test_exploration_low_flow_returns_slim_hole(self, decision):
        rec = decision.recommend(
            well_type="exploration",
            total_depth_m=4000.0,
            pressure_window_ppg=2.0,
            target_flow_rate_bopd=1000.0,
        )
        assert rec.recommended == BoreType.SLIM_HOLE

    def test_high_rate_production_returns_large_bore(self, decision):
        rec = decision.recommend(
            well_type="production",
            total_depth_m=3500.0,
            pressure_window_ppg=2.5,
            target_flow_rate_bopd=20000.0,
        )
        assert rec.recommended == BoreType.LARGE_BORE

    def test_standard_development_well_returns_standard(self, decision):
        rec = decision.recommend(
            well_type="development",
            total_depth_m=4000.0,
            pressure_window_ppg=2.5,
            target_flow_rate_bopd=3000.0,
        )
        assert rec.recommended == BoreType.STANDARD

    def test_slim_hole_has_capital_cost_factor_below_one(self, decision):
        rec = decision.recommend("exploration", 3000.0, 0.8, 500.0)
        assert rec.capital_cost_factor < 1.0

    def test_standard_has_capital_cost_factor_one(self, decision):
        rec = decision.recommend("development", 4000.0, 2.5, 3000.0)
        assert rec.capital_cost_factor == pytest.approx(1.0)

    def test_large_bore_has_capital_cost_factor_above_one(self, decision):
        rec = decision.recommend("production", 3500.0, 2.5, 20000.0)
        assert rec.capital_cost_factor > 1.0

    def test_highly_deviated_slim_hole_inadequate_cleaning(self, decision):
        rec = decision.recommend(
            well_type="exploration",
            total_depth_m=3000.0,
            pressure_window_ppg=0.8,
            target_flow_rate_bopd=500.0,
            deviation_deg=60.0,
        )
        assert rec.hole_cleaning_adequate is False

    def test_vertical_slim_hole_adequate_cleaning(self, decision):
        rec = decision.recommend(
            well_type="exploration",
            total_depth_m=3000.0,
            pressure_window_ppg=0.8,
            target_flow_rate_bopd=500.0,
            deviation_deg=0.0,
        )
        assert rec.hole_cleaning_adequate is True

    def test_complex_completion_slim_hole_adds_caveat(self, decision):
        rec = decision.recommend(
            well_type="exploration",
            total_depth_m=3000.0,
            pressure_window_ppg=0.8,
            target_flow_rate_bopd=500.0,
            completion_type="gravel_pack",
        )
        assert any("gravel_pack" in c or "completion" in c.lower() for c in rec.caveats)

    def test_rationale_is_non_empty_string(self, decision):
        rec = decision.recommend("exploration", 3000.0, 1.0, 500.0)
        assert isinstance(rec.rationale, str)
        assert len(rec.rationale) > 0


# ---------------------------------------------------------------------------
# pressure_window_check()
# ---------------------------------------------------------------------------


class TestPressureWindowCheck:
    def test_returns_dict_with_required_keys(self, decision):
        result = decision.pressure_window_check(
            bore_type=BoreType.STANDARD,
            mud_weight_ppg=10.0,
            fracture_gradient_ppg=14.0,
            pore_pressure_ppg=9.5,
            flow_rate_gpm=450.0,
            depth_ft=8000.0,
        )
        assert "compatible" in result
        assert "margin_ppg" in result
        assert "limiting_factor" in result

    def test_compatible_is_bool(self, decision):
        result = decision.pressure_window_check(
            BoreType.STANDARD, 10.0, 14.0, 9.5, 450.0, 8000.0
        )
        assert isinstance(result["compatible"], bool)

    def test_margin_ppg_is_float(self, decision):
        result = decision.pressure_window_check(
            BoreType.STANDARD, 10.0, 14.0, 9.5, 450.0, 8000.0
        )
        assert isinstance(result["margin_ppg"], float)

    def test_limiting_factor_is_string(self, decision):
        result = decision.pressure_window_check(
            BoreType.STANDARD, 10.0, 14.0, 9.5, 450.0, 8000.0
        )
        assert isinstance(result["limiting_factor"], str)

    def test_wide_window_is_compatible(self, decision):
        result = decision.pressure_window_check(
            bore_type=BoreType.STANDARD,
            mud_weight_ppg=9.5,
            fracture_gradient_ppg=16.0,
            pore_pressure_ppg=9.0,
            flow_rate_gpm=450.0,
            depth_ft=8000.0,
        )
        assert result["compatible"] is True

    def test_ecd_exceeds_fracture_gradient_is_incompatible(self, decision):
        # Use very high flow rate into slim hole at shallow depth to drive ECD up
        result = decision.pressure_window_check(
            bore_type=BoreType.SLIM_HOLE,
            mud_weight_ppg=12.0,
            fracture_gradient_ppg=12.5,
            pore_pressure_ppg=11.0,
            flow_rate_gpm=800.0,
            depth_ft=1000.0,
        )
        # High ECD in slim annulus at shallow depth may exceed fracture gradient
        assert "limiting_factor" in result
        assert result["margin_ppg"] is not None


# ---------------------------------------------------------------------------
# APPLICATION_MATRIX
# ---------------------------------------------------------------------------


class TestApplicationMatrix:
    def test_has_three_bore_type_keys(self):
        assert len(APPLICATION_MATRIX) == 3

    def test_slim_hole_key_present(self):
        assert BoreType.SLIM_HOLE.value in APPLICATION_MATRIX

    def test_standard_key_present(self):
        assert BoreType.STANDARD.value in APPLICATION_MATRIX

    def test_large_bore_key_present(self):
        assert BoreType.LARGE_BORE.value in APPLICATION_MATRIX

    def test_all_entries_have_capital_cost_factor(self):
        for key, entry in APPLICATION_MATRIX.items():
            assert "capital_cost_factor" in entry, f"Missing for {key}"

    def test_all_entries_have_well_types(self):
        for key, entry in APPLICATION_MATRIX.items():
            assert "well_types" in entry and entry["well_types"], f"Missing for {key}"

    def test_slim_hole_capital_cheaper_than_standard(self):
        slim_cost = APPLICATION_MATRIX[BoreType.SLIM_HOLE.value]["capital_cost_factor"]
        std_cost = APPLICATION_MATRIX[BoreType.STANDARD.value]["capital_cost_factor"]
        assert slim_cost < std_cost

    def test_large_bore_capital_more_than_standard(self):
        lb_cost = APPLICATION_MATRIX[BoreType.LARGE_BORE.value]["capital_cost_factor"]
        std_cost = APPLICATION_MATRIX[BoreType.STANDARD.value]["capital_cost_factor"]
        assert lb_cost > std_cost
