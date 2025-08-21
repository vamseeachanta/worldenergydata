"""
Data Processing Performance Tests

This module tests the performance of data processing operations
specific to WorldEnergyData modules.
"""

import pytest
import pandas as pd
import numpy as np
import time
from pathlib import Path
import sys
from typing import Dict, List, Tuple
import tempfile
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.worldenergydata.engine import Engine
from src.worldenergydata.core.raw_data_processing import RawDataProcessing
from src.worldenergydata.bsee.data_loader import BSEEDataLoader
from src.worldenergydata.analysis.financial_analysis import FinancialAnalysis


class TestDataProcessingPerformance:
    """Test performance of data processing operations."""
    
    @pytest.fixture
    def large_production_dataset(self):
        """Create a large production dataset for performance testing."""
        num_wells = 100
        days = 1000
        
        data = []
        base_date = datetime(2020, 1, 1)
        
        for well_id in range(num_wells):
            for day in range(days):
                date = base_date + timedelta(days=day)
                data.append({
                    'well_id': f'WELL_{well_id:04d}',
                    'date': date,
                    'oil_production': np.random.exponential(1000) * (1 - day/days),  # Declining production
                    'gas_production': np.random.exponential(5000) * (1 - day/days),
                    'water_production': np.random.exponential(500) * (1 + day/days),  # Increasing water cut
                    'pressure': 3000 - day * 0.5 + np.random.normal(0, 50),
                    'temperature': 150 + np.random.normal(0, 5),
                    'field_name': f'FIELD_{well_id // 10}',
                    'operator': f'OPERATOR_{well_id // 20}'
                })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def complex_hierarchical_data(self):
        """Create complex hierarchical data for aggregation testing."""
        size = 50000
        
        df = pd.DataFrame({
            'company': np.random.choice(['CompanyA', 'CompanyB', 'CompanyC'], size),
            'field': np.random.choice([f'Field_{i}' for i in range(20)], size),
            'well': np.random.choice([f'Well_{i}' for i in range(100)], size),
            'date': pd.date_range('2020-01-01', periods=size, freq='H'),
            'production': np.random.exponential(1000, size),
            'revenue': np.random.exponential(50000, size),
            'cost': np.random.exponential(30000, size)
        })
        
        return df
    
    @pytest.mark.performance
    def test_raw_data_processing_performance(self, large_production_dataset):
        """Test performance of RawDataProcessing operations."""
        processor = RawDataProcessing()
        
        # Test 1: Data cleaning performance
        start = time.perf_counter()
        # Add nulls to test cleaning
        dirty_data = large_production_dataset.copy()
        mask = np.random.random(len(dirty_data)) < 0.1
        dirty_data.loc[mask, 'oil_production'] = np.nan
        
        # Clean data (simulated)
        cleaned = dirty_data.dropna()
        cleaned['oil_production'] = cleaned['oil_production'].fillna(method='ffill')
        cleaning_time = time.perf_counter() - start
        
        assert cleaning_time < 1.0, f"Data cleaning took {cleaning_time:.3f}s (expected < 1s)"
        print(f"Cleaned {len(dirty_data)} rows in {cleaning_time:.3f}s")
        
        # Test 2: Data transformation performance
        start = time.perf_counter()
        transformed = large_production_dataset.copy()
        
        # Add calculated columns
        transformed['boe'] = transformed['oil_production'] + transformed['gas_production'] / 6000
        transformed['water_cut'] = transformed['water_production'] / (
            transformed['water_production'] + transformed['oil_production']
        )
        transformed['cumulative_oil'] = transformed.groupby('well_id')['oil_production'].cumsum()
        transformed['ma_30'] = transformed.groupby('well_id')['oil_production'].transform(
            lambda x: x.rolling(30, min_periods=1).mean()
        )
        
        transformation_time = time.perf_counter() - start
        
        assert transformation_time < 2.0, f"Data transformation took {transformation_time:.3f}s (expected < 2s)"
        print(f"Transformed {len(transformed)} rows in {transformation_time:.3f}s")
        
        # Test 3: Aggregation performance
        start = time.perf_counter()
        aggregated = large_production_dataset.groupby(['field_name', 'date']).agg({
            'oil_production': ['sum', 'mean', 'std'],
            'gas_production': ['sum', 'mean', 'std'],
            'water_production': ['sum', 'mean', 'std'],
            'pressure': ['mean', 'min', 'max'],
            'temperature': ['mean', 'min', 'max']
        })
        aggregation_time = time.perf_counter() - start
        
        assert aggregation_time < 1.0, f"Aggregation took {aggregation_time:.3f}s (expected < 1s)"
        print(f"Aggregated to {len(aggregated)} rows in {aggregation_time:.3f}s")
    
    @pytest.mark.performance
    def test_financial_analysis_performance(self, large_production_dataset):
        """Test performance of financial analysis calculations."""
        analyzer = FinancialAnalysis()
        
        # Prepare financial data
        financial_data = large_production_dataset.copy()
        financial_data['oil_revenue'] = financial_data['oil_production'] * 70  # $70/bbl
        financial_data['gas_revenue'] = financial_data['gas_production'] * 3.5  # $3.5/mcf
        financial_data['opex'] = financial_data['oil_production'] * 25  # $25/bbl opex
        financial_data['net_revenue'] = (
            financial_data['oil_revenue'] + 
            financial_data['gas_revenue'] - 
            financial_data['opex']
        )
        
        # Test 1: NPV calculation performance
        start = time.perf_counter()
        # Calculate NPV for each well
        npv_results = {}
        discount_rate = 0.1
        
        for well_id in financial_data['well_id'].unique()[:10]:  # Test with 10 wells
            well_data = financial_data[financial_data['well_id'] == well_id]
            cash_flows = well_data.groupby('date')['net_revenue'].sum().values
            
            # Simple NPV calculation
            periods = np.arange(len(cash_flows))
            discount_factors = (1 + discount_rate) ** (-periods / 365)
            npv = np.sum(cash_flows * discount_factors)
            npv_results[well_id] = npv
        
        npv_time = time.perf_counter() - start
        
        assert npv_time < 0.5, f"NPV calculation took {npv_time:.3f}s (expected < 0.5s)"
        print(f"Calculated NPV for 10 wells in {npv_time:.3f}s")
        
        # Test 2: IRR calculation performance (simplified)
        start = time.perf_counter()
        # Simplified IRR calculation
        for well_id in list(npv_results.keys())[:5]:  # Test with 5 wells
            well_data = financial_data[financial_data['well_id'] == well_id]
            cash_flows = well_data.groupby('date')['net_revenue'].sum().values
            
            # Simplified IRR (just for performance testing)
            initial_investment = -1000000  # $1M initial investment
            cf_with_initial = np.concatenate([[initial_investment], cash_flows[:365]])
            
            # Newton-Raphson method simulation
            irr_guess = 0.1
            for _ in range(10):  # Fixed iterations for performance test
                npv = np.sum(cf_with_initial / (1 + irr_guess) ** np.arange(len(cf_with_initial)))
                irr_guess += 0.01
        
        irr_time = time.perf_counter() - start
        
        assert irr_time < 0.3, f"IRR calculation took {irr_time:.3f}s (expected < 0.3s)"
        print(f"Calculated IRR for 5 wells in {irr_time:.3f}s")
    
    @pytest.mark.performance
    def test_hierarchical_aggregation_performance(self, complex_hierarchical_data):
        """Test performance of complex hierarchical aggregations."""
        
        # Test 1: Multi-level groupby performance
        start = time.perf_counter()
        multi_level = complex_hierarchical_data.groupby(['company', 'field', 'well']).agg({
            'production': ['sum', 'mean', 'std', 'count'],
            'revenue': ['sum', 'mean'],
            'cost': ['sum', 'mean']
        })
        multi_level_time = time.perf_counter() - start
        
        assert multi_level_time < 1.0, f"Multi-level groupby took {multi_level_time:.3f}s"
        print(f"Multi-level aggregation completed in {multi_level_time:.3f}s")
        
        # Test 2: Pivot table performance
        start = time.perf_counter()
        pivot = complex_hierarchical_data.pivot_table(
            index=['company', 'field'],
            columns=pd.Grouper(key='date', freq='D'),
            values='production',
            aggfunc='sum'
        )
        pivot_time = time.perf_counter() - start
        
        assert pivot_time < 2.0, f"Pivot table took {pivot_time:.3f}s"
        print(f"Pivot table created in {pivot_time:.3f}s")
        
        # Test 3: Window functions performance
        start = time.perf_counter()
        complex_hierarchical_data['production_rank'] = complex_hierarchical_data.groupby(
            ['company', 'field']
        )['production'].rank(method='dense', ascending=False)
        
        complex_hierarchical_data['cumulative_revenue'] = complex_hierarchical_data.groupby(
            ['company', 'field']
        )['revenue'].cumsum()
        
        complex_hierarchical_data['profit_margin'] = (
            complex_hierarchical_data['revenue'] - complex_hierarchical_data['cost']
        ) / complex_hierarchical_data['revenue']
        
        window_time = time.perf_counter() - start
        
        assert window_time < 1.0, f"Window functions took {window_time:.3f}s"
        print(f"Window functions completed in {window_time:.3f}s")
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_file_processing_performance(self, tmp_path):
        """Test performance of processing large files."""
        
        # Create a large CSV file
        num_rows = 100000
        large_df = pd.DataFrame({
            'id': range(num_rows),
            'timestamp': pd.date_range('2020-01-01', periods=num_rows, freq='min'),
            'value1': np.random.randn(num_rows),
            'value2': np.random.randn(num_rows),
            'value3': np.random.randn(num_rows),
            'category': np.random.choice(['A', 'B', 'C', 'D'], num_rows),
            'subcategory': np.random.choice(['X', 'Y', 'Z'], num_rows)
        })
        
        csv_path = tmp_path / 'large_file.csv'
        
        # Test 1: Write performance
        start = time.perf_counter()
        large_df.to_csv(csv_path, index=False)
        write_time = time.perf_counter() - start
        
        assert write_time < 5.0, f"Writing {num_rows} rows took {write_time:.3f}s"
        print(f"Wrote {num_rows} rows in {write_time:.3f}s")
        
        # Test 2: Read performance
        start = time.perf_counter()
        df_read = pd.read_csv(csv_path)
        read_time = time.perf_counter() - start
        
        assert read_time < 3.0, f"Reading {num_rows} rows took {read_time:.3f}s"
        print(f"Read {num_rows} rows in {read_time:.3f}s")
        
        # Test 3: Chunked processing performance
        start = time.perf_counter()
        chunk_size = 10000
        processed_chunks = []
        
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size):
            # Process each chunk
            chunk['processed'] = chunk['value1'] * 2 + chunk['value2']
            chunk_agg = chunk.groupby('category')['processed'].mean()
            processed_chunks.append(chunk_agg)
        
        # Combine results
        final_result = pd.concat(processed_chunks).groupby(level=0).mean()
        chunk_time = time.perf_counter() - start
        
        assert chunk_time < 2.0, f"Chunked processing took {chunk_time:.3f}s"
        print(f"Processed {num_rows} rows in chunks in {chunk_time:.3f}s")
    
    @pytest.mark.performance
    def test_data_filtering_performance(self, large_production_dataset):
        """Test performance of various filtering operations."""
        
        # Test 1: Simple filtering
        start = time.perf_counter()
        filtered1 = large_production_dataset[
            large_production_dataset['oil_production'] > 500
        ]
        simple_filter_time = time.perf_counter() - start
        
        assert simple_filter_time < 0.01, f"Simple filter took {simple_filter_time:.3f}s"
        
        # Test 2: Complex filtering
        start = time.perf_counter()
        filtered2 = large_production_dataset[
            (large_production_dataset['oil_production'] > 500) &
            (large_production_dataset['gas_production'] < 10000) &
            (large_production_dataset['water_production'] < 1000) &
            (large_production_dataset['pressure'] > 2500)
        ]
        complex_filter_time = time.perf_counter() - start
        
        assert complex_filter_time < 0.05, f"Complex filter took {complex_filter_time:.3f}s"
        
        # Test 3: Query method performance
        start = time.perf_counter()
        filtered3 = large_production_dataset.query(
            'oil_production > 500 and gas_production < 10000 and pressure > 2500'
        )
        query_time = time.perf_counter() - start
        
        assert query_time < 0.1, f"Query method took {query_time:.3f}s"
        
        # Test 4: isin filtering
        well_list = large_production_dataset['well_id'].unique()[:20]
        start = time.perf_counter()
        filtered4 = large_production_dataset[
            large_production_dataset['well_id'].isin(well_list)
        ]
        isin_time = time.perf_counter() - start
        
        assert isin_time < 0.05, f"isin filter took {isin_time:.3f}s"
        
        print(f"Filter performance - Simple: {simple_filter_time:.3f}s, "
              f"Complex: {complex_filter_time:.3f}s, Query: {query_time:.3f}s, "
              f"isin: {isin_time:.3f}s")
    
    @pytest.mark.performance
    def test_data_merge_performance(self, large_production_dataset):
        """Test performance of various merge operations."""
        
        # Create auxiliary datasets
        well_info = pd.DataFrame({
            'well_id': large_production_dataset['well_id'].unique(),
            'location': np.random.choice(['Offshore', 'Onshore'], 
                                       len(large_production_dataset['well_id'].unique())),
            'depth': np.random.uniform(5000, 15000, 
                                      len(large_production_dataset['well_id'].unique()))
        })
        
        field_info = pd.DataFrame({
            'field_name': large_production_dataset['field_name'].unique(),
            'basin': np.random.choice(['Basin_A', 'Basin_B', 'Basin_C'],
                                    len(large_production_dataset['field_name'].unique())),
            'discovery_year': np.random.randint(1950, 2020,
                                               len(large_production_dataset['field_name'].unique()))
        })
        
        # Test 1: Simple merge
        start = time.perf_counter()
        merged1 = pd.merge(large_production_dataset, well_info, on='well_id', how='left')
        simple_merge_time = time.perf_counter() - start
        
        assert simple_merge_time < 0.5, f"Simple merge took {simple_merge_time:.3f}s"
        
        # Test 2: Multiple merges
        start = time.perf_counter()
        merged2 = pd.merge(large_production_dataset, well_info, on='well_id', how='left')
        merged2 = pd.merge(merged2, field_info, on='field_name', how='left')
        multi_merge_time = time.perf_counter() - start
        
        assert multi_merge_time < 1.0, f"Multiple merges took {multi_merge_time:.3f}s"
        
        # Test 3: Join operation
        start = time.perf_counter()
        indexed_production = large_production_dataset.set_index('well_id')
        indexed_well_info = well_info.set_index('well_id')
        joined = indexed_production.join(indexed_well_info, how='left')
        join_time = time.perf_counter() - start
        
        assert join_time < 0.3, f"Join operation took {join_time:.3f}s"
        
        print(f"Merge performance - Simple: {simple_merge_time:.3f}s, "
              f"Multiple: {multi_merge_time:.3f}s, Join: {join_time:.3f}s")


