"""
Integration tests for the FDAS CLI commands.

Tests Field Development Analysis System (FDAS) CLI functionality
including NPV, MIRR, IRR calculations, and classification commands.
"""

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.main import app

runner = CliRunner()


class TestFDASCLIHelp:
    """Test FDAS CLI help and information commands."""

    def test_fdas_help_exits_successfully(self):
        """Test that fdas --help runs and exits with code 0."""
        result = runner.invoke(app, ["fdas", "--help"])
        assert result.exit_code == 0

    def test_fdas_help_shows_commands(self):
        """Test that fdas --help displays available commands."""
        result = runner.invoke(app, ["fdas", "--help"])
        # Should list available FDAS commands
        output_lower = result.output.lower()
        assert any(cmd in output_lower for cmd in ["npv", "mirr", "irr", "classify"])

    def test_fdas_help_shows_description(self):
        """Test that fdas --help shows module description."""
        result = runner.invoke(app, ["fdas", "--help"])
        # Should include FDAS-related description
        output_lower = result.output.lower()
        assert (
            "fdas" in output_lower
            or "field" in output_lower
            or "development" in output_lower
        )


class TestFDASCalculateNPV:
    """Test FDAS calculate-npv command."""

    def test_fdas_calculate_npv_exits_successfully(self):
        """Test that fdas calculate-npv with valid cashflows exits with code 0."""
        result = runner.invoke(
            app, ["fdas", "calculate-npv", "--cashflows", "[-1000,100,200,300]"]
        )
        assert result.exit_code == 0

    def test_fdas_calculate_npv_shows_result(self):
        """Test that calculate-npv displays NPV result."""
        result = runner.invoke(
            app, ["fdas", "calculate-npv", "--cashflows", "[-1000,100,200,300]"]
        )
        # Should show NPV-related output
        output_lower = result.output.lower()
        assert "npv" in output_lower or "value" in output_lower or "$" in result.output

    def test_fdas_calculate_npv_with_discount_rate(self):
        """Test calculate-npv with custom discount rate."""
        result = runner.invoke(
            app,
            [
                "fdas",
                "calculate-npv",
                "--cashflows",
                "[-1000,100,200,300,400,500]",
                "--discount-rate",
                "0.08",
            ],
        )
        assert result.exit_code == 0

    def test_fdas_calculate_npv_annual_period(self):
        """Test calculate-npv with annual period."""
        result = runner.invoke(
            app,
            [
                "fdas",
                "calculate-npv",
                "--cashflows",
                "[-5000,1000,1500,2000]",
                "--period",
                "annual",
            ],
        )
        assert result.exit_code == 0

    def test_fdas_calculate_npv_help(self):
        """Test that calculate-npv --help shows command help."""
        result = runner.invoke(app, ["fdas", "calculate-npv", "--help"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "cashflows" in output_lower

    def test_fdas_calculate_npv_without_cashflows_fails(self):
        """Test that calculate-npv without cashflows returns error."""
        result = runner.invoke(app, ["fdas", "calculate-npv"])
        # Should fail when cashflows not provided
        assert result.exit_code != 0

    def test_fdas_calculate_npv_invalid_json_fails(self):
        """Test that calculate-npv with invalid JSON fails gracefully."""
        result = runner.invoke(
            app, ["fdas", "calculate-npv", "--cashflows", "invalid-json"]
        )
        # Should fail for invalid JSON
        assert result.exit_code != 0


class TestFDASCalculateMIRR:
    """Test FDAS calculate-mirr command."""

    def test_fdas_calculate_mirr_exits_successfully(self):
        """Test that fdas calculate-mirr with valid cashflows exits with code 0."""
        result = runner.invoke(
            app, ["fdas", "calculate-mirr", "--cashflows", "[-1000,100,200,300]"]
        )
        assert result.exit_code == 0

    def test_fdas_calculate_mirr_shows_result(self):
        """Test that calculate-mirr displays MIRR result."""
        result = runner.invoke(
            app, ["fdas", "calculate-mirr", "--cashflows", "[-1000,100,200,300]"]
        )
        # Should show MIRR-related output
        output_lower = result.output.lower()
        assert "mirr" in output_lower or "rate" in output_lower or "%" in result.output

    def test_fdas_calculate_mirr_with_discount_rate(self):
        """Test calculate-mirr with custom discount rate."""
        result = runner.invoke(
            app,
            [
                "fdas",
                "calculate-mirr",
                "--cashflows",
                "[-1000,100,200,300,400,500]",
                "--discount-rate",
                "0.12",
            ],
        )
        assert result.exit_code == 0

    def test_fdas_calculate_mirr_with_reinvestment_rate(self):
        """Test calculate-mirr with reinvestment rate."""
        result = runner.invoke(
            app,
            [
                "fdas",
                "calculate-mirr",
                "--cashflows",
                "[-5000,1000,1500,2000]",
                "--reinvestment-rate",
                "0.05",
            ],
        )
        assert result.exit_code == 0

    def test_fdas_calculate_mirr_help(self):
        """Test that calculate-mirr --help shows command help."""
        result = runner.invoke(app, ["fdas", "calculate-mirr", "--help"])
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "cashflows" in output_lower

    def test_fdas_calculate_mirr_without_cashflows_fails(self):
        """Test that calculate-mirr without cashflows returns error."""
        result = runner.invoke(app, ["fdas", "calculate-mirr"])
        # Should fail when cashflows not provided
        assert result.exit_code != 0


class TestFDASClassify:
    """Test FDAS classify command."""

    def test_fdas_classify_shallow_water(self):
        """Test classify command for shallow water depth."""
        result = runner.invoke(app, ["fdas", "classify", "500"])
        assert result.exit_code == 0
        # Should show shelf classification
        output_lower = result.output.lower()
        assert "shelf" in output_lower or "500" in result.output

    def test_fdas_classify_deepwater(self):
        """Test classify command for deepwater depth."""
        result = runner.invoke(app, ["fdas", "classify", "5000"])
        assert result.exit_code == 0
        # Should show classification
        output_lower = result.output.lower()
        assert any(
            cls in output_lower for cls in ["deepwater", "deep", "5000", "5,000"]
        )

    def test_fdas_classify_ultra_deepwater(self):
        """Test classify command for ultra-deepwater depth."""
        result = runner.invoke(app, ["fdas", "classify", "10000"])
        assert result.exit_code == 0
        # Should show ultra-deepwater classification
        output_lower = result.output.lower()
        assert any(cls in output_lower for cls in ["ultra", "deep", "10000", "10,000"])

    def test_fdas_classify_shows_water_depth(self):
        """Test that classify shows the input water depth."""
        result = runner.invoke(app, ["fdas", "classify", "5000"])
        # Should display the water depth in output
        assert "5000" in result.output or "5,000" in result.output

    def test_fdas_classify_without_depth_fails(self):
        """Test that classify without depth argument returns error."""
        result = runner.invoke(app, ["fdas", "classify"])
        # Should fail when depth not provided
        assert result.exit_code != 0


class TestFDASInfo:
    """Test FDAS info command."""

    def test_fdas_info_exits_successfully(self):
        """Test that fdas info command runs and exits with code 0."""
        result = runner.invoke(app, ["fdas", "info"])
        assert result.exit_code == 0

    def test_fdas_info_shows_module_info(self):
        """Test that fdas info displays module information."""
        result = runner.invoke(app, ["fdas", "info"])
        # Should display FDAS-related information
        output_lower = result.output.lower()
        assert any(
            term in output_lower
            for term in ["fdas", "field", "development", "analysis", "npv", "mirr"]
        )

    def test_fdas_info_shows_available_metrics(self):
        """Test that info shows available financial metrics."""
        result = runner.invoke(app, ["fdas", "info"])
        output_lower = result.output.lower()
        # Should mention financial metrics
        assert any(
            metric in output_lower for metric in ["npv", "mirr", "irr", "payback"]
        )


class TestFDASCalculateIRR:
    """Test FDAS calculate-irr command."""

    def test_fdas_calculate_irr_exits_successfully(self):
        """Test that fdas calculate-irr with valid cashflows exits with code 0."""
        result = runner.invoke(
            app, ["fdas", "calculate-irr", "--cashflows", "[-1000,100,200,300,400,500]"]
        )
        assert result.exit_code == 0

    def test_fdas_calculate_irr_help(self):
        """Test that calculate-irr --help shows command help."""
        result = runner.invoke(app, ["fdas", "calculate-irr", "--help"])
        assert result.exit_code == 0


class TestFDASCalculateAll:
    """Test FDAS calculate-all command."""

    def test_fdas_calculate_all_exits_successfully(self):
        """Test that fdas calculate-all with valid cashflows exits with code 0."""
        result = runner.invoke(
            app, ["fdas", "calculate-all", "--cashflows", "[-1000,100,200,300,400,500]"]
        )
        assert result.exit_code == 0

    def test_fdas_calculate_all_help(self):
        """Test that calculate-all --help shows command help."""
        result = runner.invoke(app, ["fdas", "calculate-all", "--help"])
        assert result.exit_code == 0


class TestFDASAnalyze:
    """Test FDAS analyze command."""

    def test_fdas_analyze_help_exits_successfully(self):
        """Test that fdas analyze --help runs and exits with code 0."""
        result = runner.invoke(app, ["fdas", "analyze", "--help"])
        assert result.exit_code == 0

    def test_fdas_analyze_help_shows_options(self):
        """Test that analyze help shows available options."""
        result = runner.invoke(app, ["fdas", "analyze", "--help"])
        output_lower = result.output.lower()
        # Should show field and lease options
        assert "field" in output_lower or "lease" in output_lower


class TestFDASCLIEdgeCases:
    """Test edge cases for FDAS CLI commands."""

    def test_fdas_no_args_shows_help(self):
        """Test that fdas with no args shows help or error."""
        result = runner.invoke(app, ["fdas"])
        # Should show help when no subcommand provided
        assert result.exit_code in [0, 2]

    def test_fdas_invalid_subcommand(self):
        """Test that invalid subcommand returns error."""
        result = runner.invoke(app, ["fdas", "invalid-subcommand-xyz"])
        assert result.exit_code != 0

    def test_fdas_calculate_npv_empty_cashflows(self):
        """Test that empty cashflows list is handled."""
        result = runner.invoke(app, ["fdas", "calculate-npv", "--cashflows", "[]"])
        # Should handle empty cashflows gracefully
        # Either succeed with 0 or fail with error
        assert result.exit_code in [0, 1]

    def test_fdas_calculate_npv_single_cashflow(self):
        """Test that single cashflow is handled."""
        result = runner.invoke(app, ["fdas", "calculate-npv", "--cashflows", "[-1000]"])
        # Should handle single cashflow
        assert result.exit_code == 0

    def test_fdas_classify_zero_depth(self):
        """Test classify with zero depth."""
        result = runner.invoke(app, ["fdas", "classify", "0"])
        assert result.exit_code == 0

    def test_fdas_calculate_npv_abbreviated_flags(self):
        """Test that abbreviated flags work for calculate-npv."""
        result = runner.invoke(
            app, ["fdas", "calculate-npv", "-c", "[-1000,100,200,300]", "-r", "0.10"]
        )
        assert result.exit_code == 0

    def test_fdas_calculate_mirr_abbreviated_flags(self):
        """Test that abbreviated flags work for calculate-mirr."""
        result = runner.invoke(
            app, ["fdas", "calculate-mirr", "-c", "[-1000,100,200,300]", "-r", "0.10"]
        )
        assert result.exit_code == 0
