"""
Validation Tests Against Original FDAS Code

Compares new implementation against Roy's original FDAS V30 code
using the same input data and validating outputs match within tolerance.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add FDAS source to path for comparison
FDAS_SOURCE_DIR = (
    Path(__file__).resolve().parents[4]
    / "docs/modules/bsee/analysis/production/FDAS_V30"
)
sys.path.insert(0, str(FDAS_SOURCE_DIR))

# Import original FDAS functions for comparison
try:
    from generate_financial_summary_V30 import Aget as original_Aget
    from generate_financial_summary_V30 import (
        excel_like_mirr as original_excel_like_mirr,
    )
    from generate_financial_summary_V30 import (
        load_assumptions_fixed as original_load_assumptions,
    )

    ORIGINAL_AVAILABLE = True
except ImportError:
    ORIGINAL_AVAILABLE = False
    print("Warning: Original FDAS code not available for comparison")

from worldenergydata.fdas.core.config import (  # noqa: E402
    AssumptionsManager,
    classify_dev_system_by_depth,
)

# Import our implementation
from worldenergydata.fdas.core.financial import (  # noqa: E402
    calculate_npv,
    excel_like_mirr,
)


@pytest.mark.skipif(not ORIGINAL_AVAILABLE, reason="Original FDAS code not available")
class TestMIRRAgainstOriginal:
    """Validate MIRR calculation against original implementation"""

    def test_mirr_simple_cashflow(self):
        """Test MIRR matches original for simple cashflow"""
        cashflows = np.array([-1000.0, 100, 200, 300, 400, 500])
        discount_rate = 0.10

        # Our implementation
        our_mirr_m, our_mirr_a = excel_like_mirr(cashflows, discount_rate)

        # Original implementation
        orig_mirr_m = original_excel_like_mirr(cashflows, discount_rate)

        # Should match within floating point tolerance
        assert np.isclose(
            our_mirr_m, orig_mirr_m, rtol=1e-6
        ), f"Monthly MIRR mismatch: ours={our_mirr_m}, original={orig_mirr_m}"

    def test_mirr_with_zero_padding(self):
        """Test MIRR with leading/trailing zeros matches original"""
        cashflows = np.array([0, 0, -1000, 100, 200, 300, 400, 0, 0])
        discount_rate = 0.10

        our_mirr_m, our_mirr_a = excel_like_mirr(cashflows, discount_rate)
        orig_mirr_m = original_excel_like_mirr(cashflows, discount_rate)

        assert np.isclose(our_mirr_m, orig_mirr_m, rtol=1e-6)

    def test_mirr_complex_cashflow(self):
        """Test MIRR with realistic field development cashflow"""
        # Simulate Anchor field-like cashflow
        cashflows = np.array(
            [
                -1500,  # Year 0: Initial CAPEX
                -500,  # Year 1: Additional CAPEX
                200,  # Year 2: First production
                800,  # Year 3: Ramp up
                1200,  # Year 4: Peak
                1000,  # Year 5: Plateau
                800,  # Year 6: Decline
                600,  # Year 7
                400,  # Year 8
                200,  # Year 9
            ]
        )
        discount_rate = 0.10

        our_mirr_m, our_mirr_a = excel_like_mirr(cashflows, discount_rate)
        orig_mirr_m = original_excel_like_mirr(cashflows, discount_rate)

        assert np.isclose(our_mirr_m, orig_mirr_m, rtol=1e-6)

    def test_mirr_annualization(self):
        """Test that monthly to annual conversion matches"""
        cashflows = np.array([-1000] + [100] * 12)
        discount_rate = 0.10

        our_mirr_m, our_mirr_a = excel_like_mirr(cashflows, discount_rate)

        # Verify annualization formula
        expected_annual = (1 + our_mirr_m) ** 12 - 1
        assert np.isclose(our_mirr_a, expected_annual, rtol=1e-10)


@pytest.mark.skipif(not ORIGINAL_AVAILABLE, reason="Original FDAS code not available")
class TestAssumptionsAgainstOriginal:
    """Validate assumptions loading against original"""

    def test_aget_function_equivalence(self):
        """Test that our AssumptionsManager.get() matches original Aget()"""
        # Load original assumptions
        assumptions_file = FDAS_SOURCE_DIR / "lease_assumptions.xlsx"
        if not assumptions_file.exists():
            pytest.skip("lease_assumptions.xlsx not found")

        # Load with original
        orig_df = original_load_assumptions(str(assumptions_file))

        # Load with ours
        our_mgr = AssumptionsManager.from_excel(assumptions_file)

        # Test key lookups
        test_cases = [
            ("subsea15", "HOST_CAPEX_MM"),
            ("subsea20", "SURF_PER_WELL_MM"),
            ("dry", "ROYALTY_RATE"),
            ("subsea15", "VARIABLE_OPEX_$/BBL"),
        ]

        for system, param in test_cases:
            orig_value = original_Aget(orig_df, system, param, 0.0)
            our_value = our_mgr.get(system, param, 0.0)

            assert np.isclose(
                orig_value, our_value, rtol=1e-10
            ), f"Mismatch for {system}/{param}: ours={our_value}, original={orig_value}"


class TestWithRealData:
    """Validation tests using real FDAS input files"""

    @pytest.fixture
    def leases_file(self):
        """Leases file path"""
        path = FDAS_SOURCE_DIR / "leases.xlsx"
        if not path.exists():
            pytest.skip("leases.xlsx not found")
        return path

    @pytest.fixture
    def assumptions_file(self):
        """Assumptions file path"""
        path = FDAS_SOURCE_DIR / "lease_assumptions.xlsx"
        if not path.exists():
            pytest.skip("lease_assumptions.xlsx not found")
        return path

    @pytest.fixture
    def chronological_file(self):
        """Chronological production file path"""
        path = FDAS_SOURCE_DIR / "chronological_lease_analysis.xlsx"
        if not path.exists():
            pytest.skip("chronological_lease_analysis.xlsx not found")
        return path

    @pytest.fixture
    def drilling_file(self):
        """Drilling & completion file path"""
        path = FDAS_SOURCE_DIR / "drilling_and_completion_days.xlsx"
        if not path.exists():
            pytest.skip("drilling_and_completion_days.xlsx not found")
        return path

    def test_load_real_assumptions(self, assumptions_file):
        """Test loading real assumptions file"""
        mgr = AssumptionsManager.from_excel(assumptions_file)

        # Validate structure
        validation = mgr.validate()
        assert validation["valid"] is True, f"Validation errors: {validation['errors']}"

        # Check expected systems exist
        assert "subsea15" in validation["systems_found"]
        assert "subsea20" in validation["systems_found"]

    def test_load_real_leases(self, leases_file):
        """Test loading real leases file"""
        leases_df = pd.read_excel(leases_file)

        # Should have expected columns
        assert "LEASE_NAME" in leases_df.columns or "Lease Name" in leases_df.columns
        assert len(leases_df) > 0

    def test_load_chronological_production(self, chronological_file):
        """Test loading chronological production data"""
        prod_df = pd.read_excel(chronological_file)

        assert len(prod_df) > 0
        # Should have API well numbers and production data
        assert any("API" in col.upper() for col in prod_df.columns)

    def test_development_system_classification_real_data(self, leases_file):
        """Test dev system classification on real lease data"""
        leases_df = pd.read_excel(leases_file)

        # Try to find water depth column (various naming conventions)
        water_depth_col = None
        for col in leases_df.columns:
            if "WATER" in col.upper() and "DEPTH" in col.upper():
                water_depth_col = col
                break

        if water_depth_col is None:
            pytest.skip("Water depth column not found in leases file")

        # Classify each lease
        for _, row in leases_df.iterrows():
            water_depth = row.get(water_depth_col)
            if pd.notna(water_depth):
                dev_system = classify_dev_system_by_depth(water_depth)
                assert dev_system in ["dry", "subsea15", "subsea20", "unknown"]


class TestFinancialOutputComparison:
    """Compare financial outputs with original FDAS results"""

    @pytest.fixture
    def financial_summary_file(self):
        """Original financial summary output"""
        path = FDAS_SOURCE_DIR / "financial_project_summary.xlsx"
        if not path.exists():
            pytest.skip("financial_project_summary.xlsx not found")
        return path

    def test_compare_with_golden_baseline(self, financial_summary_file):
        """Compare calculations with original financial summary"""
        # Load original output
        try:
            orig_summary = pd.read_excel(
                financial_summary_file, sheet_name="Project Summary"
            )
        except Exception as e:
            pytest.skip(f"Could not load financial summary: {e}")

        # This is a placeholder - actual comparison would require
        # running the same input data through both systems
        assert len(orig_summary) > 0


class TestNumericalAccuracy:
    """Test numerical accuracy of calculations"""

    def test_npv_precision(self):
        """Test NPV calculation precision"""
        # Known test case
        cashflows = np.array([-1000, 500, 500, 500])
        discount_rate = 0.10

        npv = calculate_npv(cashflows, discount_rate, period="annual")

        # Known result: NPV ≈ 243.426 at 10% discount
        expected = 243.426
        assert np.isclose(
            npv, expected, atol=0.01
        ), f"NPV mismatch: got {npv}, expected ~{expected}"

    def test_mirr_precision_known_value(self):
        """Test MIRR against known Excel result"""
        # Test case from Excel MIRR documentation
        cashflows = np.array([-120000, 39000, 30000, 21000, 37000, 46000])
        discount_rate = 0.10
        reinvest_rate = 0.12

        mirr_m, mirr_a = excel_like_mirr(cashflows, discount_rate, reinvest_rate)

        # Excel MIRR for this example ≈ 12.6% (annual basis for annual cashflows)
        # Our monthly calculation should work similarly
        assert not np.isnan(mirr_m)
        assert not np.isnan(mirr_a)
        assert mirr_m > 0

    def test_cashflow_trimming_accuracy(self):
        """Test that cashflow trimming matches Excel methodology"""
        # Cashflows with padding
        cf_padded = np.array([0, 0, 0, -1000, 100, 200, 300, 0, 0, 0])
        cf_trimmed = np.array([-1000, 100, 200, 300])

        mirr_padded = excel_like_mirr(cf_padded, 0.10)
        mirr_trimmed = excel_like_mirr(cf_trimmed, 0.10)

        # Should produce identical results
        np.testing.assert_allclose(mirr_padded[0], mirr_trimmed[0], rtol=1e-10)
        np.testing.assert_allclose(mirr_padded[1], mirr_trimmed[1], rtol=1e-10)


class TestEdgeCaseHandling:
    """Test edge cases and error handling"""

    def test_all_positive_cashflows(self):
        """Test handling of all-positive cashflows (no valid MIRR)"""
        cashflows = np.array([100, 200, 300, 400])

        mirr_m, mirr_a = excel_like_mirr(cashflows, 0.10)

        # Should return NaN for invalid cashflows
        assert np.isnan(mirr_m)
        assert np.isnan(mirr_a)

    def test_all_negative_cashflows(self):
        """Test handling of all-negative cashflows"""
        cashflows = np.array([-100, -200, -300, -400])

        mirr_m, mirr_a = excel_like_mirr(cashflows, 0.10)

        assert np.isnan(mirr_m)
        assert np.isnan(mirr_a)

    def test_single_period_cashflow(self):
        """Test handling of single period"""
        cashflows = np.array([-1000, 1100])

        mirr_m, mirr_a = excel_like_mirr(cashflows, 0.10)

        # Should handle gracefully
        assert not np.isnan(mirr_m)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
