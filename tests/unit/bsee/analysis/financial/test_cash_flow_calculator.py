"""Tests for cash flow calculator dataclasses, enums, and pure helpers."""

import pytest

from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
    CashFlowCalculator,
    DevelopmentType,
    FinancialParameters,
)


# ---------------------------------------------------------------------------
# DevelopmentType enum
# ---------------------------------------------------------------------------

class TestDevelopmentType:
    def test_subsea(self):
        assert DevelopmentType.SUBSEA.value == "subsea"

    def test_dry_tree(self):
        assert DevelopmentType.DRY_TREE.value == "dry_tree"

    def test_members(self):
        assert len(DevelopmentType) == 2


# ---------------------------------------------------------------------------
# FinancialParameters dataclass
# ---------------------------------------------------------------------------

class TestFinancialParameters:
    def test_defaults(self):
        fp = FinancialParameters()
        assert fp.wti_base_price == 75.0
        assert fp.royalty_rate == 0.0
        assert fp.severance_tax_rate == 0.0
        assert fp.corporate_tax_rate == 0.21
        assert fp.subsea_opex_per_bbl == 16.0
        assert fp.dry_opex_per_bbl == 10.0
        assert fp.fixed_opex_usd_monthly == 0.0
        assert fp.modu_dayrate_usd == 250000.0
        assert fp.dry_dayrate_usd == 150000.0

    def test_facilities_defaults(self):
        fp = FinancialParameters()
        assert fp.host_subsea_mm == 0.0
        assert fp.host_dry_mm == 0.0
        assert fp.surf_per_well_mm == 0.0
        assert fp.subsea_pump_mm == 0.0
        assert fp.dry_well_system_per_producer_mm == 0.0

    def test_timing_defaults(self):
        fp = FinancialParameters()
        assert fp.host_prefo_months == 24
        assert fp.surf_prefo_months == 12

    def test_discount_defaults(self):
        fp = FinancialParameters()
        assert fp.discount_rate_annual == 0.10
        assert fp.mirr_finance_rate_annual == 0.10
        assert fp.mirr_reinvest_rate_annual == 0.10

    def test_custom_values(self):
        fp = FinancialParameters(
            wti_base_price=80.0,
            royalty_rate=0.1875,
            modu_dayrate_usd=300000.0,
        )
        assert fp.wti_base_price == 80.0
        assert fp.royalty_rate == 0.1875
        assert fp.modu_dayrate_usd == 300000.0

    def test_get_monthly_discount_rate(self):
        fp = FinancialParameters(discount_rate_annual=0.10)
        monthly = fp.get_monthly_discount_rate()
        # (1.10)^(1/12) - 1 ~ 0.007974
        assert monthly == pytest.approx(0.007974, abs=0.0001)

    def test_get_monthly_discount_rate_zero(self):
        fp = FinancialParameters(discount_rate_annual=0.0)
        assert fp.get_monthly_discount_rate() == 0.0

    def test_get_monthly_finance_rate(self):
        fp = FinancialParameters(mirr_finance_rate_annual=0.10)
        monthly = fp.get_monthly_finance_rate()
        assert monthly == pytest.approx(0.007974, abs=0.0001)

    def test_get_monthly_reinvest_rate(self):
        fp = FinancialParameters(mirr_reinvest_rate_annual=0.10)
        monthly = fp.get_monthly_reinvest_rate()
        assert monthly == pytest.approx(0.007974, abs=0.0001)


# ---------------------------------------------------------------------------
# CashFlowCalculator init
# ---------------------------------------------------------------------------

class TestCashFlowCalculator:
    def test_default_init(self):
        calc = CashFlowCalculator()
        assert isinstance(calc.params, FinancialParameters)
        assert calc.wti_prices == {}

    def test_custom_params(self):
        fp = FinancialParameters(wti_base_price=80.0)
        calc = CashFlowCalculator(params=fp)
        assert calc.params.wti_base_price == 80.0

    def test_set_wti_prices(self):
        import pandas as pd
        calc = CashFlowCalculator()
        prices = {pd.Timestamp("2024-01-01"): 75.0, pd.Timestamp("2024-02-01"): 78.0}
        calc.set_wti_prices(prices)
        assert len(calc.wti_prices) == 2
        assert calc.wti_prices[pd.Timestamp("2024-01-01")] == 75.0


# ---------------------------------------------------------------------------
# calculate_npv standalone function
# ---------------------------------------------------------------------------

class TestCalculateNpv:
    def test_empty_array(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_npv,
        )
        import numpy as np
        result = calculate_npv(np.array([]), 0.01)
        assert result == 0.0

    def test_single_cash_flow(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_npv,
        )
        import numpy as np
        # Single cash flow at period 0 => NPV = cash_flow / 1.0
        result = calculate_npv(np.array([1000.0]), 0.01)
        assert result == pytest.approx(1000.0)

    def test_multiple_cash_flows(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_npv,
        )
        import numpy as np
        # -1000 at t=0, +600 at t=1, +600 at t=2 with 10% monthly rate
        flows = np.array([-1000.0, 600.0, 600.0])
        npv = calculate_npv(flows, 0.10)
        # -1000/1.0 + 600/1.1 + 600/1.21 = -1000 + 545.45 + 495.87 = 41.32
        assert npv == pytest.approx(41.32, abs=0.5)

    def test_zero_discount_rate(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_npv,
        )
        import numpy as np
        flows = np.array([100.0, 200.0, 300.0])
        npv = calculate_npv(flows, 0.0)
        assert npv == pytest.approx(600.0)


# ---------------------------------------------------------------------------
# calculate_mirr standalone function
# ---------------------------------------------------------------------------

