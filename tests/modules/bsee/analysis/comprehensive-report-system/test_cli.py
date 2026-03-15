"""
Tests for CLI interface
Validates argument parsing and command execution
"""

import argparse
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../../src"))

from worldenergydata.modules.bsee.reports.comprehensive.cli import ReportCLI


class TestCLI(unittest.TestCase):
    """Test suite for CLI functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.cli = ReportCLI()

    def test_parser_creation(self):
        """Test argument parser is created correctly"""
        parser = self.cli.parser
        self.assertIsInstance(parser, argparse.ArgumentParser)

        # Check key arguments exist
        actions = {action.dest for action in parser._actions}
        required_args = {
            "type",
            "id",
            "ids",
            "format",
            "output",
            "oil_price",
            "gas_price",
            "config",
            "verbose",
        }
        self.assertTrue(required_args.issubset(actions))

    def test_parse_single_entity_args(self):
        """Test parsing arguments for single entity report"""
        args = self.cli.parser.parse_args(
            [
                "--type",
                "block",
                "--id",
                "759",
                "--format",
                "excel",
                "--output",
                "./test_reports",
            ]
        )

        self.assertEqual(args.type, "block")
        self.assertEqual(args.id, "759")
        self.assertEqual(args.format, "excel")
        self.assertEqual(args.output, "./test_reports")

    def test_parse_multiple_entities_args(self):
        """Test parsing arguments for multiple entity reports"""
        args = self.cli.parser.parse_args(
            ["--type", "lease", "--ids", "OCS-G-12345,OCS-G-12346", "--batch"]
        )

        self.assertEqual(args.type, "lease")
        self.assertEqual(args.ids, "OCS-G-12345,OCS-G-12346")
        self.assertTrue(args.batch)

    def test_parse_price_deck_args(self):
        """Test parsing price deck arguments"""
        args = self.cli.parser.parse_args(
            [
                "--type",
                "field",
                "--id",
                "Jack",
                "--oil-price",
                "80.00",
                "--gas-price",
                "4.50",
                "--ngl-price",
                "35.00",
            ]
        )

        self.assertEqual(args.oil_price, 80.00)
        self.assertEqual(args.gas_price, 4.50)
        self.assertEqual(args.ngl_price, 35.00)

    def test_parse_cost_structure_args(self):
        """Test parsing cost structure arguments"""
        args = self.cli.parser.parse_args(
            [
                "--type",
                "well",
                "--id",
                "API001",
                "--operating-cost",
                "15.00",
                "--royalty-rate",
                "0.20",
                "--tax-rate",
                "0.06",
            ]
        )

        self.assertEqual(args.operating_cost, 15.00)
        self.assertEqual(args.royalty_rate, 0.20)
        self.assertEqual(args.tax_rate, 0.06)

    def test_parse_config_file_arg(self):
        """Test parsing configuration file argument"""
        args = self.cli.parser.parse_args(["--config", "report_config.yaml"])

        self.assertEqual(args.config, "report_config.yaml")

    def test_parse_processing_options(self):
        """Test parsing processing options"""
        args = self.cli.parser.parse_args(
            [
                "--type",
                "block",
                "--id",
                "525",
                "--parallel",
                "4",
                "--cache",
                "--progress",
                "--verbose",
            ]
        )

        self.assertEqual(args.parallel, 4)
        self.assertTrue(args.cache)
        self.assertTrue(args.progress)
        self.assertTrue(args.verbose)

    @patch("worldenergydata.modules.bsee.reports.comprehensive.cli.yaml.safe_load")
    def test_load_config(self, mock_yaml_load):
        """Test loading configuration from YAML file"""
        mock_config = {
            "type": "field",
            "id": "Jack",
            "oil_price": 80.00,
            "gas_price": 4.50,
        }
        mock_yaml_load.return_value = mock_config

        with patch("builtins.open", unittest.mock.mock_open()):
            config = self.cli.load_config("test_config.yaml")

        self.assertEqual(config, mock_config)
        mock_yaml_load.assert_called_once()

    def test_merge_args_with_config(self):
        """Test merging command-line args with config"""
        args = argparse.Namespace(
            type="block", id="759", oil_price=85.00, gas_price=None
        )

        config = {"type": "field", "id": "Jack", "oil_price": 75.00, "gas_price": 3.50}

        merged = self.cli.merge_args_with_config(args, config)

        # Args should override config
        self.assertEqual(merged["type"], "block")
        self.assertEqual(merged["id"], "759")
        self.assertEqual(merged["oil_price"], 85.00)
        # Config value should remain if arg is None
        self.assertEqual(merged["gas_price"], 3.50)

    @patch(
        "worldenergydata.modules.bsee.reports.comprehensive.cli.HierarchicalAggregator"
    )
    @patch("worldenergydata.modules.bsee.reports.comprehensive.cli.GoByReportBuilder")
    def test_initialize_components(self, mock_builder, mock_aggregator):
        """Test component initialization"""
        config = {
            "oil_price": 80.00,
            "gas_price": 4.00,
            "operating_cost": 13.00,
            "royalty_rate": 0.19,
            "tax_rate": 0.06,
        }

        self.cli.initialize_components(config)

        # Verify components were created
        self.assertIsNotNone(self.cli.aggregator)
        self.assertIsNotNone(self.cli.report_builder)
        mock_aggregator.assert_called_once()
        mock_builder.assert_called_once()

    def test_export_to_json(self):
        """Test JSON export functionality"""
        report = {
            "metadata": {"report_type": "block", "entity": "759"},
            "summary": {"total_wells": 10, "total_oil": 1000000},
        }

        with patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            with patch("pathlib.Path.mkdir"):
                output_path = Path("./test_output")
                result_path = self.cli.export_to_json(report, output_path, "759")

        self.assertTrue(str(result_path).endswith(".json"))
        mock_file.assert_called_once()

    def test_generate_html_report(self):
        """Test HTML report generation"""
        report = {
            "metadata": {
                "report_type": "field",
                "entity": "Jack",
                "generated_date": "2025-08-23",
                "generated_time": "10:00:00",
            },
            "summary": {
                "total_wells": 5,
                "total_oil_bbls": 500000,
                "gross_revenue": 37500000,
            },
        }

        html = self.cli._generate_html_report(report)

        # Check HTML contains key elements
        self.assertIn("<html>", html)
        self.assertIn("FIELD Report", html)
        self.assertIn("Jack", html)
        self.assertIn("Total Wells", html)
        self.assertIn("5", html)

    @patch(
        "worldenergydata.modules.bsee.reports.comprehensive.cli.ReportCLI.generate_single_report"
    )
    def test_run_single_report(self, mock_generate):
        """Test running CLI for single report generation"""
        mock_generate.return_value = Path("./reports/block_759.xlsx")

        with patch("sys.stdout", new_callable=unittest.mock.StringIO) as mock_stdout:
            exit_code = self.cli.run(
                ["--type", "block", "--id", "759", "--format", "excel"]
            )

        self.assertEqual(exit_code, 0)
        mock_generate.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Report generated successfully", output)

    @patch(
        "worldenergydata.modules.bsee.reports.comprehensive.cli.ReportCLI.generate_batch_reports"
    )
    def test_run_batch_reports(self, mock_generate_batch):
        """Test running CLI for batch report generation"""
        mock_generate_batch.return_value = [
            Path("./reports/lease_1.xlsx"),
            Path("./reports/lease_2.xlsx"),
        ]

        with patch("sys.stdout", new_callable=unittest.mock.StringIO) as mock_stdout:
            exit_code = self.cli.run(
                ["--type", "lease", "--ids", "OCS-G-12345,OCS-G-12346", "--batch"]
            )

        self.assertEqual(exit_code, 0)
        mock_generate_batch.assert_called_once()
        output = mock_stdout.getvalue()
        self.assertIn("Generated 2 reports", output)

    def test_run_missing_entity(self):
        """Test CLI error handling for missing entity"""
        with patch("sys.stderr", new_callable=unittest.mock.StringIO):
            with self.assertRaises(SystemExit):
                self.cli.run(["--type", "block"])

    def test_all_output_formats(self):
        """Test all supported output formats"""
        formats = ["excel", "pdf", "html", "json", "all"]

        for fmt in formats:
            args = self.cli.parser.parse_args(
                ["--type", "block", "--id", "759", "--format", fmt]
            )
            self.assertEqual(args.format, fmt)


if __name__ == "__main__":
    unittest.main()
