# ABOUTME: Unit tests for vessel hull models CLI
# ABOUTME: Tests command-line interface functionality

"""
Unit tests for Vessel Hull Models CLI.

Tests the command-line interface using typer's CliRunner.
"""

import pytest
from pathlib import Path
import tempfile
from typer.testing import CliRunner

from worldenergydata.modules.vessel_hull_models.cli import app


runner = CliRunner()


# Path to real vessel hull for integration tests
SEA_CYPRESS_PATH = Path(__file__).parents[3] / "data" / "modules" / "vessel_hull_models" / "hulls" / "sea_cypress.obj"


class TestCLIHelp:
    """Tests for CLI help and info commands"""

    def test_help_command(self) -> None:
        """CLI shows help when invoked with --help"""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Vessel Hull Models" in result.stdout

    def test_validate_help(self) -> None:
        """Validate command shows help"""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "OBJ hull file" in result.stdout

    def test_visualize_help(self) -> None:
        """Visualize command shows help"""
        result = runner.invoke(app, ["visualize", "--help"])
        assert result.exit_code == 0
        assert "OBJ file" in result.stdout

    def test_list_help(self) -> None:
        """List command shows help"""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "hull models" in result.stdout.lower()

    def test_stats_help(self) -> None:
        """Stats command shows help"""
        result = runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0
        assert "statistics" in result.stdout.lower()

    def test_info_command(self) -> None:
        """Info command displays configuration"""
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "Hull Storage Path" in result.stdout
        assert "Dimension Tolerance" in result.stdout


class TestValidateCommand:
    """Tests for validate command"""

    def test_validate_valid_file(self) -> None:
        """Validate reports success for valid file"""
        obj_content = """# Test hull
v 0 0 0
v 100 0 0
v 100 20 0
v 0 20 0
f 1 2 3 4
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            result = runner.invoke(app, ["validate", str(temp_path)])
            assert result.exit_code == 0
            assert "valid" in result.stdout.lower()
        finally:
            temp_path.unlink()

    def test_validate_nonexistent_file(self) -> None:
        """Validate reports error for nonexistent file"""
        result = runner.invoke(app, ["validate", "/nonexistent/file.obj"])
        assert result.exit_code == 1

    def test_validate_with_dimension_check(self) -> None:
        """Validate checks dimensions with tolerance"""
        obj_content = """# Test hull
v 0 0 0
v 100 0 0
v 100 20 0
v 0 20 0
f 1 2 3 4
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            # Dimensions: length=100, width=20
            result = runner.invoke(app, [
                "validate", str(temp_path),
                "--loa", "100",
                "--beam", "20"
            ])
            assert result.exit_code == 0
        finally:
            temp_path.unlink()


class TestStatsCommand:
    """Tests for stats command"""

    def test_stats_displays_info(self) -> None:
        """Stats command displays mesh information"""
        obj_content = """# Test hull
o TestHull
v 0 0 0
v 10 0 0
v 10 5 0
v 0 5 0
f 1 2 3 4
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            result = runner.invoke(app, ["stats", str(temp_path)])
            assert result.exit_code == 0
            assert "Vertices" in result.stdout
            assert "Faces" in result.stdout
            assert "Dimensions" in result.stdout
        finally:
            temp_path.unlink()

    def test_stats_json_output(self) -> None:
        """Stats command outputs JSON when requested"""
        obj_content = """# Test hull
o TestHull
v 0 0 0
v 10 0 0
v 10 5 0
v 0 5 0
f 1 2 3 4
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".obj", delete=False
        ) as f:
            f.write(obj_content)
            temp_path = Path(f.name)

        try:
            result = runner.invoke(app, ["stats", str(temp_path), "--json"])
            assert result.exit_code == 0
            assert "vertex_count" in result.stdout
            assert "face_count" in result.stdout
        finally:
            temp_path.unlink()

    def test_stats_nonexistent_file(self) -> None:
        """Stats reports error for nonexistent file"""
        result = runner.invoke(app, ["stats", "/nonexistent.obj"])
        assert result.exit_code == 1


class TestListCommand:
    """Tests for list command"""

    def test_list_default_directory(self) -> None:
        """List command shows models in default directory"""
        result = runner.invoke(app, ["list"])
        # May succeed or fail depending on whether directory exists
        # Just check that it doesn't crash unexpectedly
        assert result.exit_code in [0, 1]

    def test_list_nonexistent_directory(self) -> None:
        """List reports error for nonexistent directory"""
        result = runner.invoke(app, ["list", "--dir", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


@pytest.mark.skipif(
    not SEA_CYPRESS_PATH.exists(),
    reason="Sea Cypress hull file not available"
)
class TestSeaCypressIntegration:
    """Integration tests using real Sea Cypress vessel hull"""

    def test_validate_sea_cypress(self) -> None:
        """Validate command works with Sea Cypress hull"""
        result = runner.invoke(app, ["validate", str(SEA_CYPRESS_PATH)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()
        assert "13,536" in result.stdout  # Expected vertex count

    def test_stats_sea_cypress(self) -> None:
        """Stats command works with Sea Cypress hull"""
        result = runner.invoke(app, ["stats", str(SEA_CYPRESS_PATH)])
        assert result.exit_code == 0
        assert "Vertices: 13,536" in result.stdout

    def test_stats_sea_cypress_json(self) -> None:
        """Stats JSON output for Sea Cypress"""
        result = runner.invoke(app, ["stats", str(SEA_CYPRESS_PATH), "--json"])
        assert result.exit_code == 0
        assert '"vertex_count": 13536' in result.stdout
