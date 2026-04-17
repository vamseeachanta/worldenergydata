"""
Integration tests for the Marine Safety CLI commands.

Tests Marine Safety incident data CLI functionality including
statistics, scraping, database operations, and export commands.
"""

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.main import app

runner = CliRunner()


class TestMarineSafetyCLIHelp:
    """Test Marine Safety CLI help and information commands."""

    def test_marine_safety_help_exits_successfully(self):
        """Test that marine-safety --help runs and exits with code 0."""
        result = runner.invoke(app, ["marine-safety", "--help"])
        assert result.exit_code == 0

    def test_marine_safety_help_shows_commands(self):
        """Test that marine-safety --help displays available commands."""
        result = runner.invoke(app, ["marine-safety", "--help"])
        # Should list available marine safety commands
        output_lower = result.output.lower()
        assert (
            "stats" in output_lower or "scrape" in output_lower or "db" in output_lower
        )

    def test_marine_safety_help_shows_description(self):
        """Test that marine-safety --help shows module description."""
        result = runner.invoke(app, ["marine-safety", "--help"])
        # Should include marine safety related description
        output_lower = result.output.lower()
        assert (
            "marine" in output_lower
            or "safety" in output_lower
            or "incident" in output_lower
        )


class TestMarineSafetyStats:
    """Test Marine Safety stats command."""

    def test_marine_safety_stats_exits_successfully(self):
        """Test that marine-safety stats command runs and exits with code 0."""
        result = runner.invoke(app, ["marine-safety", "stats"])
        assert result.exit_code == 0

    def test_marine_safety_stats_shows_statistics(self):
        """Test that marine-safety stats displays statistics information."""
        result = runner.invoke(app, ["marine-safety", "stats"])
        # Should show some statistics-related output
        assert (
            "Statistics" in result.output
            or "Incidents" in result.output
            or "USCG" in result.output
        )

    def test_marine_safety_stats_verbose_flag(self):
        """Test that marine-safety stats accepts --verbose flag."""
        result = runner.invoke(app, ["marine-safety", "stats", "--verbose"])
        assert result.exit_code == 0

    def test_marine_safety_stats_source_filter(self):
        """Test that marine-safety stats accepts --source flag."""
        result = runner.invoke(app, ["marine-safety", "stats", "--source", "uscg"])
        assert result.exit_code == 0

    def test_marine_safety_stats_all_source(self):
        """Test that marine-safety stats with --source all works."""
        result = runner.invoke(app, ["marine-safety", "stats", "--source", "all"])
        assert result.exit_code == 0

    def test_marine_safety_stats_help(self):
        """Test that marine-safety stats --help shows command help."""
        result = runner.invoke(app, ["marine-safety", "stats", "--help"])
        assert result.exit_code == 0
        assert "source" in result.output.lower() or "stats" in result.output.lower()


class TestMarineSafetyInfo:
    """Test Marine Safety info command."""

    def test_marine_safety_info_exits_successfully(self):
        """Test that marine-safety info command runs and exits with code 0."""
        result = runner.invoke(app, ["marine-safety", "info"])
        assert result.exit_code == 0

    def test_marine_safety_info_shows_module_info(self):
        """Test that marine-safety info displays module information."""
        result = runner.invoke(app, ["marine-safety", "info"])
        # Should display module-related information
        output_lower = result.output.lower()
        assert any(
            term in output_lower
            for term in ["marine", "safety", "incident", "uscg", "ntsb"]
        )

    def test_marine_safety_info_shows_data_sources(self):
        """Test that marine-safety info lists data sources."""
        result = runner.invoke(app, ["marine-safety", "info"])
        output_lower = result.output.lower()
        # Should mention at least one data source
        assert any(
            source in output_lower for source in ["uscg", "ntsb", "bsee", "maib"]
        )


