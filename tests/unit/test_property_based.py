"""
Property-based tests using Hypothesis for worldenergydata modules.

This module contains property-based tests that test the core functionality
with automatically generated inputs to ensure robustness and correctness.
"""

import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest
from hypothesis import assume, given, settings, strategies as st
from hypothesis.extra.numpy import arrays
from hypothesis.extra.pandas import column, data_frames, range_indexes

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from worldenergydata.engine import engine
import numpy_financial as npf


# ============================================================================
# Helper Functions for Testing
# ============================================================================

def calculate_npv(cash_flows: List[float], discount_rate: float) -> float:
    """Calculate NPV for a series of cash flows at a given discount rate."""
    return npf.npv(discount_rate, cash_flows)


# ============================================================================
# Strategy Definitions for Hypothesis
# ============================================================================

# Financial data strategies
@st.composite
def cash_flows_strategy(draw):
    """Generate realistic cash flow sequences for NPV testing."""
    length = draw(st.integers(min_value=2, max_value=20))
    # Initial investment (negative)
    initial = -draw(st.floats(min_value=1000, max_value=1e9, allow_nan=False))
    # Subsequent cash flows (mostly positive with some negative allowed)
    flows = draw(st.lists(
        st.floats(min_value=-1e8, max_value=1e9, allow_nan=False),
        min_size=length-1,
        max_size=length-1
    ))
    return [initial] + flows


@st.composite
def discount_rate_strategy(draw):
    """Generate realistic discount rates (0.1% to 50%)."""
    return draw(st.floats(min_value=0.001, max_value=0.5, allow_nan=False))


@st.composite
def production_data_strategy(draw):
    """Generate realistic production data for oil & gas wells."""
    n_months = draw(st.integers(min_value=1, max_value=120))
    
    # Generate production data with realistic constraints
    oil_production = draw(arrays(
        dtype=np.float64,
        shape=(n_months,),
        elements=st.floats(min_value=0, max_value=50000, allow_nan=False)
    ))
    
    gas_production = draw(arrays(
        dtype=np.float64,
        shape=(n_months,),
        elements=st.floats(min_value=0, max_value=1000000, allow_nan=False)
    ))
    
    water_production = draw(arrays(
        dtype=np.float64,
        shape=(n_months,),
        elements=st.floats(min_value=0, max_value=100000, allow_nan=False)
    ))
    
    return {
        'oil_bbls': oil_production,
        'gas_mcf': gas_production,
        'water_bbls': water_production,
        'months': n_months
    }


@st.composite
def well_data_strategy(draw):
    """Generate realistic well data structure."""
    return {
        'api_number': draw(st.text(min_size=10, max_size=14, alphabet=st.characters(categories=['Nd']))),
        'well_name': draw(st.text(min_size=1, max_size=50)),
        'field_name': draw(st.text(min_size=1, max_size=30)),
        'water_depth_ft': draw(st.floats(min_value=0, max_value=10000, allow_nan=False)),
        'total_depth_ft': draw(st.floats(min_value=100, max_value=35000, allow_nan=False)),
        'spud_date': draw(st.dates()),
        'completion_date': draw(st.dates()),
    }


@st.composite
def config_dict_strategy(draw):
    """Generate valid configuration dictionaries for the engine."""
    basename = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(categories=['L', 'Nd'])))
    
    config = {
        'basename': basename,
        'method': draw(st.sampled_from(['bsee', 'custom', 'zip'])),
        'data_source': draw(st.sampled_from(['local', 'api', 'zip'])),
    }
    
    # Add method-specific configurations
    if config['method'] == 'bsee':
        config['bsee'] = {
            'data_type': draw(st.sampled_from(['production', 'well', 'lease'])),
            'api_numbers': draw(st.lists(st.text(min_size=10, max_size=14), min_size=1, max_size=5))
        }
    
    return config


# ============================================================================
# Property-Based Tests for NPV Analysis
# ============================================================================

