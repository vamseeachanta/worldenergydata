"""
Integration tests for the BSEE CLI commands.

Tests BSEE (Bureau of Safety and Environmental Enforcement) CLI functionality
including data operations, analysis, reporting, and statistics commands.
"""

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.main import app

runner = CliRunner()


class TestBSEECLIHelp:
    """Test BSEE CLI help and information commands."""

    def test_bsee_help_exits_successfully(self):
        """Test that bsee --help runs and exits with code 0."""
        result = runner.invoke(app, ["bsee", "--help"])
        assert result.exit_code == 0

    def test_bsee_help_shows_commands(self):
        """Test that bsee --help displays available commands."""
        result = runner.invoke(app, ["bsee", "--help"])
        # Should list available BSEE commands
        output_lower = result.output.lower()
        assert (
            "analyze" in output_lower
            or "report" in output_lower
            or "stats" in output_lower
        )

    def test_bsee_help_shows_description(self):
        """Test that bsee --help shows module description."""
        result = runner.invoke(app, ["bsee", "--help"])
        # Should include BSEE-related description
        assert "bsee" in result.output.lower()


class TestBSEEStats:
    """Test BSEE stats command."""

    def test_bsee_stats_exits_successfully(self):
        """Test that bsee stats command runs and exits with code 0."""
        result = runner.invoke(app, ["bsee", "stats"])
        assert result.exit_code == 0

    def test_bsee_stats_shows_statistics(self):
        """Test that bsee stats displays statistics information."""
        result = runner.invoke(app, ["bsee", "stats"])
        # Should show some statistics-related output
        assert (
            "Statistics" in result.output
            or "Data" in result.output
            or "Module" in result.output
        )

    def test_bsee_stats_verbose_flag(self):
        """Test that bsee stats accepts --verbose flag."""
        result = runner.invoke(app, ["bsee", "stats", "--verbose"])
        assert result.exit_code == 0

    def test_bsee_stats_help(self):
        """Test that bsee stats --help shows command help."""
        result = runner.invoke(app, ["bsee", "stats", "--help"])
        assert result.exit_code == 0
        assert "stats" in result.output.lower() or "statistics" in result.output.lower()


class TestBSEEAnalyze:
    """Test BSEE analyze command."""

    def test_bsee_analyze_help_exits_successfully(self):
        """Test that bsee analyze --help runs and exits with code 0."""
        result = runner.invoke(app, ["bsee", "analyze", "--help"])
        assert result.exit_code == 0

    def test_bsee_analyze_help_shows_options(self):
        """Test that bsee analyze --help displays available options."""
        result = runner.invoke(app, ["bsee", "analyze", "--help"])
        # Should list analysis options
        output_lower = result.output.lower()
        assert (
            "block" in output_lower or "field" in output_lower or "api" in output_lower
        )

    def test_bsee_analyze_requires_parameter(self):
        """Test that bsee analyze requires at least one parameter."""
        result = runner.invoke(app, ["bsee", "analyze"])
        # Should exit with error when no parameters provided
        assert (
            result.exit_code != 0
            or "error" in result.output.lower()
            or "required" in result.output.lower()
        )


class TestBSEEReport:
    """Test BSEE report command."""

    def test_bsee_report_help_exits_successfully(self):
        """Test that bsee report --help runs and exits with code 0."""
        result = runner.invoke(app, ["bsee", "report", "--help"])
        assert result.exit_code == 0

    def test_bsee_report_help_shows_options(self):
        """Test that bsee report --help displays available options."""
        result = runner.invoke(app, ["bsee", "report", "--help"])
        # Should list report options
        output_lower = result.output.lower()
        assert (
            "type" in output_lower or "format" in output_lower or "id" in output_lower
        )

    def test_bsee_report_shows_format_options(self):
        """Test that bsee report --help shows output format options."""
        result = runner.invoke(app, ["bsee", "report", "--help"])
        output_lower = result.output.lower()
        # Should mention at least one format option
        assert any(fmt in output_lower for fmt in ["excel", "json", "html", "pdf"])


class TestBSEEData:
    """Test BSEE data command."""

    def test_bsee_data_help_exits_successfully(self):
        """Test that bsee data --help runs and exits with code 0."""
        result = runner.invoke(app, ["bsee", "data", "--help"])
        assert result.exit_code == 0

    def test_bsee_data_help_shows_options(self):
        """Test that bsee data --help displays available options."""
        result = runner.invoke(app, ["bsee", "data", "--help"])
        # Should list data retrieval options
        output_lower = result.output.lower()
        assert (
            "api" in output_lower or "block" in output_lower or "lease" in output_lower
        )


class TestBSEERefresh:
    """Test BSEE refresh command."""

    def test_bsee_refresh_help_exits_successfully(self):
        """Test that bsee refresh --help runs and exits with code 0."""
        result = runner.invoke(app, ["bsee", "refresh", "--help"])
        assert result.exit_code == 0

    def test_bsee_refresh_help_shows_options(self):
        """Test that bsee refresh --help displays available options."""
        result = runner.invoke(app, ["bsee", "refresh", "--help"])
        # Should show type and force options
        output_lower = result.output.lower()
        assert "type" in output_lower or "force" in output_lower


class TestBSEECLIEdgeCases:
    """Test edge cases for BSEE CLI commands."""

    def test_bsee_no_args_shows_help(self):
        """Test that bsee with no args shows help or error."""
        result = runner.invoke(app, ["bsee"])
        # Should show help when no subcommand provided
        assert result.exit_code in [0, 2]

    def test_bsee_invalid_subcommand(self):
        """Test that invalid subcommand returns error."""
        result = runner.invoke(app, ["bsee", "invalid-subcommand-xyz"])
        assert result.exit_code != 0

    def test_bsee_stats_with_invalid_flag(self):
        """Test that invalid flag handling is graceful."""
        result = runner.invoke(app, ["bsee", "stats", "--invalid-flag-xyz"])
        # Should return error for unknown flag
        assert result.exit_code != 0
