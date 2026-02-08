"""
Tests for the Report Exporter system in the Comprehensive Report System.
"""
import unittest
from unittest.mock import MagicMock, patch, mock_open
from datetime import datetime
from decimal import Decimal
import tempfile
import os
from pathlib import Path
from abc import ABC, abstractmethod

from worldenergydata.bsee.reports.comprehensive.exporters.base import (
    ReportExporter,
    ExportFormat,
    ExportConfig,
    ExportResult
)


class TestReportExporterBase(unittest.TestCase):
    """Tests for ReportExporter abstract base class."""
    
    def test_export_format_enum(self):
        """Test ExportFormat enum values."""
        self.assertEqual(ExportFormat.EXCEL.value, "excel")
        self.assertEqual(ExportFormat.PDF.value, "pdf")
        self.assertEqual(ExportFormat.HTML.value, "html")
        self.assertEqual(ExportFormat.JSON.value, "json")
        self.assertEqual(ExportFormat.POWERPOINT.value, "powerpoint")
    
    def test_export_config_creation(self):
        """Test ExportConfig dataclass creation."""
        config = ExportConfig(
            format=ExportFormat.EXCEL,
            output_path=Path("/tmp/report.xlsx"),
            template_name="executive",
            include_charts=True,
            include_raw_data=False,
            compression=True
        )
        
        self.assertEqual(config.format, ExportFormat.EXCEL)
        self.assertEqual(config.output_path, Path("/tmp/report.xlsx"))
        self.assertEqual(config.template_name, "executive")
        self.assertTrue(config.include_charts)
        self.assertFalse(config.include_raw_data)
        self.assertTrue(config.compression)
    
    def test_export_result_creation(self):
        """Test ExportResult dataclass creation."""
        result = ExportResult(
            success=True,
            file_path=Path("/tmp/report.xlsx"),
            file_size=1024000,
            export_time=2.5,
            message="Export completed successfully",
            warnings=["Large dataset may affect performance"]
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.file_path, Path("/tmp/report.xlsx"))
        self.assertEqual(result.file_size, 1024000)
        self.assertEqual(result.export_time, 2.5)
        self.assertEqual(result.message, "Export completed successfully")
        self.assertEqual(len(result.warnings), 1)
    
    def test_report_exporter_abstract_methods(self):
        """Test that ReportExporter is abstract and has required methods."""
        # Cannot instantiate abstract class
        with self.assertRaises(TypeError):
            ReportExporter()
        
        # Check required abstract methods exist
        self.assertTrue(hasattr(ReportExporter, 'export'))
        self.assertTrue(hasattr(ReportExporter, 'validate_data'))
        self.assertTrue(hasattr(ReportExporter, 'get_supported_features'))
    
    def test_concrete_exporter_implementation(self):
        """Test concrete implementation of ReportExporter."""
        class TestExporter(ReportExporter):
            def export(self, data, config):
                return ExportResult(
                    success=True,
                    file_path=config.output_path,
                    file_size=1000,
                    export_time=1.0
                )
            
            def validate_data(self, data):
                return True
            
            def get_supported_features(self):
                return ['charts', 'tables', 'formatting']
        
        exporter = TestExporter()
        config = ExportConfig(
            format=ExportFormat.EXCEL,
            output_path=Path("/tmp/test.xlsx")
        )
        
        result = exporter.export({}, config)
        self.assertTrue(result.success)
        self.assertTrue(exporter.validate_data({}))
        self.assertIn('charts', exporter.get_supported_features())
    
    def test_base_exporter_validation(self):
        """Test base validation methods."""
        class TestExporter(ReportExporter):
            def export(self, data, config):
                if not self.validate_data(data):
                    return ExportResult(
                        success=False,
                        file_path=None,
                        file_size=0,
                        export_time=0,
                        message="Invalid data"
                    )
                return ExportResult(success=True, file_path=config.output_path)
            
            def validate_data(self, data):
                return 'report_data' in data
            
            def get_supported_features(self):
                return []
        
        exporter = TestExporter()
        config = ExportConfig(format=ExportFormat.EXCEL, output_path=Path("/tmp/test.xlsx"))
        
        # Test with invalid data
        result = exporter.export({}, config)
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Invalid data")
        
        # Test with valid data
        result = exporter.export({'report_data': {}}, config)
        self.assertTrue(result.success)
    
    def test_export_config_defaults(self):
        """Test ExportConfig default values."""
        config = ExportConfig(
            format=ExportFormat.PDF,
            output_path=Path("/tmp/report.pdf")
        )
        
        # Check defaults
        self.assertIsNone(config.template_name)
        self.assertTrue(config.include_charts)  # Should default to True
        self.assertFalse(config.include_raw_data)  # Should default to False
        self.assertFalse(config.compression)  # Should default to False
    
    def test_export_result_with_errors(self):
        """Test ExportResult with error conditions."""
        result = ExportResult(
            success=False,
            file_path=None,
            file_size=0,
            export_time=0,
            message="Export failed: Invalid template",
            errors=["Template not found", "Missing required data"],
            warnings=[]
        )
        
        self.assertFalse(result.success)
        self.assertIsNone(result.file_path)
        self.assertEqual(result.file_size, 0)
        self.assertIn("Export failed", result.message)
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(len(result.warnings), 0)


