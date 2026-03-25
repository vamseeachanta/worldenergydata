"""
Pytest configuration for CLI integration tests.

Provides fixtures for CLI testing using typer.testing.CliRunner.
"""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Create a CliRunner instance for testing CLI commands.

    Returns:
        CliRunner: A typer test runner that captures CLI output.
    """
    return CliRunner()


@pytest.fixture
def isolated_cli_runner():
    """Create a CliRunner with mix_stderr=False for cleaner output.

    Returns:
        CliRunner: A typer test runner with separated stdout/stderr.
    """
    return CliRunner(mix_stderr=False)
