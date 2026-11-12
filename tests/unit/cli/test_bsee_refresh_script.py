"""Full refresh delegates to the existing registry script without network I/O."""

import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from worldenergydata.cli.commands import bsee

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "refresh_bsee_all.py"
LEGACY_MODULE = "worldenergydata.bsee.data.refresh.data_refresh"
runner = CliRunner()


@pytest.fixture
def dispatch(monkeypatch):
    child = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(subprocess, "run", child)
    legacy = Mock()
    legacy.return_value.router.return_value = ({}, None)
    module = ModuleType(LEGACY_MODULE)
    module.DataRefresh = legacy
    monkeypatch.setitem(sys.modules, LEGACY_MODULE, module)
    return child, legacy


@pytest.mark.parametrize(
    "arguments,forwarded",
    [
        ([], []),
        (["--type", "all"], []),
        (["--force"], ["--force"]),
        (["--dry-run"], ["--dry-run"]),
        (["--force", "--dry-run", "--verbose"], ["--force", "--dry-run"]),
    ],
)
def test_full_refresh_uses_registry_script(dispatch, arguments, forwarded):
    child, legacy = dispatch
    result = runner.invoke(bsee.app, ["refresh", *arguments])
    assert result.exit_code == 0, result.output
    child.assert_called_once_with(
        [sys.executable, str(SCRIPT), *forwarded], check=False
    )
    legacy.assert_not_called()


@pytest.mark.parametrize("code", [1, 7])
def test_full_refresh_preserves_failure_exit_code(dispatch, code):
    child, legacy = dispatch
    child.return_value = subprocess.CompletedProcess([], code)
    result = runner.invoke(bsee.app, ["refresh"])
    assert result.exit_code == code
    assert "completed successfully" not in result.output
    legacy.assert_not_called()


def test_full_refresh_reports_process_start_failure(dispatch):
    child, legacy = dispatch
    child.side_effect = OSError("process unavailable")
    result = runner.invoke(bsee.app, ["refresh"])
    assert result.exit_code == 1
    assert "process unavailable" in result.output
    legacy.assert_not_called()


def test_missing_script_reports_checkout_requirement(dispatch, tmp_path, monkeypatch):
    child, legacy = dispatch
    monkeypatch.setattr(
        bsee, "__file__", str(tmp_path / "src/worldenergydata/cli/commands/bsee.py")
    )
    result = runner.invoke(bsee.app, ["refresh"])
    assert result.exit_code == 1
    assert "repository checkout" in result.output
    child.assert_not_called()
    legacy.assert_not_called()


@pytest.mark.parametrize(
    "data_type", ["well", "production", "platform", "infrastructure"]
)
def test_typed_refresh_retains_existing_router(dispatch, data_type):
    child, legacy = dispatch
    result = runner.invoke(bsee.app, ["refresh", "--type", data_type])
    assert result.exit_code == 0, result.output
    child.assert_not_called()
    legacy.assert_called_once_with()
    legacy.return_value.router.assert_called_once()
    config = legacy.return_value.router.call_args.args[0]
    assert config["data"]["refresh"] is True
    assert config["meta"]["mode"] == (
        "legacy" if data_type in ("well", "production") else "enhanced"
    )


def test_typed_refresh_rejects_unsupported_dry_run(dispatch):
    child, legacy = dispatch
    result = runner.invoke(bsee.app, ["refresh", "--type", "well", "--dry-run"])
    assert result.exit_code == 2
    assert "only supported with --type all" in result.output
    child.assert_not_called()
    legacy.assert_not_called()


def test_typed_refresh_import_failure_is_unsuccessful(dispatch):
    child, legacy = dispatch
    legacy.side_effect = ImportError("refresh dependency unavailable")
    result = runner.invoke(bsee.app, ["refresh", "--type", "well"])
    assert result.exit_code == 1
    assert "refresh dependency unavailable" in result.output
    child.assert_not_called()


def test_refresh_help_includes_safe_preview(dispatch):
    child, legacy = dispatch
    result = runner.invoke(bsee.app, ["refresh", "--help"])
    assert result.exit_code == 0
    assert "dry-run" in result.output
    child.assert_not_called()
    legacy.assert_not_called()


def test_full_refresh_dry_run_from_another_directory(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from worldenergydata.cli.commands.bsee import app; app()",
            "refresh",
            "--dry-run",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "BSEE DATA REFRESH SUMMARY" in result.stdout
    assert "Total downloaded: 0.0 MB" in result.stdout
    assert "DRY-RUN: would download" in result.stderr
    assert list(tmp_path.iterdir()) == []