class TestExcelExporter(unittest.TestCase):
    """Tests for ExcelExporter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter import ExcelExporter
        self.exporter = ExcelExporter()
        self.sample_data = self._create_sample_data()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_data(self):
        """Create sample report data for testing."""
        return {
            'report_metadata': {
                'title': 'Test Report',
                'date': datetime(2024, 1, 1),
                'organization': 'Block 525',
                'report_type': 'executive'
            },
            'summary': {
                'total_production': 1500000,
                'revenue': Decimal('125000000'),
                'well_count': 25
            },
            'production_data': [
                {'well': 'W001', 'oil': 50000, 'gas': 25000},
                {'well': 'W002', 'oil': 45000, 'gas': 22000}
            ],
            'charts': {
                'production_trend': MagicMock(),
                'revenue_chart': MagicMock()
            }
        }
    
    @patch('worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter.Workbook')
    def test_excel_export_basic(self, mock_workbook):
        """Test basic Excel export functionality."""
        mock_wb = MagicMock()
        mock_workbook.return_value = mock_wb
        
        output_path = Path(self.temp_dir) / "test_report.xlsx"
        config = ExportConfig(
            format=ExportFormat.EXCEL,
            output_path=output_path
        )
        
        result = self.exporter.export(self.sample_data, config)
        
        self.assertTrue(result.success)
        self.assertEqual(result.file_path, output_path)
        mock_wb.save.assert_called_once()
    
    def test_excel_sheet_creation(self):
        """Test Excel sheet creation for different data sections."""
        sheets_created = self.exporter.create_sheets(self.sample_data)
        
        expected_sheets = ['Summary', 'Production Data', 'Charts']
        for sheet in expected_sheets:
            self.assertIn(sheet, sheets_created)
    
    def test_excel_formatting(self):
        """Test Excel cell formatting."""
        formats = self.exporter.get_cell_formats()
        
        self.assertIn('header', formats)
        self.assertIn('currency', formats)
        self.assertIn('percentage', formats)
        self.assertIn('number', formats)
        self.assertIn('date', formats)
    
    def test_excel_chart_embedding(self):
        """Test embedding charts in Excel."""
        with patch('worldenergydata.bsee.reports.comprehensive.exporters.excel_exporter.Image') as mock_image:
            chart_embedded = self.exporter.embed_chart(
                worksheet=MagicMock(),
                chart_data=MagicMock(),
                position='A1'
            )
            
            self.assertTrue(chart_embedded)
            mock_image.assert_called()
    
    def test_excel_data_validation(self):
        """Test Excel data validation."""
        # Test with valid data
        self.assertTrue(self.exporter.validate_data(self.sample_data))
        
        # Test with invalid data
        self.assertFalse(self.exporter.validate_data({}))
        self.assertFalse(self.exporter.validate_data({'invalid': 'data'}))
    
    def test_excel_large_dataset_handling(self):
        """Test handling of large datasets."""
        large_data = self.sample_data.copy()
        large_data['production_data'] = [
            {'well': f'W{i:03d}', 'oil': 50000, 'gas': 25000}
            for i in range(10000)
        ]
        
        output_path = Path(self.temp_dir) / "large_report.xlsx"
        config = ExportConfig(
            format=ExportFormat.EXCEL,
            output_path=output_path,
            compression=True
        )
        
        result = self.exporter.export(large_data, config)
        
        self.assertTrue(result.success)
        if result.warnings:
            self.assertIn('large', result.warnings[0].lower())


class TestPDFExporter(unittest.TestCase):
    """Tests for PDFExporter functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.bsee.reports.comprehensive.exporters.pdf_exporter import PDFExporter
        self.exporter = PDFExporter()
        self.sample_data = self._create_sample_data()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def _create_sample_data(self):
        """Create sample report data for testing."""
        return {
            'report_metadata': {
                'title': 'Executive Report',
                'date': datetime(2024, 1, 1),
                'organization': 'Field Alpha'
            },
            'content': {
                'executive_summary': 'This is an executive summary.',
                'key_findings': ['Finding 1', 'Finding 2'],
                'recommendations': ['Recommendation 1', 'Recommendation 2']
            },
            'tables': {
                'production_table': [
                    ['Well', 'Oil (BBL)', 'Gas (MCF)'],
                    ['W001', '50,000', '25,000'],
                    ['W002', '45,000', '22,000']
                ]
            },
            'charts': {
                'trend_chart': MagicMock()
            }
        }
    
    @patch('worldenergydata.bsee.reports.comprehensive.exporters.pdf_exporter.HTML')
    @patch('worldenergydata.bsee.reports.comprehensive.exporters.pdf_exporter.CSS')
    def test_pdf_export_basic(self, mock_css, mock_html):
        """Test basic PDF export functionality."""
        mock_html_instance = MagicMock()
        mock_html.return_value = mock_html_instance
        
        output_path = Path(self.temp_dir) / "test_report.pdf"
        config = ExportConfig(
            format=ExportFormat.PDF,
            output_path=output_path
        )
        
        result = self.exporter.export(self.sample_data, config)
        
        self.assertTrue(result.success)
        self.assertEqual(result.file_path, output_path)
        mock_html_instance.write_pdf.assert_called_once()
    
    def test_pdf_html_generation(self):
        """Test HTML generation for PDF."""
        html_content = self.exporter.generate_html(self.sample_data)
        
        self.assertIn('<html>', html_content)
        self.assertIn('Executive Report', html_content)
        self.assertIn('executive summary', html_content.lower())
    
    def test_pdf_css_styling(self):
        """Test CSS styling for PDF."""
        css_content = self.exporter.get_pdf_styles()
        
        self.assertIn('page', css_content)
        self.assertIn('margin', css_content)
        self.assertIn('font-family', css_content)
        self.assertIn('header', css_content)
    
    def test_pdf_page_layout(self):
        """Test PDF page layout configuration."""
        layout = self.exporter.get_page_layout()
        
        self.assertIn('size', layout)
        self.assertIn('margin', layout)
        self.assertIn('orientation', layout)
        self.assertEqual(layout['size'], 'A4')
    
    def test_pdf_table_rendering(self):
        """Test rendering tables in PDF."""
        table_html = self.exporter.render_table(
            self.sample_data['tables']['production_table']
        )
        
        self.assertIn('<table', table_html)
        self.assertIn('<tr>', table_html)
        self.assertIn('W001', table_html)
        self.assertIn('50,000', table_html)
    
    def test_pdf_chart_embedding(self):
        """Test embedding charts in PDF."""
        with patch.object(self.exporter, 'chart_to_base64') as mock_chart:
            mock_chart.return_value = "base64_image_data"
            
            chart_html = self.exporter.embed_chart_as_image(
                self.sample_data['charts']['trend_chart']
            )
            
            self.assertIn('<img', chart_html)
            self.assertIn('base64', chart_html)
    
    def test_pdf_header_footer(self):
        """Test PDF header and footer generation."""
        header = self.exporter.generate_header(self.sample_data['report_metadata'])
        footer = self.exporter.generate_footer(page_number=1, total_pages=10)
        
        self.assertIn('Executive Report', header)
        self.assertIn('Page 1 of 10', footer)
    
    def test_pdf_data_validation(self):
        """Test PDF data validation."""
        # Valid data
        self.assertTrue(self.exporter.validate_data(self.sample_data))
        
        # Invalid data
        self.assertFalse(self.exporter.validate_data({}))
        self.assertFalse(self.exporter.validate_data({'no_metadata': True}))


