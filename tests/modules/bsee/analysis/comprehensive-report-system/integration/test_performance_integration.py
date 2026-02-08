"""
Integration Tests for Performance-Enhanced Report System

Tests the integration of caching and parallel processing with the report controller.
"""

import pytest
import time
import pandas as pd
import numpy as np
from datetime import datetime, date
from pathlib import Path
import tempfile

from worldenergydata.bsee.reports.comprehensive.controller_performance import (
    PerformanceReportController,
    PerformanceConfiguration,
    ReportConfiguration,
    ReportParameters,
    ReportType
)
from worldenergydata.bsee.reports.comprehensive.performance.cache import CacheManager
from worldenergydata.bsee.reports.comprehensive.performance.parallel_processor import ParallelProcessor


class TestPerformanceIntegration:
    """Test integration of performance optimizations with report system."""
    
    @pytest.fixture
    def perf_config(self):
        """Create performance configuration for testing."""
        return PerformanceConfiguration(
            cache_enabled=True,
            cache_ttl_seconds=60,
            cache_max_size_mb=100,
            parallel_enabled=True,
            max_workers=4,
            use_threads=True,
            batch_size=100,
            log_performance_metrics=True
        )
    
    @pytest.fixture
    def controller(self, perf_config):
        """Create performance-enhanced controller."""
        return PerformanceReportController(perf_config=perf_config)
    
    @pytest.fixture
    def sample_data(self):
        """Generate sample data for testing."""
        np.random.seed(42)
        
        data = []
        for block in ['MC 123', 'MC 456']:
            for field in ['Field_A', 'Field_B']:
                for lease in ['LEASE001', 'LEASE002']:
                    for well_idx in range(10):
                        for month in range(1, 7):
                            data.append({
                                'block': block,
                                'field': field,
                                'lease': lease,
                                'well_id': f'{block}_{field}_{lease}_W{well_idx:02d}',
                                'production_date': datetime(2024, month, 1),
                                'oil_volume_bbl': np.random.uniform(1000, 5000),
                                'gas_volume_mcf': np.random.uniform(500, 2500),
                                'water_volume_bbl': np.random.uniform(100, 1000),
                                'production_days': 30
                            })
        
        return pd.DataFrame(data)
    
    def test_controller_initialization(self, perf_config):
        """Test that performance controller initializes correctly."""
        controller = PerformanceReportController(perf_config=perf_config)
        
        assert controller is not None
        assert controller.cache_manager is not None
        assert controller.parallel_processor is not None
        assert controller.perf_config.cache_enabled is True
        assert controller.perf_config.parallel_enabled is True
    
    def test_cache_integration(self, controller):
        """Test that caching is working with the controller."""
        # Create report configuration
        config = ReportConfiguration(
            report_type=ReportType.BLOCK,
            entity_name='MC 123',
            date_range=(date(2024, 1, 1), date(2024, 6, 30))
        )
        params = ReportParameters()
        
        # First generation - should be cache miss
        start_time = time.time()
        result1 = controller.generate_report(config, params)
        first_time = time.time() - start_time
        
        # Second generation - should be cache hit
        start_time = time.time()
        result2 = controller.generate_report(config, params)
        second_time = time.time() - start_time
        
        # Cache should make second call much faster
        assert second_time < first_time / 2
        
        # Check cache statistics
        stats = controller.get_performance_stats()
        assert stats['controller_metrics']['cache_hits'] >= 1
        assert stats['controller_metrics']['cache_misses'] >= 1
    
    def test_parallel_processing_integration(self, controller, sample_data):
        """Test that parallel processing is working."""
        # Mock the data loading method
        controller._load_data_for_report = lambda config: sample_data
        
        # Create block report configuration (should use parallel processing)
        config = ReportConfiguration(
            report_type=ReportType.BLOCK,
            entity_name='MC 123',
            date_range=(date(2024, 1, 1), date(2024, 6, 30))
        )
        params = ReportParameters()
        
        # Generate report with parallel processing
        result = controller.generate_report(config, params)
        
        assert result['status'] == 'success'
        
        # Check that parallel processing was used
        stats = controller.get_performance_stats()
        assert stats['controller_metrics']['parallel_tasks'] >= 1
    
    def test_batch_report_generation(self, controller):
        """Test batch generation of multiple reports."""
        # Create multiple report configurations
        configs = [
            ReportConfiguration(
                report_type=ReportType.BLOCK,
                entity_name=f'MC {i:03d}',
                date_range=(date(2024, 1, 1), date(2024, 6, 30))
            )
            for i in range(5)
        ]
        params = ReportParameters()
        
        # Generate reports in batch
        start_time = time.time()
        results = controller.batch_generate_reports(configs, params)
        batch_time = time.time() - start_time
        
        # All reports should be generated
        assert len(results) == len(configs)
        
        # Generate same reports sequentially for comparison
        start_time = time.time()
        sequential_results = []
        for config in configs:
            sequential_results.append(controller.generate_report(config, params))
        sequential_time = time.time() - start_time
        
        # Batch should be faster than sequential (accounting for cache)
        # Clear cache before sequential to ensure fair comparison
        controller.clear_cache()
        assert batch_time <= sequential_time
    
    def test_performance_with_caching_disabled(self):
        """Test performance when caching is disabled."""
        # Create controller without caching
        perf_config = PerformanceConfiguration(
            cache_enabled=False,
            parallel_enabled=True
        )
        controller = PerformanceReportController(perf_config=perf_config)
        
        assert controller.cache_manager is None
        
        # Generate report
        config = ReportConfiguration(
            report_type=ReportType.FIELD,
            entity_name='Field_A',
            date_range=(date(2024, 1, 1), date(2024, 6, 30))
        )
        params = ReportParameters()
        
        # Should work without caching
        result = controller.generate_report(config, params)
        assert result is not None
        
        # Cache stats should be empty
        stats = controller.get_performance_stats()
        assert stats['cache_stats'] == {}
    
    def test_performance_with_parallel_disabled(self):
        """Test performance when parallel processing is disabled."""
        # Create controller without parallel processing
        perf_config = PerformanceConfiguration(
            cache_enabled=True,
            parallel_enabled=False
        )
        controller = PerformanceReportController(perf_config=perf_config)
        
        assert controller.parallel_processor is None
        
        # Generate report
        config = ReportConfiguration(
            report_type=ReportType.BLOCK,
            entity_name='MC 123',
            date_range=(date(2024, 1, 1), date(2024, 6, 30))
        )
        params = ReportParameters()
        
        # Should work without parallel processing
        result = controller.generate_report(config, params)
        assert result is not None
        
        # Parallel tasks should be 0
        stats = controller.get_performance_stats()
        assert stats['controller_metrics']['parallel_tasks'] == 0
    
    def test_cache_invalidation(self, controller):
        """Test cache invalidation functionality."""
        config = ReportConfiguration(
            report_type=ReportType.LEASE,
            entity_name='LEASE001',
            date_range=(date(2024, 1, 1), date(2024, 6, 30))
        )
        params = ReportParameters()
        
        # Generate and cache report
        result1 = controller.generate_report(config, params)
        
        # Clear cache
        controller.clear_cache()
        
        # Next generation should be cache miss
        initial_misses = controller.performance_metrics['cache_misses']
        result2 = controller.generate_report(config, params)
        
        assert controller.performance_metrics['cache_misses'] > initial_misses
    
    def test_memory_efficient_processing(self, controller):
        """Test memory-efficient processing for large datasets."""
        # Configure for memory-efficient processing
        controller.perf_config.batch_size = 50
        controller.perf_config.max_memory_mb = 100
        
        # Create large dataset simulation
        large_data = pd.DataFrame({
            'block': ['MC 123'] * 1000,
            'field': ['Field_A'] * 1000,
            'lease': ['LEASE001'] * 1000,
            'well_id': [f'W{i:04d}' for i in range(1000)],
            'oil_volume_bbl': np.random.uniform(1000, 5000, 1000)
        })
        
        # Mock data loading
        controller._load_data_for_report = lambda config: large_data
        
        # Generate report with memory constraints
        config = ReportConfiguration(
            report_type=ReportType.LEASE,
            entity_name='LEASE001',
            date_range=(date(2024, 1, 1), date(2024, 6, 30))
        )
        params = ReportParameters()
        
        result = controller.generate_report(config, params)
        assert result['status'] == 'success'
    
    def test_performance_statistics(self, controller):
        """Test performance statistics collection."""
        # Generate several reports
        for i in range(3):
            config = ReportConfiguration(
                report_type=ReportType.FIELD,
                entity_name=f'Field_{i}',
                date_range=(date(2024, 1, 1), date(2024, 6, 30))
            )
            params = ReportParameters()
            controller.generate_report(config, params)
        
        # Get statistics
        stats = controller.get_performance_stats()
        
        assert 'controller_metrics' in stats
        assert 'cache_stats' in stats
        assert 'configuration' in stats
        
        # Should have some cache activity
        assert stats['controller_metrics']['cache_hits'] + stats['controller_metrics']['cache_misses'] > 0
        
        # Configuration should match
        assert stats['configuration']['cache_enabled'] == controller.perf_config.cache_enabled
        assert stats['configuration']['parallel_enabled'] == controller.perf_config.parallel_enabled
    
    @pytest.mark.integration
    def test_end_to_end_performance_improvement(self, controller, sample_data):
        """Test end-to-end performance improvement with optimizations."""
        # Mock data loading
        controller._load_data_for_report = lambda config: sample_data
        
        # Create a standard controller without optimizations for comparison
        standard_config = PerformanceConfiguration(
            cache_enabled=False,
            parallel_enabled=False
        )
        standard_controller = PerformanceReportController(perf_config=standard_config)
        standard_controller._load_data_for_report = lambda config: sample_data
        
        config = ReportConfiguration(
            report_type=ReportType.BLOCK,
            entity_name='MC 123',
            date_range=(date(2024, 1, 1), date(2024, 6, 30))
        )
        params = ReportParameters()
        
        # Generate with standard controller
        start_time = time.time()
        standard_result = standard_controller.generate_report(config, params)
        standard_time = time.time() - start_time
        
        # Generate with optimized controller (first time - no cache)
        start_time = time.time()
        optimized_result = controller.generate_report(config, params)
        optimized_time_first = time.time() - start_time
        
        # Generate with optimized controller (second time - with cache)
        start_time = time.time()
        optimized_result_cached = controller.generate_report(config, params)
        optimized_time_cached = time.time() - start_time
        
        # Cached should be significantly faster
        assert optimized_time_cached < standard_time / 2
        
        # Both should produce valid results
        assert standard_result['status'] == 'success'
        assert optimized_result['status'] == 'success'
        assert optimized_result_cached['status'] == 'success'