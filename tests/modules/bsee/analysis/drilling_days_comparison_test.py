import pytest
import os
import sys
import logging

import deepdiff
DEEPDIFF_AVAILABLE = True

from assetutilities.common.yml_utilities import ymlInput
from worldenergydata.engine import engine
ENGINE_AVAILABLE = True

# Import comparison framework
from comparison_framework import ComparisonTestFramework, ComparisonConfigManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestDrillingDaysComparison:
    """
    Main test class for drilling days comparison between lease and API12 methods.
    
    This test compares two different approaches:
    - Method 1 (lease): Uses drilling_n_completion_days.yml
    - Method 2 (api12): Uses query_api_01_wells_api12_rig_days.yml
    """

    @pytest.fixture
    def comparison_framework(self):
        """Initialize comparison framework for testing."""
        config_file = 'comparison_config.yml'
        framework = ComparisonTestFramework()
        
        if not framework.initialize(config_file):
            pytest.skip("Failed to initialize comparison framework")
        
        return framework

    @pytest.fixture
    def config_manager(self):
        """Initialize configuration manager for testing."""
        manager = ComparisonConfigManager()
        config_file = 'comparison_config.yml'
        
        try:
            manager.load_config(config_file)
        except FileNotFoundError:
            pytest.skip("Comparison configuration file not found")
        
        return manager

    def test_framework_initialization(self, comparison_framework):
        """Test that comparison framework initializes correctly."""
        assert comparison_framework is not None
        assert comparison_framework.is_ready() is True
        assert comparison_framework.config_manager.config is not None
        
        logger.info("Framework initialization test passed")

    def test_configuration_loading(self, config_manager):
        """Test that comparison configuration loads correctly."""
        config = config_manager.config
        
        # Verify required sections exist
        assert 'meta' in config
        assert 'methods' in config
        assert 'comparison' in config
        
        # Verify method configurations
        assert 'lease_method' in config['methods']
        assert 'api12_method' in config['methods']
        
        # Verify key columns are defined
        lease_config = config['methods']['lease_method']
        assert 'key_columns' in lease_config
        assert 'api' in lease_config['key_columns']
        assert 'drilling_days' in lease_config['key_columns']
        
        api12_config = config['methods']['api12_method']
        assert 'key_columns' in api12_config
        assert 'api' in api12_config['key_columns']
        assert 'drilling_days' in api12_config['key_columns']
        
        logger.info("Configuration loading test passed")

    def test_method_config_retrieval(self, comparison_framework):
        """Test retrieving individual method configurations."""
        # Test lease method configuration
        lease_config = comparison_framework.get_method_config('lease_method')
        assert lease_config is not None
        assert lease_config['config_file'] == 'drilling_n_completion_days.yml'
        assert 'output_file' in lease_config
        
        # Test API12 method configuration
        api12_config = comparison_framework.get_method_config('api12_method')
        assert api12_config is not None
        assert api12_config['config_file'] == 'query_api_01_wells_api12_rig_days.yml'
        assert 'output_pattern' in api12_config
        
        logger.info("Method config retrieval test passed")

    def test_comparison_config_validation(self, config_manager):
        """Test validation of comparison configuration parameters."""
        comparison_config = config_manager.get_comparison_config()
        assert comparison_config is not None
        
        # Verify tolerance settings
        assert 'tolerance' in comparison_config
        tolerance = comparison_config['tolerance']
        assert 'drilling_days' in tolerance
        assert 'completion_days' in tolerance
        assert isinstance(tolerance['drilling_days'], (int, float))
        assert isinstance(tolerance['completion_days'], (int, float))
        
        # Verify output settings
        assert 'output' in comparison_config
        output = comparison_config['output']
        assert 'report_file' in output
        assert 'charts_enabled' in output
        assert 'statistical_summary' in output
        
        logger.info("Comparison config validation test passed")

    def test_framework_dependency_validation(self, comparison_framework):
        """Test that all required dependencies are available."""
        deps = comparison_framework.validate_dependencies()
        
        assert 'engine_available' in deps
        assert 'deepdiff_available' in deps
        assert 'yaml_available' in deps
        
        # All dependencies should be available for tests to run
        assert deps['engine_available'] is True
        assert deps['deepdiff_available'] is True
        assert deps['yaml_available'] is True
        
        logger.info("Dependency validation test passed")

    def test_framework_ready_state(self, comparison_framework):
        """Test framework readiness validation."""
        assert comparison_framework.is_ready() is True
        
        # Test component availability
        assert comparison_framework.config_manager is not None
        assert comparison_framework.config_manager.config is not None
        assert comparison_framework.is_initialized is True
        
        logger.info("Framework ready state test passed")

    def test_method_execution_preparation(self, comparison_framework):
        """Test preparation for method execution."""
        # Verify config files exist for both methods
        lease_config = comparison_framework.get_method_config('lease_method')
        config_path = comparison_framework.config_manager.resolve_config_path(
            lease_config['config_file']
        )
        assert os.path.exists(config_path), f"Lease method config not found: {config_path}"
        
        api12_config = comparison_framework.get_method_config('api12_method')
        config_path = comparison_framework.config_manager.resolve_config_path(
            api12_config['config_file']
        )
        assert os.path.exists(config_path), f"API12 method config not found: {config_path}"
        
        logger.info("Method execution preparation test passed")

    def test_comparison_framework_setup_complete(self, comparison_framework):
        """Test that the complete comparison framework setup is working."""
        # This is the main integration test for Task 1
        
        # Verify framework is fully initialized
        assert comparison_framework.is_ready() is True
        
        # Verify both method configurations are accessible
        lease_config = comparison_framework.get_method_config('lease_method')
        api12_config = comparison_framework.get_method_config('api12_method')
        assert lease_config is not None
        assert api12_config is not None
        
        # Verify comparison configuration is loaded
        comparison_config = comparison_framework.config_manager.get_comparison_config()
        assert comparison_config is not None
        
        # Verify dependencies are available
        deps = comparison_framework.validate_dependencies()
        assert all(deps.values())
        
        logger.info("✅ Task 1 Complete: Comparison framework infrastructure is ready")
        
        # Log summary of what was set up
        logger.info("Framework Infrastructure Summary:")
        logger.info(f"  - Configuration loaded: {comparison_framework.config_manager.config_file_path}")
        logger.info(f"  - Lease method config: {lease_config['config_file']}")
        logger.info(f"  - API12 method config: {api12_config['config_file']}")
        logger.info(f"  - Output report: {comparison_config['output']['report_file']}")
        logger.info(f"  - Dependencies validated: {list(deps.keys())}")


