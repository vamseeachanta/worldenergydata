"""
Tests for SME financial analysis cash flow calculator
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from worldenergydata.modules.bsee.analysis.financial.cash_flow_calculator import (
    CashFlowCalculator,
    DevelopmentType,
    FinancialParameters,
    calculate_mirr,
    calculate_npv,
)


class TestFinancialParameters:
    """Test the FinancialParameters dataclass"""

    def test_default_parameters(self):
        """Test default financial parameters"""
        params = FinancialParameters()
        assert params.wti_base_price == 75.0
        assert params.royalty_rate == 0.0
        assert params.severance_tax_rate == 0.0
        assert params.discount_rate_annual == 0.10
        assert params.corporate_tax_rate == 0.21

    def test_custom_parameters(self):
        """Test custom financial parameters"""
        params = FinancialParameters(
            wti_base_price=80.0,
            royalty_rate=0.1875,
            severance_tax_rate=0.05,
            discount_rate_annual=0.12,
        )
        assert params.wti_base_price == 80.0
        assert params.royalty_rate == 0.1875
        assert params.severance_tax_rate == 0.05
        assert params.discount_rate_annual == 0.12

    def test_monthly_discount_rate(self):
        """Test monthly discount rate calculation"""
        params = FinancialParameters(discount_rate_annual=0.10)
        expected_monthly = (1.0 + 0.10) ** (1.0 / 12.0) - 1.0
        assert abs(params.get_monthly_discount_rate() - expected_monthly) < 1e-10


class TestCashFlowCalculator:
    """Test the CashFlowCalculator class"""

    @pytest.fixture
    def sample_production_data(self):
        """Create sample production data"""
        dates = pd.date_range("2020-01-01", periods=12, freq="MS")
        df = pd.DataFrame(
            {
                "WELL_1": [1000, 950, 900, 850, 800, 750, 700, 650, 600, 550, 500, 450],
                "WELL_2": [0, 0, 0, 500, 480, 460, 440, 420, 400, 380, 360, 340],
            },
            index=dates,
        )
        df.index.name = "YearMonth"
        return df

    @pytest.fixture
    def sample_drilling_data(self):
        """Create sample drilling and completion data"""
        return {
            "WELL_1": {
                "drill_days": {pd.Timestamp("2019-11-01"): 30},
                "comp_days": {pd.Timestamp("2019-12-01"): 20},
            },
            "WELL_2": {
                "drill_days": {pd.Timestamp("2020-01-01"): 25},
                "comp_days": {pd.Timestamp("2020-02-01"): 15},
            },
        }

    @pytest.fixture
    def calculator(self):
        """Create a CashFlowCalculator instance"""
        params = FinancialParameters(
            wti_base_price=75.0,
            royalty_rate=0.1875,
            severance_tax_rate=0.05,
            subsea_opex_per_bbl=16.0,
            dry_opex_per_bbl=10.0,
            modu_dayrate_usd=250000.0,
            dry_dayrate_usd=150000.0,
        )
        return CashFlowCalculator(params)

    def test_initialization(self, calculator):
        """Test calculator initialization"""
        assert calculator.params.wti_base_price == 75.0
        assert calculator.params.royalty_rate == 0.1875
        assert calculator.wti_prices == {}

    def test_set_wti_prices(self, calculator):
        """Test setting WTI prices"""
        prices = {
            pd.Timestamp("2020-01-01"): 80.0,
            pd.Timestamp("2020-02-01"): 78.0,
            pd.Timestamp("2020-03-01"): 76.0,
        }
        calculator.set_wti_prices(prices)
        assert calculator.wti_prices == prices

    def test_calculate_revenue(self, calculator, sample_production_data):
        """Test revenue calculation"""
        # Set custom WTI prices
        prices = {date: 80.0 for date in sample_production_data.index}
        calculator.set_wti_prices(prices)

        result = calculator.calculate_monthly_cash_flow(
            production_df=sample_production_data,
            drilling_data={},
            development_type=DevelopmentType.SUBSEA,
        )

        assert "Gross_Oil_bbls" in result
        assert "Revenue_Gross" in result
        assert "Revenue_Net" in result

        # Check gross oil calculation
        expected_gross = sample_production_data.sum(axis=1)
        pd.testing.assert_series_equal(
            result["Gross_Oil_bbls"], expected_gross, check_names=False
        )

        # Check revenue calculation
        expected_revenue_gross = expected_gross * 80.0
        pd.testing.assert_series_equal(
            result["Revenue_Gross"], expected_revenue_gross, check_names=False
        )

        # Check net revenue (after royalties and severance tax)
        deductions = expected_revenue_gross * (0.1875 + 0.05)
        expected_revenue_net = expected_revenue_gross - deductions
        pd.testing.assert_series_equal(
            result["Revenue_Net"], expected_revenue_net, check_names=False
        )

    def test_calculate_opex(self, calculator, sample_production_data):
        """Test OPEX calculation"""
        calculator.params.fixed_opex_usd_monthly = 100000.0

        result = calculator.calculate_monthly_cash_flow(
            production_df=sample_production_data,
            drilling_data={},
            development_type=DevelopmentType.SUBSEA,
        )

        assert "OPEX_Var" in result
        assert "OPEX_Fixed" in result
        assert "OPEX" in result

        # Check variable OPEX (subsea rate)
        expected_var_opex = sample_production_data.sum(axis=1) * 16.0
        pd.testing.assert_series_equal(
            result["OPEX_Var"], expected_var_opex, check_names=False
        )

        # Check fixed OPEX
        assert (result["OPEX_Fixed"] == 100000.0).all()

        # Check total OPEX
        expected_total_opex = expected_var_opex + 100000.0
        pd.testing.assert_series_equal(
            result["OPEX"], expected_total_opex, check_names=False
        )

    def test_calculate_capex_drilling(
        self, calculator, sample_production_data, sample_drilling_data
    ):
        """Test CAPEX calculation for drilling and completion"""
        result = calculator.calculate_monthly_cash_flow(
            production_df=sample_production_data,
            drilling_data=sample_drilling_data,
            development_type=DevelopmentType.SUBSEA,
        )

        assert "CAPEX_Drill" in result
        assert "CAPEX_Comp" in result
        assert "CAPEX" in result

        # Check drilling CAPEX
        assert result.loc[pd.Timestamp("2019-11-01"), "CAPEX_Drill"] == 30 * 250000.0
        assert result.loc[pd.Timestamp("2020-01-01"), "CAPEX_Drill"] == 25 * 250000.0

        # Check completion CAPEX
        assert result.loc[pd.Timestamp("2019-12-01"), "CAPEX_Comp"] == 20 * 250000.0
        assert result.loc[pd.Timestamp("2020-02-01"), "CAPEX_Comp"] == 15 * 250000.0

    def test_calculate_net_cash_flow(
        self, calculator, sample_production_data, sample_drilling_data
    ):
        """Test net cash flow calculation"""
        result = calculator.calculate_monthly_cash_flow(
            production_df=sample_production_data,
            drilling_data=sample_drilling_data,
            development_type=DevelopmentType.SUBSEA,
        )

        assert "Net_Cash_Flow" in result
        assert "Cum_Cash_Flow" in result
        assert "Tax_Savings" in result

        # Check tax savings calculation
        expected_tax_savings = result["CAPEX"] * 0.21
        pd.testing.assert_series_equal(
            result["Tax_Savings"], expected_tax_savings, check_names=False
        )

        # Check net cash flow calculation
        expected_ncf = (
            result["Revenue_Net"]
            - result["OPEX"]
            - result["CAPEX"]
            + result["Tax_Savings"]
        )
        pd.testing.assert_series_equal(
            result["Net_Cash_Flow"], expected_ncf, check_names=False
        )

        # Check cumulative cash flow
        expected_cumulative = expected_ncf.cumsum()
        pd.testing.assert_series_equal(
            result["Cum_Cash_Flow"], expected_cumulative, check_names=False
        )

    def test_development_type_opex(self, calculator, sample_production_data):
        """Test different OPEX rates for different development types"""
        # Test subsea development
        result_subsea = calculator.calculate_monthly_cash_flow(
            production_df=sample_production_data,
            drilling_data={},
            development_type=DevelopmentType.SUBSEA,
        )

        # Test dry tree development
        result_dry = calculator.calculate_monthly_cash_flow(
            production_df=sample_production_data,
            drilling_data={},
            development_type=DevelopmentType.DRY_TREE,
        )

        # Variable OPEX should be different
        gross_oil = sample_production_data.sum(axis=1)
        assert (result_subsea["OPEX_Var"] == gross_oil * 16.0).all()
        assert (result_dry["OPEX_Var"] == gross_oil * 10.0).all()

    def test_facilities_capex(self, calculator, sample_production_data):
        """Test facilities CAPEX calculation"""
        calculator.params.host_subsea_mm = 100.0  # $100MM host facility
        calculator.params.surf_per_well_mm = 10.0  # $10MM per well SURF

        # Determine first oil date
        fo_date = pd.Timestamp("2020-04-01")

        result = calculator.calculate_monthly_cash_flow(
            production_df=sample_production_data,
            drilling_data={},
            development_type=DevelopmentType.SUBSEA,
            first_oil_date=fo_date,
            producer_count=2,
        )

        assert "CAPEX_Facilities" in result

        # Check that facilities CAPEX is allocated before first oil
        facilities_capex = result["CAPEX_Facilities"]
        assert facilities_capex.sum() > 0
        assert facilities_capex[facilities_capex.index >= fo_date].sum() == 0


class TestNPVCalculation:
    """Test NPV calculation functions"""

    def test_npv_calculation_basic(self):
        """Test basic NPV calculation"""
        cash_flows = np.array([100, 100, 100, 100, 100])
        monthly_rate = 0.01

        npv = calculate_npv(cash_flows, monthly_rate)

        # Manual calculation
        expected = sum(cf / (1.01**i) for i, cf in enumerate(cash_flows))
        assert abs(npv - expected) < 0.01

    def test_npv_with_negative_flows(self):
        """Test NPV with negative cash flows"""
        cash_flows = np.array([-1000, 200, 300, 400, 500])
        monthly_rate = 0.01

        npv = calculate_npv(cash_flows, monthly_rate)

        # NPV should handle negative flows correctly
        # With these cash flows, NPV is actually positive (around 360)
        assert npv > 0  # The positive cash flows outweigh the initial investment

    def test_npv_empty_array(self):
        """Test NPV with empty cash flows"""
        cash_flows = np.array([])
        monthly_rate = 0.01

        npv = calculate_npv(cash_flows, monthly_rate)
        assert npv == 0.0


class TestMIRRCalculation:
    """Test MIRR calculation functions"""

    def test_mirr_calculation_basic(self):
        """Test basic MIRR calculation"""
        cash_flows = np.array([-1000, 300, 400, 500, 600])
        finance_rate = 0.01
        reinvest_rate = 0.015

        mirr = calculate_mirr(cash_flows, finance_rate, reinvest_rate)

        assert not np.isnan(mirr)
        assert mirr > 0  # Should be positive for profitable project

    def test_mirr_no_positive_flows(self):
        """Test MIRR with no positive cash flows"""
        cash_flows = np.array([-1000, -100, -100, -100])
        finance_rate = 0.01
        reinvest_rate = 0.015

        mirr = calculate_mirr(cash_flows, finance_rate, reinvest_rate)
        assert np.isnan(mirr)

    def test_mirr_no_negative_flows(self):
        """Test MIRR with no negative cash flows"""
        cash_flows = np.array([100, 100, 100, 100])
        finance_rate = 0.01
        reinvest_rate = 0.015

        mirr = calculate_mirr(cash_flows, finance_rate, reinvest_rate)
        assert np.isnan(mirr)

    def test_mirr_single_period(self):
        """Test MIRR with single period"""
        cash_flows = np.array([100])
        finance_rate = 0.01
        reinvest_rate = 0.015

        mirr = calculate_mirr(cash_flows, finance_rate, reinvest_rate)
        assert np.isnan(mirr)


class TestIntegration:
    """Integration tests for the cash flow calculator"""

    def test_full_financial_analysis(self):
        """Test complete financial analysis workflow"""
        # Create test data
        dates = pd.date_range("2020-01-01", periods=24, freq="MS")
        production_df = pd.DataFrame(
            {
                "WELL_1": [0] * 3 + [1000] * 12 + [800] * 9,
                "WELL_2": [0] * 6 + [800] * 12 + [600] * 6,
            },
            index=dates,
        )
        production_df.index.name = "YearMonth"

        drilling_data = {
            "WELL_1": {
                "drill_days": {pd.Timestamp("2019-10-01"): 30},
                "comp_days": {pd.Timestamp("2019-11-01"): 20},
            },
            "WELL_2": {
                "drill_days": {pd.Timestamp("2019-12-01"): 35},
                "comp_days": {pd.Timestamp("2020-01-01"): 25},
            },
        }

        # Create calculator with realistic parameters
        params = FinancialParameters(
            wti_base_price=75.0,
            royalty_rate=0.1875,
            severance_tax_rate=0.05,
            subsea_opex_per_bbl=16.0,
            dry_opex_per_bbl=10.0,
            modu_dayrate_usd=250000.0,
            dry_dayrate_usd=150000.0,
            corporate_tax_rate=0.21,
            discount_rate_annual=0.10,
            mirr_finance_rate_annual=0.08,
            mirr_reinvest_rate_annual=0.12,
        )

        calculator = CashFlowCalculator(params)

        # Calculate cash flows
        result = calculator.calculate_monthly_cash_flow(
            production_df=production_df,
            drilling_data=drilling_data,
            development_type=DevelopmentType.SUBSEA,
        )

        # Calculate financial metrics
        metrics = calculator.calculate_financial_metrics(result)

        # Verify metrics are calculated
        assert "npv" in metrics
        assert "mirr_annual" in metrics
        assert "total_oil_bbls" in metrics
        assert "total_capex" in metrics
        assert "total_opex" in metrics
        assert "total_revenue" in metrics

        # Verify values are reasonable
        assert metrics["total_oil_bbls"] > 0
        assert metrics["total_revenue"] > 0
        assert metrics["total_capex"] > 0
        assert metrics["total_opex"] > 0
        assert not np.isnan(metrics["npv"])