class TestCalculateMirr:
    def test_single_period(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_mirr,
        )
        import numpy as np
        result = calculate_mirr(np.array([100.0]), 0.01, 0.01)
        assert np.isnan(result)

    def test_all_positive(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_mirr,
        )
        import numpy as np
        # All positive => pv_negative=0 => NaN
        result = calculate_mirr(np.array([100.0, 200.0, 300.0]), 0.01, 0.01)
        assert np.isnan(result)

    def test_all_negative(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_mirr,
        )
        import numpy as np
        # All negative => fv_positive=0 => NaN
        result = calculate_mirr(np.array([-100.0, -200.0]), 0.01, 0.01)
        assert np.isnan(result)

    def test_typical_investment(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_mirr,
        )
        import numpy as np
        # Initial investment then positive returns
        flows = np.array([-1000.0, 300.0, 400.0, 500.0])
        result = calculate_mirr(flows, 0.01, 0.01)
        assert np.isfinite(result)
        assert result > 0  # Should be positive since total returns > investment

    def test_empty_flows(self):
        from worldenergydata.bsee.analysis.financial.cash_flow_calculator import (
            calculate_mirr,
        )
        import numpy as np
        result = calculate_mirr(np.array([]), 0.01, 0.01)
        assert np.isnan(result)


# ---------------------------------------------------------------------------
# CashFlowCalculator._get_date_range
# ---------------------------------------------------------------------------

class TestGetDateRange:
    def test_empty_inputs(self):
        import pandas as pd
        calc = CashFlowCalculator()
        result = calc._get_date_range(pd.DataFrame(), {})
        assert len(result) == 1
        assert result[0] == pd.Timestamp("2020-01-01")

    def test_from_drilling_data(self):
        import pandas as pd
        calc = CashFlowCalculator()
        drilling = {
            "well1": {
                "drill_days": {
                    pd.Timestamp("2024-01-01"): 15,
                    pd.Timestamp("2024-03-01"): 10,
                },
                "comp_days": {
                    pd.Timestamp("2024-04-01"): 5,
                },
            }
        }
        result = calc._get_date_range(pd.DataFrame(), drilling)
        assert result[0] == pd.Timestamp("2024-01-01")
        assert result[-1] == pd.Timestamp("2024-04-01")
        assert len(result) == 4  # Jan, Feb, Mar, Apr

    def test_from_production_df(self):
        import pandas as pd
        calc = CashFlowCalculator()
        idx = pd.date_range("2024-01-01", "2024-06-01", freq="MS")
        prod_df = pd.DataFrame({"well1": range(6)}, index=idx)
        prod_df.index.name = "YearMonth"
        result = calc._get_date_range(prod_df, {})
        assert len(result) == 6


# ---------------------------------------------------------------------------
# CashFlowCalculator.calculate_monthly_cash_flow (minimal)
# ---------------------------------------------------------------------------

class TestCalculateMonthlyCashFlow:
    def test_empty_production(self):
        import pandas as pd
        calc = CashFlowCalculator()
        drilling = {
            "well1": {
                "drill_days": {pd.Timestamp("2024-01-01"): 30},
                "comp_days": {},
            }
        }
        result = calc.calculate_monthly_cash_flow(
            pd.DataFrame(),
            drilling,
            DevelopmentType.SUBSEA,
        )
        assert "Gross_Oil_bbls" in result.columns
        assert "Revenue_Gross" in result.columns
        assert "Net_Cash_Flow" in result.columns
        assert "Cum_Cash_Flow" in result.columns

    def test_with_production(self):
        import pandas as pd
        calc = CashFlowCalculator()
        idx = pd.date_range("2024-01-01", "2024-03-01", freq="MS")
        prod_df = pd.DataFrame({"well1": [100.0, 200.0, 300.0]}, index=idx)
        prod_df.index.name = "YearMonth"
        result = calc.calculate_monthly_cash_flow(
            prod_df, {}, DevelopmentType.DRY_TREE
        )
        assert result["Gross_Oil_bbls"].sum() == 600.0
        assert result["Revenue_Gross"].sum() > 0

    def test_subsea_vs_dry_opex(self):
        import pandas as pd
        calc = CashFlowCalculator(
            params=FinancialParameters(subsea_opex_per_bbl=16.0, dry_opex_per_bbl=10.0)
        )
        idx = pd.date_range("2024-01-01", periods=1, freq="MS")
        prod_df = pd.DataFrame({"well1": [1000.0]}, index=idx)
        prod_df.index.name = "YearMonth"

        subsea = calc.calculate_monthly_cash_flow(
            prod_df, {}, DevelopmentType.SUBSEA
        )
        dry = calc.calculate_monthly_cash_flow(
            prod_df, {}, DevelopmentType.DRY_TREE
        )
        assert subsea["OPEX_Var"].iloc[0] == 16000.0
        assert dry["OPEX_Var"].iloc[0] == 10000.0


# ---------------------------------------------------------------------------
# CashFlowCalculator.calculate_financial_metrics
# ---------------------------------------------------------------------------

class TestCalculateFinancialMetrics:
    def test_basic_metrics(self):
        import pandas as pd
        calc = CashFlowCalculator()
        idx = pd.date_range("2024-01-01", "2024-03-01", freq="MS")
        prod_df = pd.DataFrame({"well1": [1000.0, 2000.0, 3000.0]}, index=idx)
        prod_df.index.name = "YearMonth"
        cf = calc.calculate_monthly_cash_flow(prod_df, {}, DevelopmentType.SUBSEA)
        metrics = calc.calculate_financial_metrics(cf)
        assert "total_oil_bbls" in metrics
        assert "total_revenue" in metrics
        assert "npv" in metrics
        assert "total_opex" in metrics
        assert "total_capex" in metrics
        assert metrics["total_oil_bbls"] == 6000.0
