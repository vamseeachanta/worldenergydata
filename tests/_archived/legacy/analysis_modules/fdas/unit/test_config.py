"""
Unit tests for FDAS configuration management module.

Tests assumption loading, development system classification, and price deck
handling with comprehensive validation.

Author: WorldEnergyData Team
Date: 2025-10-03
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from src.worldenergydata.modules.fdas.core.config import (
    normalize_dev_system,
    classify_dev_system_by_depth,
    AssumptionsManager,
    PriceDeckManager,
    ConfigurationError,
    DEFAULT_ASSUMPTIONS,
)


class TestNormalizeDevSystem:
    """Test suite for development system name normalization"""

    def test_normalize_standard_names(self):
        """Test normalization of standard system names"""
        assert normalize_dev_system('dry') == 'dry'
        assert normalize_dev_system('subsea15') == 'subsea15'
        assert normalize_dev_system('subsea20') == 'subsea20'

    def test_normalize_case_variants(self):
        """Test case-insensitive normalization"""
        assert normalize_dev_system('DRY') == 'dry'
        assert normalize_dev_system('Subsea15') == 'subsea15'
        assert normalize_dev_system('SUBSEA20') == 'subsea20'

    def test_normalize_with_spaces(self):
        """Test normalization removes spaces"""
        assert normalize_dev_system('dry tree') == 'dry'
        assert normalize_dev_system('Subsea 15') == 'subsea15'
        assert normalize_dev_system('Subsea 20') == 'subsea20'

    def test_normalize_none_values(self):
        """Test normalization handles None and NaN"""
        assert normalize_dev_system(None) == 'unknown'
        assert normalize_dev_system(np.nan) == 'unknown'

    def test_normalize_common_variants(self):
        """Test recognition of common naming variants"""
        assert normalize_dev_system('DRY TREE') == 'dry'
        assert normalize_dev_system('dry-tree') == 'dry'
        assert normalize_dev_system('subsea_15') == 'subsea15'
        assert normalize_dev_system('ultra-deep') == 'subsea20'


class TestClassifyDevSystemByDepth:
    """Test suite for water depth-based classification"""

    def test_classify_shallow_water(self):
        """Test classification for shallow water (dry tree)"""
        assert classify_dev_system_by_depth(100) == 'dry'
        assert classify_dev_system_by_depth(499) == 'dry'

    def test_classify_mid_depth(self):
        """Test classification for mid-depth (subsea15)"""
        assert classify_dev_system_by_depth(500) == 'subsea15'
        assert classify_dev_system_by_depth(3000) == 'subsea15'
        assert classify_dev_system_by_depth(5999) == 'subsea15'

    def test_classify_ultra_deep(self):
        """Test classification for ultra-deep (subsea20)"""
        assert classify_dev_system_by_depth(6000) == 'subsea20'
        assert classify_dev_system_by_depth(7500) == 'subsea20'
        assert classify_dev_system_by_depth(10000) == 'subsea20'

    def test_classify_none_depth(self):
        """Test classification with None depth"""
        assert classify_dev_system_by_depth(None) == 'unknown'
        assert classify_dev_system_by_depth(np.nan) == 'unknown'


class TestAssumptionsManager:
    """Test suite for AssumptionsManager"""

    def test_default_initialization(self):
        """Test manager initializes with default assumptions"""
        mgr = AssumptionsManager()
        assert mgr.assumptions is not None
        assert 'DEV_SYSTEM' in mgr.assumptions.columns
        assert len(mgr.assumptions) >= 3

    def test_get_basic_lookup(self):
        """Test basic assumption lookup"""
        mgr = AssumptionsManager()

        # Test known values from defaults
        host_capex_subsea15 = mgr.get('subsea15', 'HOST_CAPEX_MM')
        assert host_capex_subsea15 == 300.0

        surf_subsea20 = mgr.get('subsea20', 'SURF_PER_WELL_MM')
        assert surf_subsea20 == 12.0

    def test_get_case_insensitive(self):
        """Test that parameter lookup is case-insensitive"""
        mgr = AssumptionsManager()

        value1 = mgr.get('subsea15', 'host_capex_mm')
        value2 = mgr.get('subsea15', 'HOST_CAPEX_MM')
        value3 = mgr.get('subsea15', 'Host_Capex_MM')

        assert value1 == value2 == value3

    def test_get_fallback_to_default(self):
        """Test fallback to default system"""
        mgr = AssumptionsManager()

        # Unknown system should fall back to default
        value = mgr.get('unknown_system', 'ROYALTY_RATE')
        assert value == 0.188  # default system value

    def test_get_missing_parameter(self):
        """Test behavior when parameter doesn't exist"""
        mgr = AssumptionsManager()

        value = mgr.get('subsea15', 'NONEXISTENT_PARAM', default=99.0)
        assert value == 99.0

    def test_get_all_for_system(self):
        """Test retrieving all parameters for a system"""
        mgr = AssumptionsManager()

        params = mgr.get_all_for_system('subsea15')

        assert isinstance(params, dict)
        assert 'HOST_CAPEX_MM' in params
        assert 'ROYALTY_RATE' in params
        assert params['HOST_CAPEX_MM'] == 300.0

    def test_from_dict_initialization(self):
        """Test creating manager from dictionary"""
        custom_assumptions = {
            'DEV_SYSTEM': ['custom_sys'],
            'HOST_CAPEX_MM': [500.0],
            'ROYALTY_RATE': [0.15],
        }

        mgr = AssumptionsManager.from_dict(custom_assumptions)
        assert mgr.get('custom_sys', 'HOST_CAPEX_MM') == 500.0
        assert mgr.get('custom_sys', 'ROYALTY_RATE') == 0.15

    def test_validate_default_assumptions(self):
        """Test validation of default assumptions"""
        mgr = AssumptionsManager()
        validation = mgr.validate()

        assert validation['valid'] is True
        assert len(validation['errors']) == 0
        assert 'subsea15' in validation['systems_found']

    def test_validate_missing_systems(self):
        """Test validation detects missing systems"""
        incomplete = {
            'DEV_SYSTEM': ['subsea15'],  # Missing dry and subsea20
            'HOST_CAPEX_MM': [300.0],
            'ROYALTY_RATE': [0.188],
            'VARIABLE_OPEX_$/BBL': [12.0],
            'DISCOUNT_RATE_ANNUAL': [0.10],
            'SURF_PER_WELL_MM': [8.0],
        }

        mgr = AssumptionsManager.from_dict(incomplete)
        validation = mgr.validate()

        assert len(validation['warnings']) > 0
        assert 'dry' in str(validation['warnings'])

    def test_validate_missing_parameters(self):
        """Test validation detects missing required parameters"""
        incomplete = {
            'DEV_SYSTEM': ['dry', 'subsea15', 'subsea20', 'default'],
            'HOST_CAPEX_MM': [0, 300, 450, 300],
            # Missing required parameters
        }

        mgr = AssumptionsManager.from_dict(incomplete)
        validation = mgr.validate()

        assert validation['valid'] is False
        assert len(validation['errors']) > 0


