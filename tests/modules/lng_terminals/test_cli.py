"""Tests for LNG terminal CLI."""

from typer.testing import CliRunner

from worldenergydata.modules.lng_terminals.cli import app

runner = CliRunner()


class TestCLI:
    """Test CLI commands."""

    def test_collect_runs(self):
        """collect command should run without error."""
        result = runner.invoke(app, ["collect"])
        assert result.exit_code == 0
        assert "Collecting" in result.output
        assert "Seed:" in result.output

    def test_process_runs(self):
        """process command should run without error."""
        result = runner.invoke(app, ["process"])
        assert result.exit_code == 0
        assert "Processing" in result.output
        assert "Normalized" in result.output
        assert "Deduplicated" in result.output

    def test_export_runs(self, tmp_path):
        """export command should create output files."""
        result = runner.invoke(
            app,
            [
                "export",
                "--output-dir",
                str(tmp_path),
                "--formats",
                "csv",
            ],
        )
        assert result.exit_code == 0
        assert "Exporting" in result.output
        # Check CSV was created
        csv_files = list(tmp_path.glob("*.csv"))
        assert len(csv_files) >= 1

    def test_report_runs(self, tmp_path):
        """report command should generate reports."""
        result = runner.invoke(
            app,
            [
                "report",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "reports" in result.output.lower() or "quality" in result.output.lower()

    def test_pipeline_runs(self, tmp_path):
        """pipeline command should run full end-to-end."""
        result = runner.invoke(
            app,
            [
                "pipeline",
                "--output-dir",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output
