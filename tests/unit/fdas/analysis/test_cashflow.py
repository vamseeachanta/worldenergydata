"""Tests for FDAS monthly cashflow modeling engine."""

from datetime import datetime

import pandas as pd
import pytest

from worldenergydata.common.exceptions import ProcessingError
from worldenergydata.fdas.analysis.cashflow import (
    CashflowEngine,
    CashflowError,
    MonthlyCashflowModel,
)
from worldenergydata.fdas.core.config import AssumptionsManager


# ---------------------------------------------------------------------------
# CashflowError
# ---------------------------------------------------------------------------

class TestCashflowError:
    def test_inherits_processing_error(self):
        err = CashflowError("test")
        assert isinstance(err, ProcessingError)

    def test_default_code(self):
        err = CashflowError("test")
        assert err.code == "FDAS_CASHFLOW_ERROR"

    def test_default_operation(self):
        err = CashflowError("test")
        assert err.operation == "cashflow_calculation"


# ---------------------------------------------------------------------------
# MonthlyCashflowModel
# ---------------------------------------------------------------------------

class TestMonthlyCashflowModel:
    def test_defaults(self):
        m = MonthlyCashflowModel(year_month="2024-01")
        assert m.oil_production_bbl == 0.0
        assert m.oil_revenue_usd == 0.0
        assert m.net_cashflow_usd == 0.0

    def test_calculate_net_cashflow_positive(self):
        m = MonthlyCashflowModel(
            year_month="2024-01",
            oil_revenue_usd=1000000,
            royalty_usd=188000,
            variable_opex_usd=120000,
            fixed_opex_usd=50000,
            drilling_capex_usd=0,
            facilities_capex_usd=0,
            host_capex_usd=0,
        )
        net = m.calculate_net_cashflow()
        assert net == 642000.0
        assert m.net_cashflow_usd == 642000.0

    def test_calculate_net_cashflow_negative(self):
        m = MonthlyCashflowModel(
            year_month="2024-01",
            oil_revenue_usd=0,
            drilling_capex_usd=500000,
            host_capex_usd=200000,
        )
        net = m.calculate_net_cashflow()
        assert net == -700000.0

    def test_calculate_net_cashflow_zero(self):
        m = MonthlyCashflowModel(year_month="2024-01")
        assert m.calculate_net_cashflow() == 0.0


# ---------------------------------------------------------------------------
# CashflowEngine init
# ---------------------------------------------------------------------------

class TestCashflowEngineInit:
    def test_default_dev_system(self):
        mgr = AssumptionsManager()
        engine = CashflowEngine(mgr)
        assert engine.dev_system == "subsea15"

    def test_custom_dev_system(self):
        mgr = AssumptionsManager()
        engine = CashflowEngine(mgr, dev_system="dry")
        assert engine.dev_system == "dry"


# ---------------------------------------------------------------------------
# calculate_host_capex_timing
# ---------------------------------------------------------------------------

class TestCalculateHostCapexTiming:
    def _engine(self):
        return CashflowEngine(AssumptionsManager())

    def test_zero_capex_returns_empty(self):
        result = self._engine().calculate_host_capex_timing(0.0, datetime(2025, 1, 1))
        assert result == {}

    def test_distributes_evenly(self):
        result = self._engine().calculate_host_capex_timing(
            12.0, datetime(2025, 1, 1), months_before_first_oil=12,
        )
        assert len(result) == 12
        for val in result.values():
            assert val == pytest.approx(1.0)

    def test_goes_backwards_from_first_oil(self):
        result = self._engine().calculate_host_capex_timing(
            6.0, datetime(2025, 6, 1), months_before_first_oil=3,
        )
        assert "2025-06" in result
        assert "2025-05" in result
        assert "2025-04" in result

    def test_crosses_year_boundary(self):
        result = self._engine().calculate_host_capex_timing(
            2.0, datetime(2025, 1, 1), months_before_first_oil=2,
        )
        assert "2025-01" in result
        assert "2024-12" in result


# ---------------------------------------------------------------------------
# calculate_drilling_capex
# ---------------------------------------------------------------------------

