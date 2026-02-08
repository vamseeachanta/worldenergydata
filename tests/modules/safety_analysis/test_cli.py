# ABOUTME: Integration tests for safety analysis Typer CLI commands.
"""
Phase 4 integration tests for the safety analysis CLI.

Tests verify that CLI commands exist, respond to --help, and
handle basic input scenarios. Full pipeline execution is covered
by unit tests in earlier phases; these tests exercise the Typer
command interface itself.
"""

import pytest
from typer.testing import CliRunner

from worldenergydata.safety_analysis.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv_for_cli(tmp_path):
    """Create a minimal observations CSV for CLI load tests."""
    csv_path = tmp_path / "observations.csv"
    csv_path.write_text(
        "rig_id,date,description,obs_type\n"
        "RIG-001,2024-01-15,Worker wearing PPE,safe\n"
        "RIG-002,2024-02-20,Unsafe behavior observed,at_risk\n"
    )
    return csv_path


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------


class TestCLI:
    """Tests for safety analysis CLI commands via CliRunner."""

    def test_app_help(self):
        """The top-level --help exits 0 and mentions safety analysis."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # The help text should reference the module purpose
        output_lower = result.stdout.lower()
        assert "safety" in output_lower or "analysis" in output_lower

    def test_status_command(self):
        """The status command exits 0 and shows module information."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert len(result.stdout) > 0

    def test_load_command(self, sample_csv_for_cli):
        """The load command accepts a file path and exits 0."""
        result = runner.invoke(app, ["load", str(sample_csv_for_cli)])
        assert result.exit_code == 0

    def test_load_missing_file(self):
        """The load command exits non-zero when given a nonexistent file."""
        result = runner.invoke(app, ["load", "/nonexistent/path/data.csv"])
        assert result.exit_code != 0

    def test_classify_help(self):
        """The classify command responds to --help."""
        result = runner.invoke(app, ["classify", "--help"])
        assert result.exit_code == 0
        assert "classify" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_correlate_help(self):
        """The correlate command responds to --help."""
        result = runner.invoke(app, ["correlate", "--help"])
        assert result.exit_code == 0
        assert "correlat" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_report_help(self):
        """The report command responds to --help."""
        result = runner.invoke(app, ["report", "--help"])
        assert result.exit_code == 0
        assert "report" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_unknown_command(self):
        """Invoking an unknown sub-command exits non-zero."""
        result = runner.invoke(app, ["nonexistent-command"])
        assert result.exit_code != 0
