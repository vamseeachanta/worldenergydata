"""
Test suite for Optimized Multiple Wells Comparison Framework

This module tests the integration of performance optimization with
the multiple wells comparison framework for 120+ wells.
"""

import pytest
import pandas as pd
import numpy as np
import os
import tempfile
import shutil
import time
from pathlib import Path
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from optimized_multiple_wells_comparison_test import (
        OptimizedMultipleWellsComparisonFramework,
        create_sample_data,
        OPTIMIZER_INTEGRATION_AVAILABLE
    )
    from performance_optimizer import ResourceConstraints
    from strategic_report_generator import ReportConfig
    from advanced_comparison_engine import ComparisonConfig
except ImportError as e:
    OPTIMIZER_INTEGRATION_AVAILABLE = False
    print(f"Warning: Could not import optimized comparison framework: {e}")


@pytest.mark.skipif(not OPTIMIZER_INTEGRATION_AVAILABLE, reason="Optimized comparison framework not available")
class TestOptimizedMultipleWellsComparisonFramework:
    """Test optimized multiple wells comparison framework."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_datasets(self):
        """Create sample datasets for testing."""
        return create_sample_data(50)  # 50 wells for faster testing
    
    @pytest.fixture
    def framework(self, temp_dir):
        """Create optimized comparison framework instance."""
        performance_constraints = ResourceConstraints(
            max_chunk_size=20,  # Smaller chunks for testing
            enable_gc_optimization=True
        )
        
        report_config = ReportConfig(
            max_detailed_wells=10,
            include_charts=False,  # Disable charts for faster testing
            enable_appendix=False,
            results_directory=temp_dir
        )
        
        return OptimizedMultipleWellsComparisonFramework(
            performance_constraints=performance_constraints,
            report_config=report_config,
            results_directory=temp_dir
        )
    
    def test_framework_initialization(self, framework):
        """Test framework initialization."""
        assert framework.performance_optimizer is not None
        assert framework.comparison_engine is not None
        assert framework.report_generator is not None
        assert framework.results_directory.exists()
        
        # Check default configurations
        assert framework.performance_constraints.max_chunk_size == 20
        assert framework.report_config.max_detailed_wells == 10
        assert framework.comparison_config.enable_clustering == True
    
    def test_optimized_comparison_basic(self, framework, sample_datasets):
        """Test basic optimized comparison functionality."""
        lease_data, api12_data = sample_datasets
        
        progress_messages = []
        def progress_callback(message):
            progress_messages.append(message)
        
        # Run optimized comparison
        results = framework.run_optimized_comparison(
            lease_data, api12_data, progress_callback
        )
        
        # Verify results structure
        assert 'comparison_results' in results
        assert 'statistical_summary' in results
        assert 'report_path' in results
        assert 'export_paths' in results
        assert 'performance_metrics' in results
        
        # Verify comparison results
        comparison_results = results['comparison_results']
        assert len(comparison_results) == 50
        assert all(hasattr(r, 'api12') for r in comparison_results)
        assert all(hasattr(r, 'overall_status') for r in comparison_results)
        
        # Verify statistical summary
        statistical_summary = results['statistical_summary']
        assert statistical_summary.total_wells == 50
        assert statistical_summary.successful_matches <= 50
        
        # Verify report generation
        assert os.path.exists(results['report_path'])
        assert results['report_path'].endswith('.md')
        
        # Verify exports
        export_paths = results['export_paths']
        assert 'csv_results' in export_paths
        assert 'json_summary' in export_paths
        assert os.path.exists(export_paths['csv_results'])
        assert os.path.exists(export_paths['json_summary'])
        
        # Verify performance metrics
        perf_metrics = results['performance_metrics']
        assert 'total_execution_time' in perf_metrics
        assert 'wells_processed' in perf_metrics
        assert 'wells_per_second' in perf_metrics
        assert 'optimization_metrics' in perf_metrics
        assert 'average_memory_efficiency' in perf_metrics
        
        assert perf_metrics['total_execution_time'] > 0
        assert perf_metrics['wells_processed'] == 50
        assert perf_metrics['wells_per_second'] > 0
        assert 0 <= perf_metrics['average_memory_efficiency'] <= 100
        
        # Verify progress tracking
        assert len(progress_messages) > 0
        assert any('Starting optimized comparison' in msg for msg in progress_messages)
        assert any('Analysis complete' in msg for msg in progress_messages)
    
    def test_performance_benchmarking(self, framework, sample_datasets):
        """Test performance benchmarking functionality."""
        lease_data, api12_data = sample_datasets
        
        # Run benchmark with 2 iterations for speed
        benchmark_results = framework.benchmark_performance(
            lease_data, api12_data, iterations=2
        )
        
        # Verify benchmark structure
        assert 'benchmark_results' in benchmark_results
        assert 'summary' in benchmark_results
        assert 'system_info' in benchmark_results
        assert 'framework_analysis' in benchmark_results
        
        # Verify framework-specific analysis
        framework_analysis = benchmark_results['framework_analysis']
        assert framework_analysis['optimization_enabled'] == True
        assert 'memory_management' in framework_analysis
        assert 'recommended_settings' in framework_analysis
        
        recommended_settings = framework_analysis['recommended_settings']
        assert 'max_chunk_size' in recommended_settings
        assert 'enable_charts' in recommended_settings
        assert 'enable_appendix' in recommended_settings
    
    def test_optimization_summary(self, framework, sample_datasets):
        """Test optimization performance summary."""
        lease_data, api12_data = sample_datasets
        
        # Initially no data
        summary = framework.get_optimization_summary()
        assert 'message' in summary
        
        # Run comparison to generate data
        framework.run_optimized_comparison(lease_data, api12_data)
        
        # Now should have summary data
        summary = framework.get_optimization_summary()
        
        assert 'total_wells_processed' in summary
        assert 'total_operations' in summary
        assert 'optimization_performance' in summary
        assert 'comparison_performance' in summary
        assert 'report_generation_performance' in summary
        assert 'overall_memory_efficiency' in summary
        assert 'system_recommendations' in summary
        
        assert summary['total_wells_processed'] == 50
        assert summary['total_operations'] > 0
        assert 0 <= summary['overall_memory_efficiency'] <= 100
    
    def test_performance_validation_targets(self, framework):
        """Test performance target validation."""
        # Test with smaller dataset for speed
        validation_results = framework.validate_performance_targets(target_wells=30)
        
        # Verify validation structure
        assert 'validation_results' in validation_results
        assert 'performance_details' in validation_results
        assert 'recommendations' in validation_results
        
        # Check validation results
        validation = validation_results['validation_results']
        expected_targets = [
            'execution_time_under_60s',
            'wells_per_second_over_2', 
            'memory_efficiency_over_70',
            'successful_processing',
            'report_generated',
            'exports_created',
            'all_targets_met'
        ]
        
        for target in expected_targets:
            assert target in validation
            assert isinstance(validation[target], bool)
        
        # Check performance details
        details = validation_results['performance_details']
        assert 'total_execution_time' in details
        assert 'wells_processed' in details
        assert 'wells_per_second' in details
        assert 'memory_efficiency' in details
        assert 'system_resources' in details
        
        assert details['wells_processed'] == 30
        assert details['total_execution_time'] > 0
        
        # Check recommendations
        recommendations = validation_results['recommendations']
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
    
    def test_memory_optimization_integration(self, framework, sample_datasets):
        """Test memory optimization integration."""
        lease_data, api12_data = sample_datasets
        
        # Add memory-intensive columns to test optimization
        lease_data['large_numbers'] = np.random.randint(0, 100, len(lease_data))  # Can be int8
        lease_data['categories'] = np.random.choice(['A', 'B', 'C'], len(lease_data))  # Can be category
        
        api12_data['large_numbers'] = np.random.randint(0, 100, len(api12_data))
        api12_data['categories'] = np.random.choice(['A', 'B', 'C'], len(api12_data))
        
        # Get initial memory usage
        initial_memory = (lease_data.memory_usage(deep=True).sum() + 
                         api12_data.memory_usage(deep=True).sum()) / 1024 / 1024
        
        results = framework.run_optimized_comparison(lease_data, api12_data)
        
        # Check that memory optimization occurred
        optimization_metrics = results['performance_metrics']['optimization_metrics']
        
        # Should have good memory efficiency scores
        lease_efficiency = optimization_metrics['lease_data'].memory_efficiency_score
        api12_efficiency = optimization_metrics['api12_data'].memory_efficiency_score
        
        assert lease_efficiency > 50  # At least moderate efficiency
        assert api12_efficiency > 50
        
        # Overall process should be efficient
        avg_efficiency = results['performance_metrics']['average_memory_efficiency']
        assert avg_efficiency > 60  # Good overall efficiency
    
    def test_error_handling_and_resilience(self, framework):
        """Test error handling and system resilience."""
        # Test with empty datasets
        empty_lease = pd.DataFrame(columns=['API12', 'Well Name', 'Drilling Days', 'Completion Days'])
        empty_api12 = pd.DataFrame(columns=['API12', 'Well Name', 'Drilling Days', 'Completion Days'])
        
        # Should handle empty data gracefully
        try:
            results = framework.run_optimized_comparison(empty_lease, empty_api12)
            # If it succeeds, check it handled empty data properly
            assert len(results['comparison_results']) == 0
        except Exception as e:
            # If it raises an exception, it should be a meaningful one
            assert 'empty' in str(e).lower() or 'no data' in str(e).lower()
        
        # Test with mismatched datasets (different APIs)
        lease_data = pd.DataFrame({
            'API12': ['60812400001', '60812400002'],
            'Well Name': ['Well 1', 'Well 2'],
            'Drilling Days': [40, 45],
            'Completion Days': [15, 18]
        })
        
        api12_data = pd.DataFrame({
            'API12': ['60812400003', '60812400004'],  # Different APIs
            'Well Name': ['Well 3', 'Well 4'],
            'Drilling Days': [42, 47],
            'Completion Days': [16, 19]
        })
        
        # Should handle mismatched data appropriately
        try:
            results = framework.run_optimized_comparison(lease_data, api12_data)
            # If successful, should have no matches
            assert len(results['comparison_results']) == 0
        except Exception as e:
            # Should raise meaningful error about no matches
            assert 'match' in str(e).lower() or 'merge' in str(e).lower()


@pytest.mark.skipif(not OPTIMIZER_INTEGRATION_AVAILABLE, reason="Optimized comparison framework not available")
class TestOptimizedFrameworkIntegration:
    """Integration tests for optimized framework with large datasets."""
    
    def test_120_plus_wells_integration(self):
        """Test integration with 120+ wells."""
        # Create 125 wells dataset
        lease_data, api12_data = create_sample_data(125)
        
        # Create framework optimized for large datasets
        performance_constraints = ResourceConstraints(
            max_chunk_size=40,
            memory_warning_threshold=0.7,
            enable_gc_optimization=True
        )
        
        report_config = ReportConfig(
            max_detailed_wells=25,
            summary_top_n=15,
            include_charts=False,  # Disable for performance
            enable_appendix=False
        )
        
        framework = OptimizedMultipleWellsComparisonFramework(
            performance_constraints=performance_constraints,
            report_config=report_config
        )
        
        # Track performance
        start_time = time.time()
        
        progress_updates = []
        def track_progress(message):
            progress_updates.append(message)
        
        # Run optimized comparison
        results = framework.run_optimized_comparison(
            lease_data, api12_data, track_progress
        )
        
        total_time = time.time() - start_time
        
        # Verify successful processing
        assert len(results['comparison_results']) == 125
        assert os.path.exists(results['report_path'])
        
        # Verify performance targets
        performance_metrics = results['performance_metrics']
        assert performance_metrics['wells_processed'] == 125
        assert performance_metrics['total_execution_time'] < 60  # Under 1 minute
        assert performance_metrics['wells_per_second'] > 1  # At least 1 well/second
        assert performance_metrics['average_memory_efficiency'] >= 0  # Should be non-negative
        
        # Verify optimization occurred
        opt_metrics = performance_metrics['optimization_metrics']
        assert all(m.memory_efficiency_score >= 0 for m in opt_metrics.values())
        
        # Verify progress tracking
        assert len(progress_updates) > 0
        assert any('125 wells' in msg or '125' in msg for msg in progress_updates)
        
        print(f"✓ Successfully processed 125 wells in {total_time:.2f} seconds")
        print(f"✓ Performance: {performance_metrics['wells_per_second']:.1f} wells/second")
        print(f"✓ Memory efficiency: {performance_metrics['average_memory_efficiency']:.1f}%")
    
    def test_performance_scalability(self):
        """Test performance scalability with different dataset sizes."""
        dataset_sizes = [50, 100, 150]
        performance_results = []
        
        for size in dataset_sizes:
            lease_data, api12_data = create_sample_data(size)
            
            framework = OptimizedMultipleWellsComparisonFramework(
                performance_constraints=ResourceConstraints(
                    max_chunk_size=min(50, size // 3),  # Adaptive chunk size
                    enable_gc_optimization=True
                ),
                report_config=ReportConfig(
                    include_charts=False,
                    enable_appendix=False
                )
            )
            
            start_time = time.time()
            results = framework.run_optimized_comparison(lease_data, api12_data)
            execution_time = time.time() - start_time
            
            performance_results.append({
                'dataset_size': size,
                'execution_time': execution_time,
                'wells_per_second': results['performance_metrics']['wells_per_second'],
                'memory_efficiency': results['performance_metrics']['average_memory_efficiency']
            })
        
        # Verify scalability
        for i, result in enumerate(performance_results):
            assert result['wells_per_second'] > 0.5  # Minimum performance
            assert result['memory_efficiency'] > 40  # Minimum efficiency
            
            print(f"Dataset {result['dataset_size']} wells: "
                  f"{result['execution_time']:.2f}s, "
                  f"{result['wells_per_second']:.1f} wells/s, "
                  f"{result['memory_efficiency']:.1f}% efficiency")
        
        # Performance should remain reasonable as dataset grows
        largest_result = performance_results[-1]  # 150 wells
        assert largest_result['execution_time'] < 90  # Under 1.5 minutes
        assert largest_result['wells_per_second'] > 1  # At least 1 well/second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])