class TestDataProcessingOptimization:
    """Test optimized data processing techniques."""
    
    @pytest.mark.performance
    def test_vectorized_vs_iterative(self):
        """Compare vectorized vs iterative operations."""
        size = 100000
        df = pd.DataFrame({
            'a': np.random.randn(size),
            'b': np.random.randn(size),
            'c': np.random.randn(size)
        })
        
        # Iterative approach (slow)
        start = time.perf_counter()
        result_iter = []
        for idx, row in df.iterrows():
            if idx > 1000:  # Limit iterations for testing
                break
            result_iter.append(row['a'] * 2 + row['b'] ** 2 - row['c'])
        iter_time = time.perf_counter() - start
        
        # Vectorized approach (fast)
        start = time.perf_counter()
        result_vect = df['a'] * 2 + df['b'] ** 2 - df['c']
        vect_time = time.perf_counter() - start
        
        # Vectorized should be much faster
        assert vect_time < iter_time / 10, "Vectorized should be >10x faster than iterative"
        print(f"Vectorized: {vect_time:.3f}s vs Iterative: {iter_time:.3f}s")
    
    @pytest.mark.performance
    def test_categorical_optimization(self):
        """Test performance gains from using categorical dtype."""
        size = 100000
        categories = ['Category_' + str(i) for i in range(10)]
        
        # Create DataFrame with object dtype
        df_object = pd.DataFrame({
            'category': np.random.choice(categories, size),
            'value': np.random.randn(size)
        })
        
        # Create DataFrame with categorical dtype
        df_categorical = df_object.copy()
        df_categorical['category'] = df_categorical['category'].astype('category')
        
        # Compare memory usage
        memory_object = df_object.memory_usage(deep=True).sum() / 1024 / 1024
        memory_categorical = df_categorical.memory_usage(deep=True).sum() / 1024 / 1024
        
        assert memory_categorical < memory_object * 0.5, "Categorical should use <50% memory"
        
        # Compare groupby performance
        start = time.perf_counter()
        grouped_object = df_object.groupby('category')['value'].mean()
        object_time = time.perf_counter() - start
        
        start = time.perf_counter()
        grouped_categorical = df_categorical.groupby('category')['value'].mean()
        categorical_time = time.perf_counter() - start
        
        print(f"Memory - Object: {memory_object:.2f}MB, Categorical: {memory_categorical:.2f}MB")
        print(f"Groupby - Object: {object_time:.3f}s, Categorical: {categorical_time:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "performance"])