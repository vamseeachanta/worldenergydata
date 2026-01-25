"""
Tests for Well Production Dashboard Export Manager

This module tests the export integration functionality for the well production dashboard,
including PDF, Excel, and JSON export capabilities with verification metadata.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path
import json
import tempfile
import os

from src.worldenergydata.modules.well_production_dashboard.export_manager import (
    WellDashboardExportManager,
    ExportConfiguration,
    ExportResult,
    VerificationMetadata
)


class TestExportConfiguration(unittest.TestCase):
    """Test suite for ExportConfiguration class"""
    
    def test_configuration_initialization(self):
        """Test export configuration initialization"""
        config = ExportConfiguration(
            formats=['pdf', 'excel'],
            include_verification=True,
            include_charts=True,
            include_raw_data=False
        )
        
        self.assertEqual(config.formats, ['pdf', 'excel'])
        self.assertTrue(config.include_verification)
        self.assertTrue(config.include_charts)
        self.assertFalse(config.include_raw_data)
    
    def test_configuration_defaults(self):
        """Test default configuration values"""
        config = ExportConfiguration()
        
        self.assertEqual(config.formats, ['excel'])
        self.assertTrue(config.include_verification)
        self.assertTrue(config.include_charts)
        self.assertTrue(config.include_raw_data)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        # Test invalid format
        with self.assertRaises(ValueError):
            ExportConfiguration(formats=['invalid_format'])
        
        # Test empty formats
        with self.assertRaises(ValueError):
            ExportConfiguration(formats=[])


class TestVerificationMetadata(unittest.TestCase):
    """Test suite for VerificationMetadata class"""
    
    def test_metadata_creation(self):
        """Test verification metadata creation"""
        metadata = VerificationMetadata(
            quality_score=0.95,
            verification_date=datetime.now(),
            audit_trail_id='AUDIT-001',
            anomalies_detected=2,
            data_completeness=0.98
        )
        
        self.assertEqual(metadata.quality_score, 0.95)
        self.assertIsNotNone(metadata.verification_date)
        self.assertEqual(metadata.audit_trail_id, 'AUDIT-001')
        self.assertEqual(metadata.anomalies_detected, 2)
        self.assertEqual(metadata.data_completeness, 0.98)
    
    def test_metadata_to_dict(self):
        """Test metadata conversion to dictionary"""
        metadata = VerificationMetadata(
            quality_score=0.92,
            verification_date=datetime(2025, 1, 13),
            audit_trail_id='AUDIT-002'
        )
        
        result = metadata.to_dict()
        
        self.assertIn('quality_score', result)
        self.assertIn('verification_date', result)
        self.assertIn('audit_trail_id', result)
        self.assertEqual(result['quality_score'], 0.92)


class TestWellDashboardExportManager(unittest.TestCase):
    """Test suite for WellDashboardExportManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.export_manager = WellDashboardExportManager()
        
        # Create sample dashboard data
        self.sample_data = {
            'well_data': pd.DataFrame({
                'well_name': ['Well-001', 'Well-002', 'Well-003'],
                'oil_production': [1000, 1500, 800],
                'gas_production': [5000, 7500, 4000],
                'water_production': [100, 150, 80],
                'operating_days': [30, 30, 28],
                'quality_score': [0.95, 0.88, 0.92]
            }),
            'economic_metrics': {
                'npv': 15000000,
                'irr': 0.25,
                'payback_period': 3.5,
                'total_revenue': 50000000,
                'total_cost': 35000000
            },
            'verification_metadata': VerificationMetadata(
                quality_score=0.91,
                verification_date=datetime.now(),
                audit_trail_id='AUDIT-2025-001',
                anomalies_detected=3,
                data_completeness=0.96
            ),
            'charts': {
                'production_trend': Mock(spec=['to_json', 'to_image']),
                'decline_curve': Mock(spec=['to_json', 'to_image']),
                'economic_summary': Mock(spec=['to_json', 'to_image'])
            }
        }
    
    def test_manager_initialization(self):
        """Test export manager initialization"""
        self.assertIsNotNone(self.export_manager.excel_exporter)
        self.assertIsNotNone(self.export_manager.pdf_exporter)
        self.assertIsNotNone(self.export_manager.batch_exporter)
        self.assertIsInstance(self.export_manager.config, dict)
    
    @patch('src.worldenergydata.modules.well_production_dashboard.export_manager.ExcelExporter')
    def test_export_to_excel(self, mock_excel_exporter):
        """Test Excel export functionality"""
        # Setup mock
        mock_exporter_instance = Mock()
        mock_excel_exporter.return_value = mock_exporter_instance
        mock_exporter_instance.export.return_value = Mock(
            success=True,
            file_path='export.xlsx',
            file_size=1024
        )
        
        # Create manager and export
        manager = WellDashboardExportManager()
        config = ExportConfiguration(formats=['excel'])
        
        result = manager.export_to_excel(
            self.sample_data,
            'test_export.xlsx',
            config
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.format, 'excel')
        self.assertIn('.xlsx', result.file_path)
    
    @patch('src.worldenergydata.modules.well_production_dashboard.export_manager.PDFExporter')
    def test_export_to_pdf(self, mock_pdf_exporter):
        """Test PDF export functionality"""
        # Setup mock
        mock_exporter_instance = Mock()
        mock_pdf_exporter.return_value = mock_exporter_instance
        mock_exporter_instance.export.return_value = Mock(
            success=True,
            file_path='export.pdf',
            file_size=2048
        )
        
        # Create manager and export
        manager = WellDashboardExportManager()
        config = ExportConfiguration(formats=['pdf'])
        
        result = manager.export_to_pdf(
            self.sample_data,
            'test_export.pdf',
            config
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.format, 'pdf')
        self.assertIn('.pdf', result.file_path)
    
    def test_export_to_json(self):
        """Test JSON export functionality"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            config = ExportConfiguration(formats=['json'])
            
            result = self.export_manager.export_to_json(
                self.sample_data,
                output_path,
                config
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.format, 'json')
            
            # Verify JSON content
            with open(output_path, 'r') as f:
                exported_data = json.load(f)
            
            self.assertIn('well_data', exported_data)
            self.assertIn('economic_metrics', exported_data)
            self.assertIn('verification_metadata', exported_data)
            
        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def test_prepare_export_data(self):
        """Test export data preparation"""
        config = ExportConfiguration(
            include_verification=True,
            include_charts=True,
            include_raw_data=True
        )
        
        prepared_data = self.export_manager.prepare_export_data(
            self.sample_data,
            config
        )
        
        self.assertIn('summary', prepared_data)
        self.assertIn('production_data', prepared_data)
        self.assertIn('economic_data', prepared_data)
        self.assertIn('verification_data', prepared_data)
        self.assertIn('charts', prepared_data)
        self.assertIn('raw_data', prepared_data)
    
    def test_prepare_export_data_without_verification(self):
        """Test export data preparation without verification"""
        config = ExportConfiguration(
            include_verification=False,
            include_charts=True,
            include_raw_data=False
        )
        
        prepared_data = self.export_manager.prepare_export_data(
            self.sample_data,
            config
        )
        
        self.assertNotIn('verification_data', prepared_data)
        self.assertNotIn('raw_data', prepared_data)
        self.assertIn('charts', prepared_data)
    
    @patch('src.worldenergydata.modules.well_production_dashboard.export_manager.BatchExporter')
    def test_batch_export(self, mock_batch_exporter):
        """Test batch export functionality"""
        # Setup mock
        mock_exporter_instance = Mock()
        mock_batch_exporter.return_value = mock_exporter_instance
        mock_exporter_instance.export_batch.return_value = [
            Mock(success=True, format='pdf', file_path='export.pdf'),
            Mock(success=True, format='excel', file_path='export.xlsx'),
            Mock(success=True, format='json', file_path='export.json')
        ]
        
        # Create manager and export
        manager = WellDashboardExportManager()
        config = ExportConfiguration(formats=['pdf', 'excel', 'json'])
        
        results = manager.export_batch(
            self.sample_data,
            'test_export',
            config
        )
        
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.success for r in results))
        self.assertEqual(set(r.format for r in results), {'pdf', 'excel', 'json'})
    
    def test_add_verification_report(self):
        """Test adding verification report to export data"""
        export_data = {}
        
        self.export_manager.add_verification_report(
            export_data,
            self.sample_data['verification_metadata']
        )
        
        self.assertIn('verification_report', export_data)
        report = export_data['verification_report']
        
        self.assertIn('quality_score', report)
        self.assertIn('verification_date', report)
        self.assertIn('audit_trail_id', report)
        self.assertIn('anomalies_detected', report)
        self.assertIn('data_completeness', report)
        self.assertIn('quality_assessment', report)
    
    def test_format_bsee_standard(self):
        """Test formatting data to BSEE 14-row standard"""
        formatted_data = self.export_manager.format_bsee_standard(
            self.sample_data['well_data']
        )
        
        # Check for required BSEE rows
        expected_rows = [
            'Field/Block/Lease',
            'Well Name',
            'Oil Production (BBL)',
            'Gas Production (MCF)',
            'Water Production (BBL)',
            'Operating Days',
            'Oil Sales (BBL)',
            'Gas Sales (MCF)',
            'Revenue ($)',
            'Operating Cost ($)',
            'Net Income ($)',
            'Cumulative Oil (BBL)',
            'Cumulative Gas (MCF)',
            'Quality Score'
        ]
        
        for row in expected_rows:
            self.assertIn(row, formatted_data)
    
    def test_export_with_field_aggregation(self):
        """Test export with field-level aggregation"""
        # Add field data to sample
        self.sample_data['field_data'] = pd.DataFrame({
            'field_name': ['Field-A', 'Field-B'],
            'total_wells': [10, 15],
            'active_wells': [8, 12],
            'total_oil': [10000, 15000],
            'total_gas': [50000, 75000]
        })
        
        config = ExportConfiguration(
            include_field_aggregation=True
        )
        
        prepared_data = self.export_manager.prepare_export_data(
            self.sample_data,
            config
        )
        
        self.assertIn('field_aggregation', prepared_data)
        self.assertEqual(len(prepared_data['field_aggregation']), 2)
    
    def test_export_error_handling(self):
        """Test error handling in export operations"""
        # Test with invalid data
        invalid_data = {'invalid': 'data'}
        config = ExportConfiguration()
        
        result = self.export_manager.export_to_excel(
            invalid_data,
            'test.xlsx',
            config
        )
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
    
    def test_export_with_charts(self):
        """Test export with chart integration"""
        config = ExportConfiguration(
            include_charts=True,
            chart_format='base64'
        )
        
        # Mock chart to_image method
        for chart in self.sample_data['charts'].values():
            chart.to_image.return_value = b'fake_image_data'
        
        prepared_data = self.export_manager.prepare_export_data(
            self.sample_data,
            config
        )
        
        self.assertIn('charts', prepared_data)
        self.assertEqual(len(prepared_data['charts']), 3)
    
    def test_verification_quality_assessment(self):
        """Test verification quality assessment logic"""
        # Test excellent quality
        metadata = VerificationMetadata(quality_score=0.95)
        assessment = self.export_manager.get_quality_assessment(metadata)
        self.assertEqual(assessment, 'Excellent')
        
        # Test good quality
        metadata = VerificationMetadata(quality_score=0.85)
        assessment = self.export_manager.get_quality_assessment(metadata)
        self.assertEqual(assessment, 'Good')
        
        # Test fair quality
        metadata = VerificationMetadata(quality_score=0.75)
        assessment = self.export_manager.get_quality_assessment(metadata)
        self.assertEqual(assessment, 'Fair')
        
        # Test poor quality
        metadata = VerificationMetadata(quality_score=0.65)
        assessment = self.export_manager.get_quality_assessment(metadata)
        self.assertEqual(assessment, 'Poor')


class TestExportIntegration(unittest.TestCase):
    """Integration tests for export functionality"""
    
    @patch('src.worldenergydata.modules.well_production_dashboard.well_production.WellProductionDashboard')
    def test_dashboard_export_integration(self, mock_dashboard):
        """Test integration between dashboard and export manager"""
        # Setup mock dashboard
        mock_dashboard_instance = Mock()
        mock_dashboard.return_value = mock_dashboard_instance
        mock_dashboard_instance.get_dashboard_data.return_value = {
            'well_data': pd.DataFrame({'well': ['W1'], 'oil': [1000]}),
            'verification_metadata': VerificationMetadata(quality_score=0.9)
        }
        
        # Create export manager
        export_manager = WellDashboardExportManager()
        
        # Get dashboard data and export
        dashboard_data = mock_dashboard_instance.get_dashboard_data()
        config = ExportConfiguration(formats=['excel', 'pdf'])
        
        results = export_manager.export_batch(
            dashboard_data,
            'dashboard_export',
            config
        )
        
        self.assertIsNotNone(results)
        mock_dashboard_instance.get_dashboard_data.assert_called_once()
    
    def test_cli_export_command(self):
        """Test CLI export command integration"""
        from src.worldenergydata.modules.well_production_dashboard.cli import DashboardCLI
        
        cli = DashboardCLI()
        
        # Test export command exists
        self.assertTrue(hasattr(cli, 'export'))
        
        # Test export command parameters
        export_params = cli.get_export_parameters()
        self.assertIn('format', export_params)
        self.assertIn('include_verification', export_params)
        self.assertIn('output_path', export_params)


if __name__ == '__main__':
    unittest.main()