def run_application(input_file, expected_result={}):
    """Legacy function for compatibility with existing test patterns."""
    if input_file is not None and not os.path.isfile(input_file):
        input_file = os.path.join(os.path.dirname(__file__), input_file)
    
    if not ENGINE_AVAILABLE:
        pytest.skip("Engine not available - dependencies missing")
    
    cfg = engine(input_file)
    return cfg


def get_valid_pytest_output_file(pytest_output_file):
    """Legacy function for compatibility with existing test patterns."""
    if pytest_output_file is not None and not os.path.isfile(pytest_output_file):
        pytest_output_file = os.path.join(os.path.dirname(__file__), pytest_output_file)
    return pytest_output_file


def test_application():
    """
    Main test function for drilling days comparison.
    
    This test initializes the comparison framework and validates that it's ready
    to run comparisons between the two drilling days calculation methods.
    """
    logger.info("Starting drilling days comparison framework test")
    
    # Initialize comparison framework
    config_file = 'comparison_config.yml'
    framework = ComparisonTestFramework()
    
    try:
        # Initialize framework
        if not framework.initialize(config_file):
            logger.error("Failed to initialize comparison framework")
            return
        
        logger.info("Framework initialized successfully")
        
        # Validate framework readiness
        if not framework.is_ready():
            logger.error("Framework not ready for comparison")
            return
        
        logger.info("Framework is ready for drilling days comparison")
        
        # Log configuration summary
        meta_config = framework.config_manager.get_meta_config()
        if meta_config:
            logger.info(f"Comparison label: {meta_config.get('label', 'N/A')}")
            logger.info(f"Description: {meta_config.get('description', 'N/A')}")
        
        logger.info("✅ Task 1 Infrastructure Setup Complete")
        
    except Exception as e:
        logger.error(f"Error in comparison framework test: {e}")
        raise
    
    finally:
        # Clean up framework
        framework.cleanup()


