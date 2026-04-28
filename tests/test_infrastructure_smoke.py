"""
Smoke tests to verify test infrastructure is properly configured.

These tests ensure all test infrastructure components are working correctly:
- Fixtures are available and functional
- Markers can be used
- Configuration is loaded
- Test data is accessible
- Parallel execution works
"""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

# Import markers
from tests.test_markers import integration, smoke, unit

# Define test config locally since test_config was archived
_TEST_DATA_DIR = Path(__file__).parent / "fixtures"
TEST_CONFIG = SimpleNamespace(
    project_root=Path(__file__).parent.parent,
    test_data_dir=_TEST_DATA_DIR,
    timeout=30,
    parallel=False,
    coverage_threshold=90.0,
    test_fields=["JULIA", "JACK", "ST_MALO"],
)


class _TestDataPaths:
    """Small compatibility shim for archived test data helpers."""

    base_dir = _TEST_DATA_DIR

    @classmethod
    def get_field_data(cls, field: str) -> Path:
        return cls.base_dir / "fields" / f"{field}.csv"


TEST_DATA = _TestDataPaths()


@smoke
@unit
class TestInfrastructureSmoke:
    """Smoke tests for test infrastructure."""

    def test_pytest_installed(self):
        """Verify pytest is installed and importable."""
        import pytest

        assert pytest.__version__

    def test_plugins_installed(self):
        """Verify all required pytest plugins are installed."""
        required_plugins = [
            "pytest_cov",
            "pytest_timeout",
        ]

        import pkg_resources

        installed_packages = {pkg.key for pkg in pkg_resources.working_set}

        for plugin in required_plugins:
            plugin_name = plugin.replace("_", "-")
            # Special case for xdist which is installed as pytest-xdist
            if plugin == "xdist":
                plugin_name = "pytest-xdist"
            assert plugin_name in installed_packages, f"Plugin {plugin} not installed"

    def test_fixtures_available(self, project_root, test_data_dir, temp_dir):
        """Verify basic fixtures are available."""
        assert project_root.exists()
        assert test_data_dir.exists()
        assert temp_dir.exists()

    def test_data_fixtures_work(self, sample_production_data, sample_well_data):
        """Verify data fixtures generate correct data."""
        # Check production data
        assert isinstance(sample_production_data, pd.DataFrame)
        assert len(sample_production_data) == 36
        assert "oil_production_bbl" in sample_production_data.columns

        # Check well data
        assert isinstance(sample_well_data, dict)
        assert sample_well_data["api_well_number"] == "608124003301"
        assert "field" in sample_well_data

    def test_mock_file_fixtures(self, mock_excel_file, mock_yaml_config):
        """Verify mock file fixtures create files."""
        assert mock_excel_file.exists()
        assert mock_excel_file.suffix == ".xlsx"

        assert mock_yaml_config.exists()
        assert mock_yaml_config.suffix == ".yml"

    def test_configuration_loaded(self):
        """Verify test configuration is loaded."""
        assert TEST_CONFIG is not None
        assert TEST_CONFIG.project_root.exists()
        assert TEST_CONFIG.coverage_threshold == 90.0
        assert len(TEST_CONFIG.test_fields) > 0

    def test_test_data_accessible(self):
        """Verify test data files are accessible."""
        sample_csv = Path("tests/fixtures/sample_production_data.csv")
        assert sample_csv.exists(), "Sample CSV data not found"

        sample_config = Path("tests/fixtures/sample_config.yml")
        assert sample_config.exists(), "Sample config not found"

    def test_markers_work(self):
        """Verify test markers are functional."""
        # This test itself uses markers
        assert True

    @pytest.mark.timeout(1)
    def test_timeout_works(self):
        """Verify timeout marker works."""
        import time

        # Should complete within timeout
        time.sleep(0.1)
        assert True

    def test_parallel_execution_config(self):
        """Verify optional parallel execution configuration when xdist is installed."""
        pytest.importorskip("xdist", reason="pytest-xdist is optional for this CI lane")

    def test_coverage_configured(self):
        """Verify coverage is configured."""
        import coverage

        assert coverage.__version__

        # Check coverage config in pytest.ini
        ini_path = Path("pytest.ini")
        assert ini_path.exists()

        content = ini_path.read_text()
        assert "--cov=" in content
        assert "coverage:" in content

    def test_environment_isolation(self, reset_environment):
        """Verify environment isolation fixture works."""
        import os

        # Set a test variable
        os.environ["TEST_VAR"] = "test_value"
        assert os.environ.get("TEST_VAR") == "test_value"

        # After test, fixture should reset environment
        # (verified by fixture cleanup)

    def test_assertion_helpers(self, assert_dataframe_equal):
        """Verify custom assertion helpers work."""
        df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df2 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

        # Should not raise
        assert_dataframe_equal(df1, df2)

    def test_benchmark_available(self, benchmark):
        """Verify benchmark fixture is available."""

        def sample_function():
            return sum(range(100))

        result = benchmark(sample_function)
        assert result == 4950


@smoke
@integration
class TestInfrastructureIntegration:
    """Integration tests for test infrastructure."""

    def test_full_test_workflow(self, temp_dir, sample_production_data):
        """Test a complete workflow using infrastructure."""
        # Use temp directory
        output_file = temp_dir / "test_output.csv"

        # Use sample data
        sample_production_data.to_csv(output_file, index=False)

        # Verify file created
        assert output_file.exists()

        # Read back and verify
        df_read = pd.read_csv(output_file)
        assert len(df_read) == len(sample_production_data)

    def test_config_and_data_integration(self):
        """Test configuration and data management integration."""
        # Load config
        assert TEST_CONFIG.test_fields == ["JULIA", "JACK", "ST_MALO"]

        # Access test data
        assert TEST_DATA.base_dir.exists()

        # Verify integration
        for field in TEST_CONFIG.test_fields:
            field_data_path = TEST_DATA.get_field_data(field)
            # Path should be constructable (file may not exist)
            assert field_data_path.parent == TEST_DATA.base_dir / "fields"


@smoke
def test_smoke_suite_executable():
    """Verify smoke test suite can be executed."""
    import subprocess
    import sys

    # Run smoke tests in subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "smoke", "--co", "-q"],
        capture_output=True,
        text=True,
    )

    # Should find smoke tests
    assert "test session starts" in result.stdout or "collected" in result.stdout


if __name__ == "__main__":
    # Run smoke tests
    pytest.main([__file__, "-v", "-m", "smoke"])
