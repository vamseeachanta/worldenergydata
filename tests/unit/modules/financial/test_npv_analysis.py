"""
Unit tests for NPV (Net Present Value) analysis module.

Tests financial analysis functions including NPV calculations,
cash flow analysis, and scenario testing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import pandas as pd
import numpy as np
import numpy_financial as npf
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))

from tests.test_markers import unit, smoke, performance


@unit
class TestNPVAnalysis:
    """Unit tests for NPV analysis functions."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.sample_cash_flows = [-1000000, 300000, 400000, 500000, 300000]
        self.discount_rates = [0.05, 0.10, 0.15, 0.20]
        self.expected_npv_10pct = npf.npv(0.10, self.sample_cash_flows)
    
    def test_npv_calculation_basic(self):
        """Test basic NPV calculation."""
        rate = 0.10
        npv_result = npf.npv(rate, self.sample_cash_flows)
        
        assert isinstance(npv_result, (float, np.floating))
        assert npv_result == pytest.approx(self.expected_npv_10pct)
    
    @pytest.mark.parametrize("rate,expected_sign", [
        (0.05, 1),   # Low rate, positive NPV expected
        (0.30, -1),  # High rate, negative NPV expected
    ])
    def test_npv_with_different_rates(self, rate, expected_sign):
        """Test NPV calculation with various discount rates."""
        npv_result = npf.npv(rate, self.sample_cash_flows)
        
        if expected_sign > 0:
            assert npv_result > 0, f"NPV should be positive at {rate:.1%} discount rate"
        else:
            assert npv_result < 0, f"NPV should be negative at {rate:.1%} discount rate"
    
    def test_npv_with_zero_rate(self):
        """Test NPV with zero discount rate (should equal sum of cash flows)."""
        rate = 0.0
        npv_result = npf.npv(rate, self.sample_cash_flows)
        expected = sum(self.sample_cash_flows)
        
        assert npv_result == pytest.approx(expected)
    
    def test_npv_with_empty_cash_flows(self):
        """Test NPV with empty cash flows."""
        rate = 0.10
        cash_flows = []
        npv_result = npf.npv(rate, cash_flows)
        
        assert npv_result == 0.0
    
    def test_npv_with_single_cash_flow(self):
        """Test NPV with single cash flow."""
        rate = 0.10
        cash_flows = [1000]
        npv_result = npf.npv(rate, cash_flows)
        
        assert npv_result == pytest.approx(1000)
    
    @patch('os.path.exists')
    @patch('pandas.read_excel')
    def test_load_actual_excel_data_success(self, mock_read_excel, mock_exists):
        """Test loading actual Excel data successfully."""
        # Import from tests location where custom scripts were moved
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../modules/bsee/analysis/custom_scripts'))
        from Copilot.npv_analysis import load_actual_excel_data
        
        mock_exists.return_value = True
        mock_read_excel.return_value = pd.DataFrame()
        
        cash_flows, discount_rates = load_actual_excel_data()
        
        assert cash_flows is not None
        assert discount_rates is not None
        assert len(cash_flows) > 0
        assert len(discount_rates) > 0
    
    @patch('os.path.exists')
    def test_load_actual_excel_data_file_not_found(self, mock_exists):
        """Test loading Excel data when file doesn't exist."""
        # Import from tests location where custom scripts were moved
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../modules/bsee/analysis/custom_scripts'))
        from Copilot.npv_analysis import load_actual_excel_data
        
        mock_exists.return_value = False
        
        cash_flows, discount_rates = load_actual_excel_data()
        
        assert cash_flows is None
        assert discount_rates is None
    
    @patch('Copilot.npv_analysis.load_actual_excel_data')
    def test_calculate_custom_npv_scenarios(self, mock_load):
        """Test calculating NPV scenarios."""
        # Import from tests location where custom scripts were moved
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../modules/bsee/analysis/custom_scripts'))
        from Copilot.npv_analysis import calculate_custom_npv_scenarios
        
        mock_load.return_value = (self.sample_cash_flows, self.discount_rates)
        
        npv_collection = calculate_custom_npv_scenarios()
        
        assert len(npv_collection) == len(self.discount_rates)
        for rate, npv in npv_collection:
            assert rate in self.discount_rates
            assert isinstance(npv, (float, np.floating))
    
    def test_save_results_to_file(self):
        """Test saving NPV results to file."""
        # Import from tests location where custom scripts were moved
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../modules/bsee/analysis/custom_scripts'))
        from Copilot.npv_analysis import save_results_to_file
        
        npv_collection = [(0.10, 123456.78), (0.15, -98765.43)]
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json:
                save_results_to_file(npv_collection)
                
                # Verify file operations
                mock_file.assert_called()
                mock_json.assert_called()