class TestCalculateDrillingCapex:
    def _engine(self):
        return CashflowEngine(AssumptionsManager())

    def test_simple_calculation(self):
        result = self._engine().calculate_drilling_capex(
            {"2024-01": 30, "2024-02": 28}, 0.8,
        )
        assert result["2024-01"] == pytest.approx(24.0)
        assert result["2024-02"] == pytest.approx(22.4)

    def test_empty_drilling_days(self):
        result = self._engine().calculate_drilling_capex({}, 0.8)
        assert result == {}

    def test_zero_rig_rate(self):
        result = self._engine().calculate_drilling_capex({"2024-01": 30}, 0.0)
        assert result["2024-01"] == 0.0


# ---------------------------------------------------------------------------
# calculate_facilities_capex
# ---------------------------------------------------------------------------

class TestCalculateFacilitiesCapex:
    def _engine(self):
        return CashflowEngine(AssumptionsManager())

    def test_simple(self):
        result = self._engine().calculate_facilities_capex(
            {"2024-06": 2, "2024-12": 1}, 8.0,
        )
        assert result["2024-06"] == 16.0
        assert result["2024-12"] == 8.0

    def test_empty(self):
        result = self._engine().calculate_facilities_capex({}, 8.0)
        assert result == {}


# ---------------------------------------------------------------------------
# calculate_revenue
# ---------------------------------------------------------------------------

class TestCalculateRevenue:
    def _engine(self):
        return CashflowEngine(AssumptionsManager())

    def test_basic_revenue(self):
        result = self._engine().calculate_revenue(
            {"2024-01": 100000}, {"2024-01": 75.0},
        )
        assert result["2024-01"] == pytest.approx(7500000.0)

    def test_with_differential(self):
        result = self._engine().calculate_revenue(
            {"2024-01": 100000}, {"2024-01": 75.0}, oil_differential=-2.0,
        )
        assert result["2024-01"] == pytest.approx(7300000.0)

    def test_missing_price_uses_default(self):
        result = self._engine().calculate_revenue(
            {"2024-01": 100000}, {},
        )
        # Default WTI price is 75.0
        assert result["2024-01"] == pytest.approx(7500000.0)


# ---------------------------------------------------------------------------
# calculate_royalty
# ---------------------------------------------------------------------------

class TestCalculateRoyalty:
    def _engine(self):
        return CashflowEngine(AssumptionsManager())

    def test_explicit_rate(self):
        result = self._engine().calculate_royalty(
            {"2024-01": 7500000}, royalty_rate=0.188,
        )
        assert result["2024-01"] == pytest.approx(1410000.0)

    def test_default_rate_from_assumptions(self):
        result = self._engine().calculate_royalty({"2024-01": 1000000})
        # subsea15 default royalty rate = 0.188
        assert result["2024-01"] == pytest.approx(188000.0)


# ---------------------------------------------------------------------------
# calculate_variable_opex
# ---------------------------------------------------------------------------

class TestCalculateVariableOpex:
    def _engine(self):
        return CashflowEngine(AssumptionsManager())

    def test_explicit_rate(self):
        result = self._engine().calculate_variable_opex(
            {"2024-01": 100000}, opex_per_bbl=12.0,
        )
        assert result["2024-01"] == pytest.approx(1200000.0)

    def test_default_from_assumptions(self):
        result = self._engine().calculate_variable_opex({"2024-01": 100000})
        assert result["2024-01"] > 0


# ---------------------------------------------------------------------------
# calculate_fixed_opex
# ---------------------------------------------------------------------------

class TestCalculateFixedOpex:
    def _engine(self):
        return CashflowEngine(AssumptionsManager())

    def test_explicit_annual(self):
        result = self._engine().calculate_fixed_opex(
            "2024-01", "2024-03", annual_fixed_opex_mm=12.0,
        )
        assert len(result) == 3
        for val in result.values():
            assert val == pytest.approx(1.0)

    def test_single_month(self):
        result = self._engine().calculate_fixed_opex(
            "2024-06", "2024-06", annual_fixed_opex_mm=12.0,
        )
        assert len(result) == 1

    def test_default_from_assumptions(self):
        result = self._engine().calculate_fixed_opex("2024-01", "2024-12")
        assert len(result) == 12