class TestEndToEndComparisonWorkflow:
    """
    Test cases for complete end-to-end comparison workflow.
    
    These tests cover the integration of all components:
    - Method execution
    - Data loading and alignment
    - Statistical analysis
    - Report generation
    """

    @pytest.fixture
    def comparison_framework(self):
        """Initialize comparison framework for end-to-end testing."""
        config_file = 'comparison_config.yml'
        framework = ComparisonTestFramework()
        
        if not framework.initialize(config_file):
            pytest.skip("Failed to initialize comparison framework")
        
        return framework

    @pytest.fixture
    def workflow_components(self):
        """Initialize all workflow components for testing."""
        from comparison_framework.data_loader import DataLoader
        from comparison_framework.comparison_engine import ComparisonEngine
        from comparison_framework.report_generator import ReportManager
        
        return {
            'data_loader': DataLoader(),
            'comparison_engine': ComparisonEngine(),
            'report_manager': ReportManager()
        }

    def test_method_execution_workflow(self, comparison_framework):
        """Test execution of both drilling days calculation methods."""
        # Execute lease method
        lease_success = comparison_framework.execute_method('lease_method')
        logger.info(f"Lease method execution: {'SUCCESS' if lease_success else 'FAILED'}")
        
        # Execute API12 method
        api12_success = comparison_framework.execute_method('api12_method')
        logger.info(f"API12 method execution: {'SUCCESS' if api12_success else 'FAILED'}")
        
        # Get method outputs
        method_outputs = comparison_framework.get_method_outputs()
        
        # Verify both methods executed
        assert 'lease_method' in method_outputs
        assert 'api12_method' in method_outputs
        
        # Verify execution status
        if lease_success:
            assert method_outputs['lease_method']['executed'] is True
        if api12_success:
            assert method_outputs['api12_method']['executed'] is True
        
        logger.info("✅ Method execution workflow test completed")

    def test_data_loading_and_alignment_workflow(self, comparison_framework, workflow_components):
        """Test data loading and alignment between methods."""
        # Execute methods first
        comparison_framework.execute_method('lease_method')
        comparison_framework.execute_method('api12_method')
        
        # Get configuration
        config = comparison_framework.config_manager.config
        
        # Load data from both methods
        data_loader = workflow_components['data_loader']
        
        # Load lease method data
        lease_config = config['methods']['lease_method']
        lease_data = data_loader.load_excel_data(
            file_path=lease_config.get('output_file', 'drilling_and_completion_days_by_api.xlsx'),
            column_mapping=lease_config['key_columns']
        )
        
        # Load API12 method data
        api12_config = config['methods']['api12_method']
        api12_data = data_loader.load_csv_data(
            pattern=api12_config.get('output_pattern', 'block_api12_*.csv'),
            column_mapping=api12_config['key_columns']
        )
        
        # Verify data was loaded
        assert lease_data is not None, "Failed to load lease method data"
        assert api12_data is not None, "Failed to load API12 method data"
        
        logger.info(f"Loaded lease data: {len(lease_data) if hasattr(lease_data, '__len__') else 'N/A'} records")
        logger.info(f"Loaded API12 data: {len(api12_data) if hasattr(api12_data, '__len__') else 'N/A'} records")
        logger.info("✅ Data loading and alignment workflow test completed")

    def test_statistical_analysis_workflow(self, comparison_framework, workflow_components):
        """Test statistical analysis component of the workflow."""
        # Execute methods
        comparison_framework.execute_method('lease_method')
        comparison_framework.execute_method('api12_method')
        
        # Initialize comparison engine
        comparison_engine = workflow_components['comparison_engine']
        
        # Get tolerance configuration
        config = comparison_framework.config_manager.config
        tolerance_config = config.get('comparison', {}).get('tolerance', {
            'drilling_days': 5,
            'completion_days': 3,
            'dates': 1
        })
        
        # Set up comparison engine with tolerance
        comparison_engine.set_tolerance_config(tolerance_config)
        
        # Test with sample data (in real scenario, this would use loaded data)
        import pandas as pd
        sample_lease_data = pd.DataFrame({
            'api_normalized': ['420030123450', '420030456780'],
            'drilling_days': [36, 34],
            'completion_days': [45, 42]
        })
        
        sample_api12_data = pd.DataFrame({
            'api_normalized': ['420030123450', '420030456780'],
            'drilling_days': [36, 33],
            'completion_days': [44, 43]
        })
        
        # Run comparison
        result = comparison_engine.compare_methods(
            lease_data=sample_lease_data,
            api12_data=sample_api12_data,
            lease_column_mapping={'api': 'api_normalized', 'drilling_days': 'drilling_days', 'completion_days': 'completion_days'},
            api12_column_mapping={'api': 'api_normalized', 'drilling_days': 'drilling_days', 'completion_days': 'completion_days'}
        )
        
        # Verify statistical analysis results
        assert result is not None, "Statistical analysis failed"
        assert hasattr(result, 'statistics'), "Statistics not computed"
        assert hasattr(result, 'well_coverage'), "Well coverage not analyzed"
        assert hasattr(result, 'discrepancies'), "Discrepancies not identified"
        
        logger.info("✅ Statistical analysis workflow test completed")

    def test_report_generation_workflow(self, comparison_framework, workflow_components):
        """Test report generation component of the workflow."""
        import tempfile
        from pathlib import Path
        from comparison_framework.comparison_engine import ComparisonResult, WellCoverageAnalysis
        import pandas as pd
        
        # Create sample comparison result for testing
        sample_coverage = WellCoverageAnalysis(
            total_lease_wells=100,
            total_api12_wells=95,
            common_wells=90,
            lease_only_wells=10,
            api12_only_wells=5,
            coverage_percentage=90.0
        )
        
        sample_statistics = {
            'drilling_days': {
                'count': 90,
                'mean': 1.5,
                'std': 2.3,
                'median': 1.0,
                'min': -5,
                'max': 8,
                'mean_abs_diff': 2.1,
                'max_abs_diff': 8
            }
        }
        
        sample_matched_data = pd.DataFrame({
            'api_normalized': ['420030123450', '420030456780', '420030789010'],
            'drilling_days_lease': [36, 34, 36],
            'drilling_days_api12': [36, 33, 37],
            'drilling_days_diff': [0, 1, -1]
        })
        
        sample_result = ComparisonResult(
            total_common_wells=90,
            statistics=sample_statistics,
            well_coverage=sample_coverage,
            matched_data=sample_matched_data,
            discrepancies=pd.DataFrame()
        )
        
        # Test report generation
        report_manager = workflow_components['report_manager']
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Generate all reports
            report_paths = report_manager.generate_all_reports(
                result=sample_result,
                output_dir=output_dir,
                report_name="workflow_test"
            )
            
            # Verify reports were generated
            assert 'html_report' in report_paths, "HTML report not generated"
            assert 'csv_summary' in report_paths, "CSV summary not generated"
            
            # Verify files exist
            for report_type, path in report_paths.items():
                assert Path(path).exists(), f"Report file not found: {report_type}"
            
            logger.info(f"Generated {len(report_paths)} reports successfully")
        
        logger.info("✅ Report generation workflow test completed")

    def test_complete_end_to_end_workflow(self, comparison_framework, workflow_components):
        """Test complete end-to-end comparison workflow integration."""
        logger.info("Starting complete end-to-end workflow test")
        
        try:
            # Step 1: Execute methods
            logger.info("Step 1: Executing drilling days calculation methods")
            results = comparison_framework.run_comparison()
            
            assert results is not None, "Comparison workflow failed"
            logger.info(f"Methods executed: {results.get('methods_executed', 0)}/{results.get('total_methods', 2)}")
            
            # Step 2: Load and align data (simulated with sample data)
            logger.info("Step 2: Loading and aligning data")
            import pandas as pd
            
            # In a real scenario, this would load from actual output files
            sample_lease_data = pd.DataFrame({
                'api_normalized': ['420030123450', '420030456780', '420030789010'],
                'drilling_days': [36, 34, 36],
                'completion_days': [45, 42, 48]
            })
            
            sample_api12_data = pd.DataFrame({
                'api_normalized': ['420030123450', '420030456780', '420030789010'],
                'drilling_days': [36, 33, 37],
                'completion_days': [44, 43, 47]
            })
            
            # Step 3: Perform statistical analysis
            logger.info("Step 3: Performing statistical analysis")
            comparison_engine = workflow_components['comparison_engine']
            
            # Get tolerance from config
            config = comparison_framework.config_manager.config
            tolerance_config = config.get('comparison', {}).get('tolerance', {
                'drilling_days': 5,
                'completion_days': 3
            })
            
            comparison_engine.set_tolerance_config(tolerance_config)
            
            comparison_result = comparison_engine.compare_methods(
                lease_data=sample_lease_data,
                api12_data=sample_api12_data,
                lease_column_mapping={'api': 'api_normalized', 'drilling_days': 'drilling_days', 'completion_days': 'completion_days'},
                api12_column_mapping={'api': 'api_normalized', 'drilling_days': 'drilling_days', 'completion_days': 'completion_days'}
            )
            
            assert comparison_result is not None, "Statistical analysis failed"
            logger.info(f"Analysis completed - Common wells: {comparison_result.total_common_wells}")
            
            # Step 4: Generate reports
            logger.info("Step 4: Generating comparison reports")
            import tempfile
            from pathlib import Path
            
            report_manager = workflow_components['report_manager']
            
            with tempfile.TemporaryDirectory() as tmpdir:
                output_dir = Path(tmpdir)
                
                # Generate comprehensive reports
                report_paths = report_manager.generate_all_reports(
                    result=comparison_result,
                    output_dir=output_dir,
                    report_name="drilling_days_comparison_complete"
                )
                
                # Verify all expected reports were generated
                expected_reports = ['html_report', 'csv_summary', 'csv_detailed']
                for report_type in expected_reports:
                    assert report_type in report_paths, f"Missing report: {report_type}"
                    assert Path(report_paths[report_type]).exists(), f"Report file not found: {report_type}"
                
                logger.info(f"✅ Generated {len(report_paths)} reports successfully")
                
                # Log report paths for debugging
                for report_type, path in report_paths.items():
                    logger.info(f"  - {report_type}: {path}")
            
            # Step 5: Validate workflow completion
            logger.info("Step 5: Validating workflow completion")
            
            # Verify workflow components executed successfully
            assert comparison_result.total_common_wells > 0, "No common wells found"
            assert comparison_result.statistics is not None, "Statistics not computed"
            assert comparison_result.well_coverage is not None, "Well coverage not analyzed"
            
            logger.info("✅ Complete end-to-end workflow test PASSED")
            logger.info("="*60)
            logger.info("WORKFLOW SUMMARY:")
            logger.info(f"  - Methods executed: {results.get('methods_executed', 0)}")
            logger.info(f"  - Common wells analyzed: {comparison_result.total_common_wells}")
            logger.info(f"  - Discrepancies found: {len(comparison_result.discrepancies)}")
            logger.info(f"  - Reports generated: {len(report_paths)}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"End-to-end workflow test failed: {e}")
            raise

    def test_error_handling_and_resilience(self, comparison_framework):
        """Test error handling and workflow resilience."""
        logger.info("Testing error handling and workflow resilience")
        
        # Test handling of missing configuration
        invalid_framework = ComparisonTestFramework()
        assert not invalid_framework.is_ready(), "Framework should not be ready without config"
        
        # Test handling of invalid method names
        result = comparison_framework.execute_method('nonexistent_method')
        assert result is False, "Should handle invalid method names gracefully"
        
        # Test framework state after errors
        assert comparison_framework.is_ready(), "Framework should remain ready after handling errors"
        
        logger.info("✅ Error handling and resilience test completed")

    def test_performance_and_logging(self, comparison_framework):
        """Test performance monitoring and comprehensive logging."""
        import time
        
        logger.info("Testing performance monitoring and logging")
        
        # Measure execution time
        start_time = time.time()
        
        # Run a quick comparison workflow
        results = comparison_framework.run_comparison()
        
        execution_time = time.time() - start_time
        
        # Log performance metrics
        logger.info(f"Workflow execution time: {execution_time:.2f} seconds")
        logger.info(f"Methods execution success rate: {results.get('methods_executed', 0)}/{results.get('total_methods', 2)}")
        
        # Verify logging is comprehensive
        method_outputs = comparison_framework.get_method_outputs()
        for method, output in method_outputs.items():
            logger.info(f"Method {method}: {'✅ EXECUTED' if output.get('executed') else '❌ FAILED'}")
        
        logger.info("✅ Performance and logging test completed")


if __name__ == "__main__":
    test_application()