class TestPriceDeckManager:
    """Test suite for PriceDeckManager"""

    def test_default_initialization(self):
        """Test manager initializes without data"""
        mgr = PriceDeckManager()
        assert mgr.wti_df is None

    def test_get_price_no_data(self):
        """Test getting price when no data loaded"""
        mgr = PriceDeckManager()
        price = mgr.get_price('2024-01', default=80.0)
        assert price == 80.0

    def test_get_price_with_data(self):
        """Test price lookup with actual data"""
        wti_data = pd.DataFrame({
            'year_month': ['2024-01', '2024-02', '2024-03'],
            'wti_price': [75.0, 78.5, 82.0]
        })

        mgr = PriceDeckManager(wti_data)

        assert mgr.get_price('2024-01') == 75.0
        assert mgr.get_price('2024-02') == 78.5
        assert mgr.get_price('2024-03') == 82.0

    def test_get_price_missing_month(self):
        """Test price lookup for missing month"""
        wti_data = pd.DataFrame({
            'year_month': ['2024-01'],
            'wti_price': [75.0]
        })

        mgr = PriceDeckManager(wti_data)
        price = mgr.get_price('2024-12', default=80.0)
        assert price == 80.0


class TestIntegration:
    """Integration tests for configuration system"""

    def test_complete_workflow(self):
        """Test complete assumptions workflow"""
        # Create manager
        mgr = AssumptionsManager()

        # Classify a field by depth
        water_depth = 7500
        dev_system = classify_dev_system_by_depth(water_depth)
        assert dev_system == 'subsea20'

        # Get assumptions for that system
        host_capex = mgr.get(dev_system, 'HOST_CAPEX_MM')
        assert host_capex == 450.0

        surf_cost = mgr.get(dev_system, 'SURF_PER_WELL_MM')
        assert surf_cost == 12.0

        royalty = mgr.get(dev_system, 'ROYALTY_RATE')
        assert royalty == 0.188

    def test_assumptions_manager_aget_equivalence(self):
        """Test that manager.get() matches FDAS Aget() behavior"""
        mgr = AssumptionsManager()

        # These should match the FDAS Aget() function behavior
        test_cases = [
            ('subsea15', 'HOST_CAPEX_MM', 300.0),
            ('subsea20', 'SURF_PER_WELL_MM', 12.0),
            ('dry', 'HOST_CAPEX_MM', 0.0),
            ('unknown', 'ROYALTY_RATE', 0.188),  # Falls back to default
        ]

        for system, param, expected in test_cases:
            result = mgr.get(system, param)
            assert result == expected, f"Failed for {system}, {param}"


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_assumptions_dataframe(self):
        """Test behavior with empty DataFrame"""
        empty_df = pd.DataFrame()
        mgr = AssumptionsManager(empty_df)

        value = mgr.get('subsea15', 'HOST_CAPEX_MM', default=100.0)
        assert value == 100.0

    def test_normalization_with_special_characters(self):
        """Test normalization handles special characters"""
        assert normalize_dev_system('subsea-15') == 'subsea15'
        assert normalize_dev_system('subsea_15') == 'subsea15'
        assert normalize_dev_system('dry/tree') == 'dry'

    def test_depth_classification_boundary_values(self):
        """Test exact boundary values for depth classification"""
        assert classify_dev_system_by_depth(499.99) == 'dry'
        assert classify_dev_system_by_depth(500.0) == 'subsea15'
        assert classify_dev_system_by_depth(5999.99) == 'subsea15'
        assert classify_dev_system_by_depth(6000.0) == 'subsea20'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
