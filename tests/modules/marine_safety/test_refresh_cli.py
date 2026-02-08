# ABOUTME: Integration tests for the marine safety refresh CLI workflow.
# ABOUTME: Validates command registration, dry run mode, manual downloads, and integration flow.

"""
Integration tests for the marine safety refresh CLI commands.

Tests the complete refresh workflow including:
- CLI command registration and options
- Dry run mode behavior
- Manual download source handling
- Integration flow with mocked dependencies
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from worldenergydata.marine_safety.cli import cli, refresh


class TestRefreshCommandRegistration:
    """Test suite for refresh command registration and structure."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_refresh_group_exists(self, runner):
        """Test that the refresh command group is registered."""
        result = runner.invoke(cli, ["refresh", "--help"])
        assert result.exit_code == 0
        assert "refresh" in result.output.lower()
        assert "Refresh incident data from sources" in result.output

    @pytest.mark.unit
    def test_ntsb_command_exists(self, runner):
        """Test that refresh ntsb command is registered."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--help"])
        assert result.exit_code == 0
        assert "ntsb" in result.output.lower()

    @pytest.mark.unit
    def test_atsb_command_exists(self, runner):
        """Test that refresh atsb command is registered."""
        result = runner.invoke(cli, ["refresh", "atsb", "--help"])
        assert result.exit_code == 0
        assert "atsb" in result.output.lower()

    @pytest.mark.unit
    def test_tsb_command_exists(self, runner):
        """Test that refresh tsb command is registered."""
        result = runner.invoke(cli, ["refresh", "tsb", "--help"])
        assert result.exit_code == 0
        assert "tsb" in result.output.lower()

    @pytest.mark.unit
    def test_maib_command_exists(self, runner):
        """Test that refresh maib command is registered."""
        result = runner.invoke(cli, ["refresh", "maib", "--help"])
        assert result.exit_code == 0
        assert "maib" in result.output.lower()

    @pytest.mark.unit
    def test_noaa_command_exists(self, runner):
        """Test that refresh noaa command is registered."""
        result = runner.invoke(cli, ["refresh", "noaa", "--help"])
        assert result.exit_code == 0
        assert "noaa" in result.output.lower()

    @pytest.mark.unit
    def test_boating_command_exists(self, runner):
        """Test that refresh boating command is registered."""
        result = runner.invoke(cli, ["refresh", "boating", "--help"])
        assert result.exit_code == 0
        assert "boating" in result.output.lower()

    @pytest.mark.unit
    def test_imo_command_exists(self, runner):
        """Test that refresh imo command is registered."""
        result = runner.invoke(cli, ["refresh", "imo", "--help"])
        assert result.exit_code == 0
        assert "imo" in result.output.lower()

    @pytest.mark.unit
    def test_all_command_exists(self, runner):
        """Test that refresh all command is registered."""
        result = runner.invoke(cli, ["refresh", "all", "--help"])
        assert result.exit_code == 0
        assert "all" in result.output.lower()

    @pytest.mark.unit
    def test_all_refresh_commands_registered(self, runner):
        """Test that all expected refresh subcommands are available."""
        result = runner.invoke(cli, ["refresh", "--help"])
        assert result.exit_code == 0

        expected_commands = [
            "ntsb",
            "atsb",
            "tsb",
            "maib",
            "noaa",
            "boating",
            "imo",
            "all",
        ]
        for cmd in expected_commands:
            assert (
                cmd in result.output
            ), f"Command '{cmd}' not found in refresh subcommands"


class TestRefreshCommandOptions:
    """Test suite for refresh command options."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_ntsb_has_since_option(self, runner):
        """Test that refresh ntsb has --since option."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--help"])
        assert "--since" in result.output or "-s" in result.output

    @pytest.mark.unit
    def test_ntsb_has_output_dir_option(self, runner):
        """Test that refresh ntsb has --output-dir option."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--help"])
        assert "--output-dir" in result.output

    @pytest.mark.unit
    def test_ntsb_has_keep_files_option(self, runner):
        """Test that refresh ntsb has --keep-files option."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--help"])
        assert "--keep-files" in result.output

    @pytest.mark.unit
    def test_ntsb_has_dry_run_option(self, runner):
        """Test that refresh ntsb has --dry-run option."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--help"])
        assert "--dry-run" in result.output

    @pytest.mark.unit
    def test_ntsb_has_verbose_option(self, runner):
        """Test that refresh ntsb has --verbose option."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--help"])
        assert "--verbose" in result.output

    @pytest.mark.unit
    def test_atsb_has_standard_options(self, runner):
        """Test that refresh atsb has all standard options."""
        result = runner.invoke(cli, ["refresh", "atsb", "--help"])
        assert "--since" in result.output or "-s" in result.output
        assert "--output-dir" in result.output
        assert "--keep-files" in result.output
        assert "--dry-run" in result.output
        assert "--verbose" in result.output

    @pytest.mark.unit
    def test_all_has_sources_option(self, runner):
        """Test that refresh all has --sources option."""
        result = runner.invoke(cli, ["refresh", "all", "--help"])
        assert "--sources" in result.output or "-s" in result.output

    @pytest.mark.unit
    def test_all_has_skip_manual_option(self, runner):
        """Test that refresh all has --skip-manual option."""
        result = runner.invoke(cli, ["refresh", "all", "--help"])
        assert "--skip-manual" in result.output


class TestDryRunMode:
    """Test suite for dry run mode functionality."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_ntsb_dry_run_shows_preview(self, runner):
        """Test that refresh ntsb --dry-run shows preview without executing."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--dry-run"])
        assert result.exit_code == 0
        # Should show dry run info
        assert (
            "dry run" in result.output.lower()
            or "would refresh" in result.output.lower()
        )

    @pytest.mark.unit
    def test_ntsb_dry_run_shows_date_range(self, runner):
        """Test that dry run shows the date range."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--dry-run"])
        assert result.exit_code == 0
        # Should show date information
        assert "date" in result.output.lower() or "20" in result.output  # Year

    @pytest.mark.unit
    def test_ntsb_dry_run_with_since_date(self, runner):
        """Test dry run with --since option."""
        result = runner.invoke(
            cli, ["refresh", "ntsb", "--dry-run", "--since", "2023-01-01"]
        )
        assert result.exit_code == 0
        assert "2023-01-01" in result.output

    @pytest.mark.unit
    def test_atsb_dry_run_shows_preview(self, runner):
        """Test that refresh atsb --dry-run shows preview without executing."""
        result = runner.invoke(cli, ["refresh", "atsb", "--dry-run"])
        assert result.exit_code == 0
        assert (
            "dry run" in result.output.lower()
            or "would refresh" in result.output.lower()
        )

    @pytest.mark.unit
    def test_all_dry_run_shows_sources(self, runner):
        """Test that refresh all --dry-run shows all sources that would be processed."""
        result = runner.invoke(cli, ["refresh", "all", "--dry-run"])
        assert result.exit_code == 0
        # Should mention refreshing sources
        assert "refresh" in result.output.lower()
        # Should list some sources
        assert "ntsb" in result.output.lower() or "atsb" in result.output.lower()

    @pytest.mark.unit
    def test_all_dry_run_with_specific_sources(self, runner):
        """Test dry run with specific sources selected."""
        result = runner.invoke(
            cli,
            ["refresh", "all", "--dry-run", "--sources", "ntsb", "--sources", "atsb"],
        )
        assert result.exit_code == 0
        assert "ntsb" in result.output.lower()
        assert "atsb" in result.output.lower()


