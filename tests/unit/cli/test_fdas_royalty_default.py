"""CLI defaults must preserve the recorded US Gulf source-note rate."""

from typer.testing import CliRunner

from worldenergydata.cli.commands.fdas import app


def test_analyze_default_royalty_matches_reported_assumption():
    """The deck note's 18.75 / 100 gives 0.1875 in both output sections."""
    result = CliRunner().invoke(app, ["analyze", "--field", "Synthetic"])
    assert result.exit_code == 0, result.output
    assert result.output.count("18.75%") == 2
    assert "18.80%" not in result.output