@unit
class TestNPVEdgeCases:
    """Test edge cases for NPV calculations."""
    
    @pytest.mark.parametrize("cash_flows", [
        [0, 0, 0, 0],           # All zeros
        [-1000, -500, -300],    # All negative
        [1000, 2000, 3000],     # All positive
        [-1e10, 1e10],          # Very large values
        [-0.01, 0.01],          # Very small values
    ])
    def test_npv_edge_case_cash_flows(self, cash_flows):
        """Test NPV with various edge case cash flows."""
        rate = 0.10
        npv_result = npf.npv(rate, cash_flows)
        
        assert isinstance(npv_result, (float, np.floating))
        assert not np.isnan(npv_result)
        assert not np.isinf(npv_result)
    
    @pytest.mark.parametrize("rate", [
        -0.99,  # Negative rate close to -1
        0.0,    # Zero rate
        0.99,   # Very high rate
        1.0,    # 100% rate
        10.0,   # Extremely high rate
    ])
    def test_npv_edge_case_rates(self, rate):
        """Test NPV with edge case discount rates."""
        cash_flows = [-1000, 500, 500, 500]
        
        if rate == -1.0:
            with pytest.raises((ValueError, ZeroDivisionError)):
                npf.npv(rate, cash_flows)
        else:
            npv_result = npf.npv(rate, cash_flows)
            assert isinstance(npv_result, (float, np.floating))
            assert not np.isnan(npv_result)


@unit
class TestFinancialMetrics:
    """Test additional financial metrics and calculations."""
    
    def test_irr_calculation(self):
        """Test Internal Rate of Return calculation."""
        cash_flows = [-1000, 300, 400, 500, 300]
        irr = npf.irr(cash_flows)
        
        assert isinstance(irr, (float, np.floating))
        assert 0 < irr < 1  # IRR should be between 0 and 100%
    
    def test_payback_period(self):
        """Test payback period calculation."""
        cash_flows = [-1000, 400, 400, 400]
        cumulative = np.cumsum(cash_flows)
        
        # Find payback period
        payback_index = np.where(cumulative >= 0)[0]
        if len(payback_index) > 0:
            payback_period = payback_index[0]
        else:
            payback_period = len(cash_flows)
        
        assert payback_period == 3  # Should payback in year 3
    
    def test_profitability_index(self):
        """Test profitability index calculation."""
        initial_investment = 1000000
        rate = 0.10
        future_cash_flows = [400000, 500000, 600000]
        
        pv_future = npf.npv(rate, [0] + future_cash_flows)
        pi = pv_future / initial_investment
        
        assert pi > 0
        assert isinstance(pi, (float, np.floating))
    
    @pytest.mark.parametrize("periods,rate,pv,expected_fv", [
        (5, 0.10, 1000, 1610.51),    # Standard case
        (10, 0.05, 1000, 1628.89),   # Longer period, lower rate
        (1, 0.10, 1000, 1100),       # Single period
    ])
    def test_future_value(self, periods, rate, pv, expected_fv):
        """Test future value calculations."""
        fv = npf.fv(rate, periods, 0, -pv)
        assert fv == pytest.approx(expected_fv, rel=0.01)


@performance
@unit
class TestNPVPerformance:
    """Performance tests for NPV calculations."""
    
    def test_npv_large_cash_flow_performance(self, benchmark):
        """Test NPV performance with large cash flow arrays."""
        # Generate large cash flow array (20 years monthly)
        cash_flows = [-10000000] + [50000] * 240
        rate = 0.10 / 12  # Monthly rate
        
        result = benchmark(npf.npv, rate, cash_flows)
        
        assert isinstance(result, (float, np.floating))
    
    def test_multiple_npv_calculations_performance(self, benchmark):
        """Test performance of multiple NPV calculations."""
        cash_flows = [-1000000, 300000, 400000, 500000, 300000]
        rates = np.linspace(0.05, 0.25, 100)
        
        def calculate_all_npvs():
            return [npf.npv(rate, cash_flows) for rate in rates]
        
        results = benchmark(calculate_all_npvs)
        
        assert len(results) == 100
        assert all(isinstance(r, (float, np.floating)) for r in results)


@smoke
@unit
class TestNPVSmoke:
    """Smoke tests for NPV analysis module."""
    
    def test_numpy_financial_import(self):
        """Test that numpy_financial can be imported."""
        import numpy_financial
        assert numpy_financial.__version__
    
    def test_basic_npv_function(self):
        """Test that basic NPV function works."""
        result = npf.npv(0.10, [-1000, 500, 500, 500])
        assert result is not None
        assert isinstance(result, (float, np.floating))
    
    def test_npv_module_imports(self):
        """Test that NPV analysis modules can be imported."""
        # Import from tests location where custom scripts were moved
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../modules/bsee/analysis/custom_scripts'))
        from Copilot import npv_analysis
        assert hasattr(npv_analysis, 'calculate_custom_npv_scenarios')
        assert hasattr(npv_analysis, 'load_actual_excel_data')
        assert hasattr(npv_analysis, 'save_results_to_file')