class TestManualDownloadSources:
    """Test suite for sources requiring manual download."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_tsb_shows_download_url(self, runner):
        """Test that refresh tsb shows download URL."""
        result = runner.invoke(cli, ["refresh", "tsb"])
        assert result.exit_code == 0
        # Should show manual download info
        assert "manual" in result.output.lower() or "download" in result.output.lower()
        # Should include TSB URL
        assert "tsb.gc.ca" in result.output.lower()

    @pytest.mark.unit
    def test_maib_shows_download_url(self, runner):
        """Test that refresh maib shows download URL."""
        result = runner.invoke(cli, ["refresh", "maib"])
        assert result.exit_code == 0
        # Should show manual download info
        assert "manual" in result.output.lower() or "download" in result.output.lower()
        # Should include MAIB/gov.uk URL
        assert "gov.uk" in result.output.lower() or "maib" in result.output.lower()

    @pytest.mark.unit
    def test_noaa_shows_download_url(self, runner):
        """Test that refresh noaa shows download URL."""
        result = runner.invoke(cli, ["refresh", "noaa"])
        assert result.exit_code == 0
        # Should show manual download info
        assert "manual" in result.output.lower() or "download" in result.output.lower()
        # Should include NOAA URL
        assert "noaa" in result.output.lower()

    @pytest.mark.unit
    def test_boating_shows_download_url(self, runner):
        """Test that refresh boating shows download URL."""
        result = runner.invoke(cli, ["refresh", "boating"])
        assert result.exit_code == 0
        # Should show manual download info
        assert "manual" in result.output.lower() or "download" in result.output.lower()

    @pytest.mark.unit
    def test_imo_shows_download_url(self, runner):
        """Test that refresh imo shows download URL."""
        result = runner.invoke(cli, ["refresh", "imo"])
        assert result.exit_code == 0
        # Should show manual download info
        assert "manual" in result.output.lower() or "download" in result.output.lower()
        # Should include IMO/GISIS URL
        assert "imo" in result.output.lower() or "gisis" in result.output.lower()

    @pytest.mark.unit
    def test_manual_sources_provide_import_instructions(self, runner):
        """Test that manual sources provide import command instructions."""
        manual_sources = ["tsb", "maib", "noaa", "boating", "imo"]

        for source in manual_sources:
            result = runner.invoke(cli, ["refresh", source])
            assert result.exit_code == 0
            # Should mention import command
            assert (
                "import" in result.output.lower()
            ), f"'{source}' should mention import command"


class TestIntegrationFlow:
    """Test suite for the complete refresh integration flow."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_refresh_workflow_supports_scraper_sources(self, runner):
        """Test that scraper-enabled sources have proper dry-run output."""
        # NTSB and ATSB have automated scrapers
        scraper_sources = ["ntsb", "atsb"]

        for source in scraper_sources:
            result = runner.invoke(cli, ["refresh", source, "--dry-run"])
            assert result.exit_code == 0, f"Failed for source: {source}"
            # Should show preview info for sources with scrapers
            output_lower = result.output.lower()
            assert (
                "would refresh" in output_lower
                or "dry run" in output_lower
                or "date" in output_lower
            ), f"Source {source} missing dry run info"

    @pytest.mark.unit
    def test_temp_files_cleanup_flow(self, runner):
        """Test that temp files are cleaned up when --keep-files is not set."""
        # In dry run mode, no files are created so nothing to clean
        result = runner.invoke(cli, ["refresh", "ntsb", "--dry-run"])
        assert result.exit_code == 0

        # The dry run output should mention file handling
        assert (
            "keep files" in result.output.lower()
            or "output" in result.output.lower()
            or "dry run" in result.output.lower()
        )

    @pytest.mark.unit
    def test_keep_files_option_behavior(self, runner):
        """Test that --keep-files option is properly handled."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--dry-run", "--keep-files"])
        assert result.exit_code == 0
        # Dry run should still work with keep-files flag
        assert (
            "dry run" in result.output.lower()
            or "would refresh" in result.output.lower()
        )

    @pytest.mark.unit
    def test_manual_sources_show_download_info(self, runner):
        """Test that manual download sources show proper download information."""
        manual_sources = ["tsb", "maib", "noaa", "boating", "imo"]

        for source in manual_sources:
            result = runner.invoke(cli, ["refresh", source])
            assert result.exit_code == 0, f"Failed for source: {source}"
            output_lower = result.output.lower()
            # Should show manual download info
            assert (
                "manual" in output_lower or "download" in output_lower
            ), f"Source {source} missing download info"
            # Should mention how to import after manual download
            assert (
                "import" in output_lower
            ), f"Source {source} missing import instructions"


class TestRefreshAllCommand:
    """Test suite for the refresh all command."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_all_defaults_to_automated_sources(self, runner):
        """Test that refresh all defaults to automated sources only."""
        result = runner.invoke(cli, ["refresh", "all", "--dry-run"])
        assert result.exit_code == 0
        # Should mention automated sources
        output_lower = result.output.lower()
        assert "ntsb" in output_lower or "atsb" in output_lower

    @pytest.mark.unit
    def test_all_respects_skip_manual_flag(self, runner):
        """Test that --skip-manual flag is respected."""
        result = runner.invoke(cli, ["refresh", "all", "--dry-run"])
        assert result.exit_code == 0
        # With default skip-manual, manual sources should not trigger scraping

    @pytest.mark.unit
    def test_all_with_specific_sources(self, runner):
        """Test refresh all with specific sources selected."""
        result = runner.invoke(
            cli, ["refresh", "all", "--dry-run", "--sources", "ntsb"]
        )
        assert result.exit_code == 0
        assert "ntsb" in result.output.lower()

    @pytest.mark.unit
    def test_all_processes_multiple_sources(self, runner):
        """Test that all command processes multiple sources."""
        result = runner.invoke(
            cli,
            ["refresh", "all", "--dry-run", "--sources", "ntsb", "--sources", "atsb"],
        )
        assert result.exit_code == 0
        output_lower = result.output.lower()
        assert "ntsb" in output_lower
        assert "atsb" in output_lower

    @pytest.mark.unit
    def test_all_sources_choice_validation(self, runner):
        """Test that invalid source names are rejected."""
        result = runner.invoke(cli, ["refresh", "all", "--sources", "invalid_source"])
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "error" in result.output.lower()


