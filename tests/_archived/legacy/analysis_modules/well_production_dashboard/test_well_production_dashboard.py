"""
Tests for WellProductionDashboard extension of DashboardBuilder.

Tests the integration with verification system and well-specific functionality.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Import the modules we're testing
from worldenergydata.modules.analysis.dashboard.well_production import (
    WellProductionDashboard,
    WellDashboardConfig,
    WellMetrics,
    FieldAggregator
)
from worldenergydata.modules.bsee.reports.comprehensive.visualizations.dashboard_builder import (
    DashboardBuilder,
    DashboardConfig,
    ChartConfig
)


class TestWellProductionDashboard:
    """Test suite for WellProductionDashboard class."""
    
    @pytest.fixture
    def sample_well_data(self):
        """Generate sample well production data."""
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='M')
        return pd.DataFrame({
            'date': dates,
            'well_id': 'TEST-001',
            'oil_production': np.random.uniform(1000, 5000, len(dates)),
            'gas_production': np.random.uniform(500, 2000, len(dates)),
            'water_production': np.random.uniform(100, 500, len(dates)),
            'operating_days': np.random.uniform(25, 31, len(dates)),
            'revenue': np.random.uniform(50000, 200000, len(dates)),
            'opex': np.random.uniform(10000, 50000, len(dates)),
            'verification_status': 'verified',
            'quality_score': np.random.uniform(0.8, 1.0, len(dates))
        })
    
    @pytest.fixture
    def dashboard_config(self):
        """Create dashboard configuration."""
        return WellDashboardConfig(
            title="Test Well Production Dashboard",
            enable_verification=True,
            enable_real_time=False,
            cache_ttl=300
        )
    
    @pytest.fixture
    def dashboard(self, dashboard_config):
        """Create WellProductionDashboard instance."""
        return WellProductionDashboard(config=dashboard_config)
    
    def test_dashboard_initialization(self, dashboard, dashboard_config):
        """Test dashboard initializes correctly."""
        assert dashboard is not None
        assert dashboard.config == dashboard_config
        assert isinstance(dashboard, DashboardBuilder)
        assert dashboard.verification_enabled == True
        assert dashboard.cache_ttl == 300
    
    def test_extends_dashboard_builder(self, dashboard):
        """Test that WellProductionDashboard extends DashboardBuilder."""
        # Check inheritance
        assert isinstance(dashboard, DashboardBuilder)
        
        # Check that base methods are available
        assert hasattr(dashboard, 'add_chart')
        assert hasattr(dashboard, 'add_filter')
        assert hasattr(dashboard, 'build')
        assert hasattr(dashboard, 'run')
    
    def test_load_well_data(self, dashboard, sample_well_data):
        """Test loading well production data."""
        dashboard.load_well_data(sample_well_data)
        
        assert dashboard.well_data is not None
        assert len(dashboard.well_data) == len(sample_well_data)
        assert 'well_id' in dashboard.well_data.columns
        assert 'verification_status' in dashboard.well_data.columns
    
    def test_verification_integration(self, dashboard, sample_well_data):
        """Test integration with verification system."""
        with patch('worldenergydata.modules.analysis.dashboard.well_production.VerificationWorkflow') as mock_workflow:
            mock_instance = Mock()
            mock_result = Mock()
            mock_result.is_valid = True
            mock_result.issues = []
            mock_instance.verify.return_value = mock_result
            mock_workflow.return_value = mock_instance
            
            with patch('worldenergydata.modules.analysis.dashboard.well_production.DataQualityFramework') as mock_quality:
                mock_quality_instance = Mock()
                mock_quality_instance.calculate_quality_score.return_value = 0.95
                mock_quality.return_value = mock_quality_instance
                
                result = dashboard.verify_well_data(sample_well_data)
                
                assert result is not None
                assert result['status'] == 'verified'
                assert result['quality_score'] == 0.95
                mock_instance.verify.assert_called_once()
    
    def test_create_production_chart(self, dashboard, sample_well_data):
        """Test creation of production charts."""
        dashboard.load_well_data(sample_well_data)
        chart = dashboard.create_production_chart('TEST-001')
        
        assert chart is not None
        assert chart.chart_type == 'production_timeline'
        assert chart.title == 'Production Timeline - TEST-001'
        assert chart.data_source == 'well_data'
    
    def test_create_economic_metrics(self, dashboard, sample_well_data):
        """Test creation of economic metrics display."""
        dashboard.load_well_data(sample_well_data)
        metrics = dashboard.create_economic_metrics('TEST-001')
        
        assert metrics is not None
        assert 'npv' in metrics
        assert 'total_revenue' in metrics
        assert 'total_opex' in metrics
        assert 'profit_margin' in metrics
    
    def test_quality_indicators(self, dashboard, sample_well_data):
        """Test quality indicators are properly displayed."""
        dashboard.load_well_data(sample_well_data)
        indicators = dashboard.get_quality_indicators('TEST-001')
        
        assert indicators is not None
        assert 'status' in indicators
        assert 'quality_score' in indicators
        assert 'indicator_color' in indicators
        assert indicators['indicator_color'] in ['green', 'yellow', 'red']
    
    def test_field_aggregation(self, dashboard):
        """Test field-level aggregation."""
        # Create sample data for multiple wells
        field_data = pd.DataFrame({
            'well_id': ['W1', 'W2', 'W3'] * 12,
            'date': pd.date_range('2023-01-01', periods=36, freq='M'),
            'oil_production': np.random.uniform(1000, 5000, 36),
            'gas_production': np.random.uniform(500, 2000, 36),
            'field': 'TestField'
        })
        
        aggregator = FieldAggregator()
        result = aggregator.aggregate_field_data(field_data, 'TestField')
        
        assert result is not None
        assert 'total_oil' in result.columns
        assert 'total_gas' in result.columns
        assert 'well_count' in result
    
    def test_decline_curve_analysis(self, dashboard, sample_well_data):
        """Test decline curve analysis component."""
        dashboard.load_well_data(sample_well_data)
        decline_analysis = dashboard.create_decline_curve('TEST-001')
        
        assert decline_analysis is not None
        assert 'decline_rate' in decline_analysis
        assert 'forecast' in decline_analysis
        assert 'confidence_interval' in decline_analysis
    
    def test_authentication_setup(self, dashboard):
        """Test authentication setup using BSEE patterns."""
        with patch('worldenergydata.modules.analysis.dashboard.well_production.BSEEAuthenticator') as mock_auth:
            mock_instance = Mock()
            mock_instance.is_authenticated.return_value = True
            mock_auth.return_value = mock_instance
            
            dashboard.setup_authentication()
            
            assert dashboard.authenticator is not None
            assert dashboard.is_authenticated() == True
    
    def test_cache_functionality(self, dashboard, sample_well_data):
        """Test caching functionality."""
        dashboard.load_well_data(sample_well_data)
        
        # First call should cache
        chart1 = dashboard.create_production_chart('TEST-001', use_cache=True)
        
        # Second call should use cache
        chart2 = dashboard.create_production_chart('TEST-001', use_cache=True)
        
        assert chart1 == chart2
        assert dashboard.cache_hits > 0
    
    def test_real_time_updates(self, dashboard):
        """Test real-time update capability."""
        dashboard.enable_real_time_updates(interval=5000)
        
        assert dashboard.real_time_enabled == True
        assert dashboard.update_interval == 5000
        assert dashboard.websocket_handler is not None
    
    def test_export_functionality(self, dashboard, sample_well_data):
        """Test export integration with comprehensive reports."""
        dashboard.load_well_data(sample_well_data)
        
        with patch('worldenergydata.modules.analysis.dashboard.well_production.ComprehensiveExporter') as mock_exporter:
            mock_instance = Mock()
            mock_instance.export_to_pdf.return_value = b'PDF_CONTENT'
            mock_instance.export_to_excel.return_value = b'EXCEL_CONTENT'
            mock_exporter.return_value = mock_instance
            
            pdf_result = dashboard.export_dashboard('pdf')
            excel_result = dashboard.export_dashboard('excel')
            
            assert pdf_result == b'PDF_CONTENT'
            assert excel_result == b'EXCEL_CONTENT'
            mock_instance.export_to_pdf.assert_called_once()
            mock_instance.export_to_excel.assert_called_once()
    
    def test_filter_functionality(self, dashboard, sample_well_data):
        """Test filtering capabilities."""
        dashboard.load_well_data(sample_well_data)
        
        # Add filters
        dashboard.add_filter('date_range', ['2023-01-01', '2023-06-30'])
        dashboard.add_filter('min_quality_score', 0.9)
        
        filtered_data = dashboard.apply_filters()
        
        assert len(filtered_data) < len(sample_well_data)
        assert all(filtered_data['quality_score'] >= 0.9)
    
    def test_api_endpoints(self, dashboard):
        """Test API endpoint configuration."""
        endpoints = dashboard.get_api_endpoints()
        
        assert '/api/wells' in endpoints
        assert '/api/wells/{well_id}' in endpoints
        assert '/api/dashboard/data' in endpoints
        assert '/api/dashboard/export' in endpoints
    
    def test_cli_interface(self):
        """Test CLI interface creation."""
        from worldenergydata.modules.analysis.dashboard.cli import DashboardCLI
        
        cli = DashboardCLI()
        
        assert cli is not None
        assert hasattr(cli, 'run')
        assert hasattr(cli, 'configure')
        assert hasattr(cli, 'export')
    
    def test_yaml_configuration(self, tmp_path):
        """Test YAML-based configuration."""
        config_path = tmp_path / "dashboard_config.yml"
        config_content = """
        dashboard:
          title: Production Dashboard
          enable_verification: true
          cache_ttl: 600
        wells:
          - id: W1
          - id: W2
        filters:
          date_range:
            start: 2023-01-01
            end: 2023-12-31
        """
        config_path.write_text(config_content)
        
        dashboard = WellProductionDashboard.from_yaml(str(config_path))
        
        assert dashboard.config.title == "Production Dashboard"
        assert dashboard.config.enable_verification == True
        assert dashboard.config.cache_ttl == 600
    
    def test_performance_metrics(self, dashboard, sample_well_data):
        """Test performance metrics tracking."""
        import time
        
        dashboard.load_well_data(sample_well_data)
        
        start_time = time.time()
        dashboard.create_production_chart('TEST-001')
        end_time = time.time()
        
        metrics = dashboard.get_performance_metrics()
        
        assert 'render_time' in metrics
        assert 'memory_usage' in metrics
        assert 'cache_hit_rate' in metrics
        assert metrics['render_time'] < 3.0  # Should render in less than 3 seconds
    
    def test_error_handling(self, dashboard):
        """Test error handling for invalid data."""
        invalid_data = pd.DataFrame({'invalid': [1, 2, 3]})
        
        with pytest.raises(ValueError) as exc_info:
            dashboard.load_well_data(invalid_data)
        
        assert "Missing required columns" in str(exc_info.value)
    
    def test_audit_trail_integration(self, dashboard, sample_well_data):
        """Test audit trail integration from verification system."""
        dashboard.load_well_data(sample_well_data)
        
        audit_trail = dashboard.get_audit_trail('TEST-001')
        
        assert audit_trail is not None
        assert 'timestamp' in audit_trail.columns
        assert 'action' in audit_trail.columns
        assert 'user' in audit_trail.columns
        assert 'details' in audit_trail.columns


class TestWellMetrics:
    """Test suite for WellMetrics calculator."""
    
    def test_npv_calculation(self):
        """Test NPV calculation."""
        cash_flows = [100000, 120000, 140000, 130000, 110000]
        discount_rate = 0.1
        
        metrics = WellMetrics()
        npv = metrics.calculate_npv(cash_flows, discount_rate)
        
        assert npv > 0
        assert isinstance(npv, float)
    
    def test_decline_rate_calculation(self):
        """Test decline rate calculation."""
        production = [5000, 4800, 4600, 4400, 4200, 4000]
        
        metrics = WellMetrics()
        decline_rate = metrics.calculate_decline_rate(production)
        
        assert decline_rate > 0
        assert decline_rate < 1
    
    def test_economic_indicators(self):
        """Test economic indicator calculations."""
        revenue = 1000000
        opex = 300000
        capex = 200000
        
        metrics = WellMetrics()
        indicators = metrics.calculate_economic_indicators(revenue, opex, capex)
        
        assert 'profit_margin' in indicators
        assert 'roi' in indicators
        assert 'payback_period' in indicators


class TestFieldAggregator:
    """Test suite for FieldAggregator."""
    
    def test_field_rollup(self):
        """Test field-level data rollup."""
        well_data = pd.DataFrame({
            'well_id': ['W1', 'W2', 'W3'] * 4,
            'date': pd.date_range('2023-01-01', periods=12, freq='M'),
            'oil_production': np.random.uniform(1000, 5000, 12),
            'field': 'TestField'
        })
        
        aggregator = FieldAggregator()
        result = aggregator.rollup_field_data(well_data, 'TestField')
        
        assert result is not None
        assert len(result) == 12  # Monthly aggregation
        assert 'total_production' in result.columns
    
    def test_comparative_analysis(self):
        """Test comparative analysis between fields."""
        field1_data = pd.DataFrame({
            'field': 'Field1',
            'total_production': [10000, 11000, 12000],
            'date': pd.date_range('2023-01-01', periods=3, freq='M')
        })
        
        field2_data = pd.DataFrame({
            'field': 'Field2',
            'total_production': [8000, 9000, 10000],
            'date': pd.date_range('2023-01-01', periods=3, freq='M')
        })
        
        aggregator = FieldAggregator()
        comparison = aggregator.compare_fields(field1_data, field2_data)
        
        assert comparison is not None
        assert 'performance_ratio' in comparison
        assert 'trend_comparison' in comparison