class TestMarineSafetyScrape:
    """Test Marine Safety scrape command."""

    def test_marine_safety_scrape_help_exits_successfully(self):
        """Test that marine-safety scrape --help runs and exits with code 0."""
        result = runner.invoke(app, ["marine-safety", "scrape", "--help"])
        assert result.exit_code == 0

    def test_marine_safety_scrape_uscg_help(self):
        """Test that marine-safety scrape uscg --help works."""
        result = runner.invoke(app, ["marine-safety", "scrape", "uscg", "--help"])
        assert result.exit_code == 0

    def test_marine_safety_scrape_uscg_help_shows_options(self):
        """Test that scrape uscg help shows available options."""
        result = runner.invoke(app, ["marine-safety", "scrape", "uscg", "--help"])
        output_lower = result.output.lower()
        # Should show year and output options
        assert "year" in output_lower or "output" in output_lower


class TestMarineSafetyDB:
    """Test Marine Safety database commands."""

    def test_marine_safety_db_help_exits_successfully(self):
        """Test that marine-safety db --help runs and exits with code 0."""
        result = runner.invoke(app, ["marine-safety", "db", "--help"])
        assert result.exit_code == 0

    def test_marine_safety_db_init_help(self):
        """Test that marine-safety db init --help works."""
        result = runner.invoke(app, ["marine-safety", "db", "init", "--help"])
        assert result.exit_code == 0

    def test_marine_safety_db_init_help_shows_options(self):
        """Test that db init help shows available options."""
        result = runner.invoke(app, ["marine-safety", "db", "init", "--help"])
        output_lower = result.output.lower()
        # Should show database-related options
        assert "force" in output_lower or "db" in output_lower or "dry" in output_lower

    def test_marine_safety_db_migrate_help(self):
        """Test that marine-safety db migrate --help works."""
        result = runner.invoke(app, ["marine-safety", "db", "migrate", "--help"])
        assert result.exit_code == 0


class TestMarineSafetyExport:
    """Test Marine Safety export command."""

    def test_marine_safety_export_help_exits_successfully(self):
        """Test that marine-safety export --help runs and exits with code 0."""
        result = runner.invoke(app, ["marine-safety", "export", "--help"])
        assert result.exit_code == 0

    def test_marine_safety_export_help_shows_formats(self):
        """Test that export help shows available formats."""
        result = runner.invoke(app, ["marine-safety", "export", "--help"])
        output_lower = result.output.lower()
        # Should mention export formats
        assert any(fmt in output_lower for fmt in ["csv", "json", "excel", "parquet"])


class TestMarineSafetyAnalyze:
    """Test Marine Safety analyze command."""

    def test_marine_safety_analyze_help_exits_successfully(self):
        """Test that marine-safety analyze --help runs and exits with code 0."""
        result = runner.invoke(app, ["marine-safety", "analyze", "--help"])
        assert result.exit_code == 0

    def test_marine_safety_analyze_help_shows_options(self):
        """Test that analyze help shows available options."""
        result = runner.invoke(app, ["marine-safety", "analyze", "--help"])
        output_lower = result.output.lower()
        # Should show analysis options
        assert (
            "type" in output_lower
            or "region" in output_lower
            or "output" in output_lower
        )


class TestMarineSafetyCLIEdgeCases:
    """Test edge cases for Marine Safety CLI commands."""

    def test_marine_safety_no_args_shows_help(self):
        """Test that marine-safety with no args shows help or error."""
        result = runner.invoke(app, ["marine-safety"])
        # Should show help when no subcommand provided
        assert result.exit_code in [0, 2]

    def test_marine_safety_invalid_subcommand(self):
        """Test that invalid subcommand returns error."""
        result = runner.invoke(app, ["marine-safety", "invalid-subcommand-xyz"])
        assert result.exit_code != 0

    def test_marine_safety_stats_invalid_source(self):
        """Test that invalid source handling is graceful."""
        result = runner.invoke(
            app, ["marine-safety", "stats", "--source", "invalid-source"]
        )
        # Should return error for invalid source
        assert result.exit_code != 0

    def test_marine_safety_abbreviation(self):
        """Test that abbreviated flags work."""
        result = runner.invoke(app, ["marine-safety", "stats", "-v"])
        assert result.exit_code == 0

    def test_marine_safety_stats_combined_flags(self):
        """Test stats with multiple flags combined."""
        result = runner.invoke(
            app, ["marine-safety", "stats", "--source", "uscg", "--verbose"]
        )
        assert result.exit_code == 0