class TestBatchExporter(unittest.TestCase):
    """Tests for batch export functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        from worldenergydata.bsee.reports.comprehensive.exporters.batch import BatchExporter
        self.batch_exporter = BatchExporter()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_batch_export_multiple_formats(self):
        """Test exporting to multiple formats in batch."""
        report_data = {
            'report_metadata': {'title': 'Batch Test'},
            'content': {'summary': 'Test summary'}
        }
        
        configs = [
            ExportConfig(
                format=ExportFormat.EXCEL,
                output_path=Path(self.temp_dir) / "report.xlsx"
            ),
            ExportConfig(
                format=ExportFormat.PDF,
                output_path=Path(self.temp_dir) / "report.pdf"
            )
        ]
        
        results = self.batch_exporter.export_batch(report_data, configs)
        
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.success for r in results))
    
    def test_batch_export_error_handling(self):
        """Test error handling in batch export."""
        report_data = {'invalid': 'data'}
        
        configs = [
            ExportConfig(
                format=ExportFormat.EXCEL,
                output_path=Path(self.temp_dir) / "report.xlsx"
            )
        ]
        
        results = self.batch_exporter.export_batch(report_data, configs)
        
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
    
    def test_batch_export_parallel_processing(self):
        """Test parallel processing for batch exports."""
        with patch.object(self.batch_exporter, 'use_parallel', True):
            report_data = {'report_metadata': {'title': 'Test'}}
            
            configs = [
                ExportConfig(format=ExportFormat.EXCEL, output_path=Path(f"report_{i}.xlsx"))
                for i in range(5)
            ]
            
            results = self.batch_exporter.export_batch(report_data, configs)
            
            self.assertEqual(len(results), 5)


if __name__ == '__main__':
    unittest.main()