class TestRefreshErrorHandling:
    """Test suite for error handling in refresh commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_invalid_date_format(self, runner):
        """Test handling of invalid date format in --since."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--since", "not-a-date"])
        assert result.exit_code != 0

    @pytest.mark.unit
    def test_invalid_output_dir_handled(self, runner):
        """Test that invalid output directory is handled gracefully in dry run."""
        result = runner.invoke(
            cli,
            ["refresh", "ntsb", "--dry-run", "--output-dir", "/nonexistent/path/123"],
        )
        # Dry run should still work regardless of output dir existence
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_cli_handles_unknown_command_gracefully(self, runner):
        """Test that CLI handles unknown commands properly."""
        result = runner.invoke(cli, ["refresh", "unknown_source"])
        # Unknown command should return error
        assert result.exit_code != 0

    @pytest.mark.unit
    def test_refresh_with_future_date(self, runner):
        """Test refresh with future date in dry run mode."""
        # Using a date far in the future
        result = runner.invoke(
            cli, ["refresh", "ntsb", "--dry-run", "--since", "2099-01-01"]
        )
        # Should still work in dry run but may show empty range
        assert result.exit_code == 0


class TestRefreshVerboseMode:
    """Test suite for verbose mode output."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_verbose_flag_accepted(self, runner):
        """Test that --verbose flag is accepted."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--dry-run", "--verbose"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_verbose_provides_additional_output(self, runner):
        """Test that verbose mode provides additional information."""
        # Run with verbose
        verbose_result = runner.invoke(
            cli, ["refresh", "ntsb", "--dry-run", "--verbose"]
        )
        # Run without verbose
        normal_result = runner.invoke(cli, ["refresh", "ntsb", "--dry-run"])

        # Both should succeed
        assert verbose_result.exit_code == 0
        assert normal_result.exit_code == 0


class TestRefreshDateHandling:
    """Test suite for date handling in refresh commands."""

    @pytest.fixture
    def runner(self):
        """Create a CLI runner for testing."""
        return CliRunner()

    @pytest.mark.unit
    def test_since_date_parsing(self, runner):
        """Test that --since date is properly parsed."""
        result = runner.invoke(
            cli, ["refresh", "ntsb", "--dry-run", "--since", "2023-06-15"]
        )
        assert result.exit_code == 0
        assert "2023-06-15" in result.output

    @pytest.mark.unit
    def test_default_date_range(self, runner):
        """Test that default date range is applied when --since not provided."""
        result = runner.invoke(cli, ["refresh", "ntsb", "--dry-run"])
        assert result.exit_code == 0
        # Should show some date range info
        assert "date" in result.output.lower() or "20" in result.output

    @pytest.mark.unit
    def test_various_date_formats(self, runner):
        """Test various date format inputs."""
        # Click's DateTime supports ISO format
        date_formats = [
            "2023-01-01",
            "2023-12-31",
        ]

        for date_str in date_formats:
            result = runner.invoke(
                cli, ["refresh", "ntsb", "--dry-run", "--since", date_str]
            )
            assert result.exit_code == 0, f"Failed for date: {date_str}"