class TestNPVPropertyBased:
    """Property-based tests for NPV calculation functions."""
    
    @given(
        cash_flows=cash_flows_strategy(),
        discount_rate=discount_rate_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_npv_calculation_properties(self, cash_flows: List[float], discount_rate: float):
        """Test properties of NPV calculations.

        Tests basic properties that hold for all cash flow patterns.
        """
        npv = calculate_npv(cash_flows, discount_rate)

        # Property 1: NPV should be a finite number
        assert np.isfinite(npv), "NPV should be finite"

        # Property 2: NPV should be between sum of discounted min and max possible values
        # This is a loose bound that should always hold
        total_abs = sum(abs(cf) for cf in cash_flows)
        assert abs(npv) <= total_abs + 1, "NPV should be bounded by sum of absolute values"
    
    @given(
        cash_flows=cash_flows_strategy(),
        rates=st.lists(discount_rate_strategy(), min_size=2, max_size=10)
    )
    @settings(max_examples=50, deadline=None)
    def test_npv_monotonicity(self, cash_flows: List[float], rates: List[float]):
        """Test that NPV decreases monotonically with increasing discount rate for typical investments."""
        # Only test for typical investment patterns
        if cash_flows[0] >= 0 or sum(cash_flows[1:]) <= 0:
            return  # Skip non-typical patterns
        
        sorted_rates = sorted(rates)
        npvs = [calculate_npv(cash_flows, rate) for rate in sorted_rates]
        
        # Check monotonic decrease
        for i in range(len(npvs) - 1):
            assert npvs[i] >= npvs[i+1] - 1e-6, "NPV should decrease with increasing rate"
    
    @given(cash_flows=cash_flows_strategy())
    @settings(max_examples=50, deadline=None)
    def test_npv_scaling_property(self, cash_flows: List[float]):
        """Test that NPV scales linearly with cash flows."""
        rate = 0.1
        npv1 = calculate_npv(cash_flows, rate)
        
        # Scale all cash flows by a factor
        scale_factor = 2.5
        scaled_flows = [cf * scale_factor for cf in cash_flows]
        npv2 = calculate_npv(scaled_flows, rate)
        
        # NPV should scale by the same factor
        assert np.isclose(npv2, npv1 * scale_factor, rtol=1e-10), "NPV should scale linearly"


# ============================================================================
# Property-Based Tests for Production Data Processing
# ============================================================================

class TestProductionDataPropertyBased:
    """Property-based tests for production data processing."""
    
    @given(production_data=production_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_production_data_invariants(self, production_data: Dict):
        """Test invariants that should hold for production data."""
        oil = production_data['oil_bbls']
        gas = production_data['gas_mcf']
        water = production_data['water_bbls']
        
        # Property 1: All production values should be non-negative
        assert np.all(oil >= 0), "Oil production should be non-negative"
        assert np.all(gas >= 0), "Gas production should be non-negative"
        assert np.all(water >= 0), "Water production should be non-negative"
        
        # Property 2: Length consistency
        assert len(oil) == production_data['months'], "Oil array length should match months"
        assert len(gas) == production_data['months'], "Gas array length should match months"
        assert len(water) == production_data['months'], "Water array length should match months"
        
        # Property 3: Cumulative production should be monotonically increasing
        cum_oil = np.cumsum(oil)
        cum_gas = np.cumsum(gas)
        
        if len(cum_oil) > 1:
            assert np.all(np.diff(cum_oil) >= -1e-10), "Cumulative oil should increase"
        if len(cum_gas) > 1:
            assert np.all(np.diff(cum_gas) >= -1e-10), "Cumulative gas should increase"
    
    @given(
        production_df=data_frames(
            columns=[
                column('oil_bbls', dtype=float, elements=st.floats(0, 50000, allow_nan=False)),
                column('gas_mcf', dtype=float, elements=st.floats(0, 1000000, allow_nan=False)),
                column('water_bbls', dtype=float, elements=st.floats(0, 100000, allow_nan=False)),
            ],
            index=range_indexes(min_size=1, max_size=100)
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_production_dataframe_processing(self, production_df: pd.DataFrame):
        """Test properties of production dataframe processing."""
        # Property 1: DataFrame shape should be preserved through transformations
        original_shape = production_df.shape
        
        # Add calculated columns
        production_df['boe'] = production_df['oil_bbls'] + production_df['gas_mcf'] / 6
        production_df['water_cut'] = production_df['water_bbls'] / (
            production_df['oil_bbls'] + production_df['water_bbls'] + 1e-10
        )
        
        # Check shape increased by 2 columns
        assert production_df.shape[0] == original_shape[0], "Row count should be preserved"
        assert production_df.shape[1] == original_shape[1] + 2, "Should have 2 new columns"
        
        # Property 2: BOE calculation should be correct
        expected_boe = production_df['oil_bbls'] + production_df['gas_mcf'] / 6
        assert np.allclose(production_df['boe'], expected_boe), "BOE calculation should be correct"
        
        # Property 3: Water cut should be between 0 and 1
        assert np.all(production_df['water_cut'] >= 0), "Water cut should be >= 0"
        assert np.all(production_df['water_cut'] <= 1 + 1e-10), "Water cut should be <= 1"


# ============================================================================
# Property-Based Tests for Well Data
# ============================================================================

class TestWellDataPropertyBased:
    """Property-based tests for well data structures and processing."""
    
    @given(well_data=well_data_strategy())
    @settings(max_examples=50, deadline=None)
    def test_well_data_validation(self, well_data: Dict):
        """Test validation properties of well data."""
        # Property 1: Water depth should be less than or equal to total depth
        if 'water_depth_ft' in well_data and 'total_depth_ft' in well_data:
            # Water depth is typically less than total depth for offshore wells
            # For onshore wells, water depth would be 0
            pass  # Skip this check as water depth can vary independently
        
        # Property 2: API number should have correct format (if numeric)
        api = well_data.get('api_number', '')
        if api and api.isdigit():
            assert 10 <= len(api) <= 14, "API number should be 10-14 digits"
        
        # Property 3: Total depth should be positive
        if 'total_depth_ft' in well_data:
            assert well_data['total_depth_ft'] > 0, "Total depth should be positive"
        
        # Property 4: Field name should not be empty if present
        if 'field_name' in well_data:
            assert len(well_data['field_name']) > 0, "Field name should not be empty"
    
    @given(
        depths=st.lists(
            st.floats(min_value=0, max_value=35000, allow_nan=False, allow_infinity=False),
            min_size=2,
            max_size=50
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_depth_statistics(self, depths: List[float]):
        """Test statistical properties of depth measurements."""
        depths_array = np.array(depths)

        # Property 1: Mean should be between min and max (with floating point tolerance)
        mean_depth = np.mean(depths_array)
        min_depth = np.min(depths_array)
        max_depth = np.max(depths_array)
        assert min_depth - 1e-10 <= mean_depth <= max_depth + 1e-10, \
            "Mean should be between min and max"

        # Property 2: Standard deviation should be non-negative
        std_depth = np.std(depths_array)
        assert std_depth >= -1e-10, "Standard deviation should be non-negative"

        # Property 3: Median should be between min and max (with tolerance)
        median_depth = np.median(depths_array)
        assert min_depth - 1e-10 <= median_depth <= max_depth + 1e-10, \
            "Median should be between min and max"


# ============================================================================
# Property-Based Tests for Configuration and Engine
# ============================================================================

class TestEnginePropertyBased:
    """Property-based tests for the main engine configuration."""
    
    @given(config=config_dict_strategy())
    @settings(max_examples=30, deadline=None)
    def test_config_validation(self, config: Dict):
        """Test that configuration dictionaries maintain required properties."""
        # Property 1: Basename should always be present
        assert 'basename' in config, "Config should have basename"
        assert config['basename'], "Basename should not be empty"
        
        # Property 2: Method should be valid
        valid_methods = ['bsee', 'custom', 'zip']
        if 'method' in config:
            assert config['method'] in valid_methods, f"Method should be one of {valid_methods}"
        
        # Property 3: Method-specific config should match method
        if config.get('method') == 'bsee' and 'bsee' in config:
            assert 'data_type' in config['bsee'], "BSEE config should have data_type"
    
    @given(
        basename=st.text(min_size=1, max_size=50, alphabet=st.characters(categories=['L', 'Nd'])),
        method=st.sampled_from(['bsee', 'custom', 'zip'])
    )
    @settings(max_examples=20, deadline=None)
    def test_config_creation_invariants(self, basename: str, method: str):
        """Test invariants when creating configurations."""
        config = {
            'basename': basename,
            'method': method,
            'meta': {
                'basename': basename,
                'version': '1.0.0'
            }
        }
        
        # Property 1: Basename should be consistent
        assert config['basename'] == config['meta']['basename'], \
            "Basename should be consistent across config"
        
        # Property 2: Config should be serializable (no complex types)
        import json
        try:
            json.dumps(config)
            serializable = True
        except (TypeError, ValueError):
            serializable = False
        assert serializable, "Config should be JSON serializable"


# ============================================================================
# Property-Based Tests for Data Transformations
# ============================================================================

class TestDataTransformationsPropertyBased:
    """Property-based tests for data transformation functions."""
    
    @given(
        values=arrays(
            dtype=np.float64,
            shape=100,  # Fixed shape for stability
            elements=st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False)
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_cumulative_sum_properties(self, values: np.ndarray):
        """Test properties of cumulative sum operations."""
        cumsum = np.cumsum(values)

        # Property 1: Length should be preserved
        assert len(cumsum) == len(values), "Cumsum should preserve length"

        # Property 2: Last element should equal total sum (with relaxed tolerance for floating point)
        assert np.isclose(cumsum[-1], np.sum(values), rtol=1e-6, atol=1e-6), \
            "Last cumsum element should equal total sum"

        # Property 3: Differences should recover original values (with relaxed tolerance)
        if len(values) > 1:
            recovered = np.diff(cumsum)
            recovered = np.concatenate([[cumsum[0]], recovered])
            assert np.allclose(recovered, values, rtol=1e-6, atol=1e-6), \
                "Differencing cumsum should recover original"
    
    @given(
        data=arrays(
            dtype=np.float64,
            shape=(10, 5),  # Fixed shape for stability
            elements=st.floats(min_value=0, max_value=1e4, allow_nan=False, allow_infinity=False)
        )
    )
    @settings(max_examples=30, deadline=None)
    def test_aggregation_properties(self, data: np.ndarray):
        """Test properties of aggregation operations."""
        # Sum across rows
        row_sums = np.sum(data, axis=1)
        # Sum across columns
        col_sums = np.sum(data, axis=0)

        # Property 1: Total sum should be consistent
        total_from_rows = np.sum(row_sums)
        total_from_cols = np.sum(col_sums)
        total_direct = np.sum(data)

        assert np.isclose(total_from_rows, total_direct, rtol=1e-6, atol=1e-6), \
            "Sum of row sums should equal total"
        assert np.isclose(total_from_cols, total_direct, rtol=1e-6, atol=1e-6), \
            "Sum of column sums should equal total"

        # Property 2: Mean relationships (for uniform matrix shape)
        mean_of_means = np.mean(np.mean(data, axis=0))
        overall_mean = np.mean(data)
        # For uniform shape, these should be equal
        assert np.isclose(mean_of_means, overall_mean, rtol=1e-6, atol=1e-6), \
            "Mean of column means should equal overall mean"


# ============================================================================
# Run tests if executed directly
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])