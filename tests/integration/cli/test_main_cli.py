"""
Integration tests for the main WorldEnergyData CLI.

Tests the main CLI application commands including version, info, status,
and help functionality using typer.testing.CliRunner.
"""

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.main import app

runner = CliRunner()


class TestMainCLI:
    """Test suite for main CLI commands."""

    def test_version_command_exits_successfully(self):
        """Test that version command runs and exits with code 0."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0

    def test_version_command_contains_version_info(self):
        """Test that version command output contains version information."""
        result = runner.invoke(app, ["version"])
        # Should contain either version number or WorldEnergyData name
        assert "WorldEnergyData" in result.output or "Version" in result.output

    def test_info_command_exits_successfully(self):
        """Test that info command runs and exits with code 0."""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0

    def test_info_command_lists_modules(self):
        """Test that info command displays available modules."""
        result = runner.invoke(app, ["info"])
        # Should list at least the core modules
        assert "bsee" in result.output.lower()
        assert "marine" in result.output.lower() or "fdas" in result.output.lower()

    def test_help_command_exits_successfully(self):
        """Test that --help flag runs and exits with code 0."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_help_shows_available_commands(self):
        """Test that help output lists available commands."""
        result = runner.invoke(app, ["--help"])
        # Should show main commands and options
        assert "version" in result.output.lower() or "info" in result.output.lower()

    def test_help_shows_module_subcommands(self):
        """Test that help output lists module subcommands."""
        result = runner.invoke(app, ["--help"])
        # Should list module subcommands
        assert "bsee" in result.output.lower()
        assert "fdas" in result.output.lower()
        assert "marine-safety" in result.output.lower()

    def test_status_command_exits_successfully(self):
        """Test that status command runs and exits with code 0."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0

    def test_status_command_shows_system_status(self):
        """Test that status command displays system status information."""
        result = runner.invoke(app, ["status"])
        # Should display some status-related content
        assert (
            "Status" in result.output
            or "Component" in result.output
            or "Available" in result.output
            or "Not Found" in result.output
        )

    def test_no_args_shows_help_or_exits_cleanly(self):
        """Test that running with no arguments shows help or exits cleanly."""
        result = runner.invoke(app, [])
        # Should either exit with code 0 (showing help) or handle gracefully
        assert result.exit_code in [0, 2]  # 2 is common for no-args-is-help

    def test_verbose_flag_accepted(self):
        """Test that --verbose flag is accepted by the main app."""
        result = runner.invoke(app, ["--verbose", "--help"])
        # Should not error on verbose flag
        assert result.exit_code == 0

    def test_invalid_command_returns_error(self):
        """Test that invalid command returns non-zero exit code."""
        result = runner.invoke(app, ["invalid-command-xyz"])
        # Should return error for unknown command
        assert result.exit_code != 0


class TestMainCLIEdgeCases:
    """Test edge cases and error handling in main CLI."""

    def test_multiple_flags_accepted(self):
        """Test that multiple flags can be combined."""
        result = runner.invoke(app, ["--verbose", "version"])
        # Should accept multiple flags
        assert result.exit_code == 0

    def test_abbreviated_help_flag(self):
        """Test that -h abbreviated help flag works if supported."""
        result = runner.invoke(app, ["-h"])
        # Some CLIs support -h, some don't - just check it doesn't crash
        assert result.exit_code in [0, 2]  # 2 for unrecognized option is acceptable

    def test_version_with_verbose(self):
        """Test version command with verbose flag."""
        result = runner.invoke(app, ["--verbose", "version"])
        assert result.exit_code == 0
        assert "WorldEnergyData" in result.output or "Version" in result.output
