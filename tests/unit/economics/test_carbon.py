"""
ABOUTME: Tests for carbon cost sensitivity analysis module.
ABOUTME: Covers sensitivity curves, breakeven solver, and tornado chart output.

All expected values derived analytically using the underlying NPV formula.
"""

from __future__ import annotations

import numpy as np
import pytest

from worldenergydata.economics.carbon import (
    CarbonSensitivityResult,
    TornadoEntry,
    breakeven_carbon_price,
    carbon_npv_curve,
    tornado_sensitivity,
)
from worldenergydata.economics.dcf import (
    CashFlowSchedule,
    build_cash_flow_schedule,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _field_schedule(carbon_price: float = 0.0) -> CashFlowSchedule:
    """Standard 5-year field development schedule for sensitivity tests.

    Capex: 2_000_000 at t=0
    Production: 50_000 boe/yr for 5 years
    Oil price: 70 USD/boe
    Opex: 15 USD/boe
    Scope1: 0.02 tCO2/boe, Scope2: 0.03 tCO2/boe
    """
    return build_cash_flow_schedule(
        years=list(range(6)),
        production_boe_per_year=[0.0] + [50_000.0] * 5,
        oil_price_usd_per_boe=70.0,
        opex_usd_per_boe=15.0,
        capex_by_year=[2_000_000.0] + [0.0] * 5,
        carbon_cost_usd_per_tonne=carbon_price,
        scope1_tco2_per_boe=0.02,
        scope2_tco2_per_boe=0.03,
    )


# ---------------------------------------------------------------------------
# carbon_npv_curve
# ---------------------------------------------------------------------------


class TestCarbonNpvCurve:
    """Tests for NPV vs. carbon price curve generation."""

    def test_curve_returns_sensitivity_result(self):
        """carbon_npv_curve returns CarbonSensitivityResult."""
        result = carbon_npv_curve(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            carbon_prices=np.array([0.0, 50.0, 100.0]),
        )
        assert isinstance(result, CarbonSensitivityResult)

    def test_curve_length_matches_input(self):
        """Output arrays same length as carbon_prices input."""
        prices = np.linspace(0, 200, 10)
        result = carbon_npv_curve(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            carbon_prices=prices,
        )
        assert len(result.carbon_prices) == 10
        assert len(result.npv_values) == 10

    def test_npv_decreases_with_higher_carbon_price(self):
        """NPV is monotonically non-increasing as carbon price rises."""
        prices = np.linspace(0, 500, 50)
        result = carbon_npv_curve(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            carbon_prices=prices,
        )
        diffs = np.diff(result.npv_values)
        assert np.all(diffs <= 1e-6), "NPV should decrease as carbon price increases"

    def test_npv_at_zero_carbon_matches_no_carbon_case(self):
        """NPV at carbon_price=0 equals NPV with no carbon module."""
        from worldenergydata.economics.dcf import calculate_npv

        schedule_no_carbon = _field_schedule(carbon_price=0.0)
        result_no_carbon = calculate_npv(schedule_no_carbon, discount_rate=0.10)

        result_curve = carbon_npv_curve(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            carbon_prices=np.array([0.0]),
        )
        assert result_curve.npv_values[0] == pytest.approx(
            result_no_carbon.npv, rel=1e-6
        )

    def test_base_npv_stored(self):
        """CarbonSensitivityResult stores base NPV (at carbon_price=0)."""
        result = carbon_npv_curve(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            carbon_prices=np.linspace(0, 100, 5),
        )
        assert hasattr(result, "base_npv")
        assert isinstance(result.base_npv, float)

    def test_discount_rate_stored(self):
        """CarbonSensitivityResult stores discount rate."""
        result = carbon_npv_curve(
            base_schedule=_field_schedule(),
            discount_rate=0.12,
            carbon_prices=np.array([0.0, 50.0]),
        )
        assert result.discount_rate == pytest.approx(0.12)


# ---------------------------------------------------------------------------
# breakeven_carbon_price
# ---------------------------------------------------------------------------


class TestBreakevenCarbonPrice:
    """Tests for NPV=0 breakeven carbon price solver."""

    def test_breakeven_exists_for_marginal_project(self):
        """A project barely profitable at zero carbon has a finite breakeven."""
        # NPV > 0 at carbon=0, so there must be a breakeven carbon price
        result = carbon_npv_curve(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            carbon_prices=np.linspace(0, 2000, 200),
        )
        # Verify project is profitable at 0 carbon
        assert result.npv_values[0] > 0

        bp = breakeven_carbon_price(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            search_upper=5000.0,
        )
        assert bp is not None
        assert bp > 0

    def test_breakeven_npv_is_zero(self):
        """At the breakeven price, NPV must be ~0."""
        from worldenergydata.economics.dcf import calculate_npv

        bp = breakeven_carbon_price(
            base_schedule=_field_schedule(),
            discount_rate=0.10,
            search_upper=5000.0,
        )
        assert bp is not None

        schedule_at_bp = build_cash_flow_schedule(
            years=list(range(6)),
            production_boe_per_year=[0.0] + [50_000.0] * 5,
            oil_price_usd_per_boe=70.0,
            opex_usd_per_boe=15.0,
            capex_by_year=[2_000_000.0] + [0.0] * 5,
            carbon_cost_usd_per_tonne=bp,
            scope1_tco2_per_boe=0.02,
            scope2_tco2_per_boe=0.03,
        )
        npv_at_bp = calculate_npv(schedule_at_bp, discount_rate=0.10)
        assert npv_at_bp.npv == pytest.approx(0.0, abs=1.0)

    def test_breakeven_returns_none_for_always_negative(self):
        """Returns None when NPV is negative even at zero carbon price."""
        # Project with huge capex, tiny revenues
        unprofitable = build_cash_flow_schedule(
            years=[0, 1, 2],
            production_boe_per_year=[0.0, 100.0, 100.0],
            oil_price_usd_per_boe=10.0,
            opex_usd_per_boe=0.0,
            capex_by_year=[10_000_000.0, 0.0, 0.0],
            carbon_cost_usd_per_tonne=0.0,
            scope1_tco2_per_boe=0.0,
            scope2_tco2_per_boe=0.0,
        )
        bp = breakeven_carbon_price(
            base_schedule=unprofitable,
            discount_rate=0.10,
            search_upper=5000.0,
        )
        assert bp is None

    def test_breakeven_returns_none_for_always_positive(self):
        """Returns None when NPV stays positive across entire search range."""
        # Tiny emissions => carbon cost barely dents NPV
        tiny_emissions = build_cash_flow_schedule(
            years=list(range(6)),
            production_boe_per_year=[0.0] + [50_000.0] * 5,
            oil_price_usd_per_boe=70.0,
            opex_usd_per_boe=0.0,  # zero opex — very profitable
            capex_by_year=[10_000.0] + [0.0] * 5,  # tiny capex
            carbon_cost_usd_per_tonne=0.0,
            scope1_tco2_per_boe=1e-9,
            scope2_tco2_per_boe=1e-9,
        )
        bp = breakeven_carbon_price(
            base_schedule=tiny_emissions,
            discount_rate=0.10,
            search_upper=10.0,  # very small search range
        )
        assert bp is None


# ---------------------------------------------------------------------------
# tornado_sensitivity
# ---------------------------------------------------------------------------


class TestTornadoSensitivity:
    """Tests for tornado chart sensitivity data generation."""

    def _base_kwargs(self):
        return dict(
            years=list(range(6)),
            production_boe_per_year=[0.0] + [50_000.0] * 5,
            oil_price_usd_per_boe=70.0,
            opex_usd_per_boe=15.0,
            capex_by_year=[2_000_000.0] + [0.0] * 5,
            carbon_cost_usd_per_tonne=30.0,
            scope1_tco2_per_boe=0.02,
            scope2_tco2_per_boe=0.03,
            discount_rate=0.10,
        )

    def test_tornado_returns_list_of_entries(self):
        """tornado_sensitivity returns a list of TornadoEntry objects."""
        entries = tornado_sensitivity(**self._base_kwargs())
        assert isinstance(entries, list)
        assert len(entries) > 0
        for entry in entries:
            assert isinstance(entry, TornadoEntry)

    def test_tornado_entry_fields(self):
        """Each TornadoEntry has required fields."""
        entries = tornado_sensitivity(**self._base_kwargs())
        for entry in entries:
            assert hasattr(entry, "parameter")
            assert hasattr(entry, "low_npv")
            assert hasattr(entry, "high_npv")
            assert hasattr(entry, "base_npv")
            assert hasattr(entry, "swing")

    def test_tornado_swing_is_absolute_range(self):
        """Swing = abs(high_npv - low_npv)."""
        entries = tornado_sensitivity(**self._base_kwargs())
        for entry in entries:
            expected_swing = abs(entry.high_npv - entry.low_npv)
            assert entry.swing == pytest.approx(expected_swing, rel=1e-6)

    def test_tornado_sorted_by_swing_descending(self):
        """Entries sorted by swing (largest first) for standard tornado chart."""
        entries = tornado_sensitivity(**self._base_kwargs())
        swings = [e.swing for e in entries]
        assert swings == sorted(swings, reverse=True)

    def test_tornado_includes_carbon_price_parameter(self):
        """Carbon price must appear as a tornado parameter."""
        entries = tornado_sensitivity(**self._base_kwargs())
        names = [e.parameter for e in entries]
        assert any("carbon" in n.lower() for n in names)

    def test_tornado_includes_oil_price_parameter(self):
        """Oil price must appear as a tornado parameter."""
        entries = tornado_sensitivity(**self._base_kwargs())
        names = [e.parameter for e in entries]
        assert any("oil" in n.lower() or "price" in n.lower() for n in names)

    def test_tornado_high_npv_gt_low_npv_for_positive_drivers(self):
        """For revenue-driving parameters, high scenario NPV > low scenario NPV."""
        entries = tornado_sensitivity(**self._base_kwargs())
        oil_entry = next(e for e in entries if "oil" in e.parameter.lower())
        assert oil_entry.high_npv > oil_entry.low_npv

    def test_tornado_carbon_high_npv_lt_low_npv(self):
        """Higher carbon price reduces NPV — high scenario NPV < low scenario NPV."""
        entries = tornado_sensitivity(**self._base_kwargs())
        carbon_entry = next(e for e in entries if "carbon" in e.parameter.lower())
        assert carbon_entry.high_npv < carbon_entry.low_npv
