"""Startup/import-surface tests for the standalone BSEE refresh CLI."""

from __future__ import annotations

import builtins
import importlib.util
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "refresh_bsee_all.py"

FORBIDDEN_HELP_IMPORT_PREFIXES = (
    "pandas",
    "requests",
    "worldenergydata.bsee.data.refresh.url_registry",
)


@contextmanager
def _forbid_imports(prefixes: tuple[str, ...]) -> Iterator[None]:
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            raise AssertionError(f"forbidden eager import before CLI execution: {name}")
        return original_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import
    try:
        yield
    finally:
        builtins.__import__ = original_import


def test_refresh_bsee_all_module_import_does_not_load_download_dependencies():
    """Importing the script for --help/parser access must avoid heavy runtime deps."""
    module_name = "_issue_353_refresh_bsee_all_startup"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    with _forbid_imports(FORBIDDEN_HELP_IMPORT_PREFIXES):
        spec.loader.exec_module(module)

    assert hasattr(module, "main")


def test_refresh_dry_run_subprocess_regression_pin():
    """Regression pin: an installed workspace prints a plan without PYTHONPATH.

    The uninstalled system interpreter is checked separately before and after
    the bootstrap change; workspace-root discovery carries the import guard.
    """
    import os
    import subprocess

    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--dry-run"],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "DRY-RUN: would download" in result.stderr
    assert "BSEE DATA REFRESH SUMMARY" in result.stdout
    assert "Total downloaded: 0.0 MB" in result.stdout


def test_workspace_bootstrap_roots_and_idempotent_path(tmp_path, monkeypatch):
    """Existing source directories are ordered; missing roots are omitted."""
    monkeypatch.syspath_prepend(str(REPO_ROOT / "scripts"))
    from workspace_bootstrap import bootstrap_workspace, workspace_source_roots

    root_src = tmp_path / "src"
    alpha_src = tmp_path / "packages" / "alpha" / "src"
    zeta_src = tmp_path / "packages" / "zeta" / "src"
    for directory in (zeta_src, root_src, alpha_src):
        directory.mkdir(parents=True)
    (tmp_path / "packages" / "missing").mkdir()
    file_src = tmp_path / "packages" / "file" / "src"
    file_src.parent.mkdir()
    file_src.touch()
    expected = [root_src, alpha_src, zeta_src]
    assert workspace_source_roots(tmp_path) == expected
    assert workspace_source_roots(tmp_path / "absent") == []

    monkeypatch.setattr(sys, "path", ["unrelated"])
    bootstrap_workspace(tmp_path)
    bootstrap_workspace(tmp_path)
    assert sys.path == [str(path) for path in expected] + ["unrelated"]


def test_make_data_recipes_use_workspace_environment():
    """Both data recipes execute the refresh CLI through uv."""
    import re

    makefile = (REPO_ROOT / "Makefile").read_text()
    for target in ("data", "data-dry"):
        match = re.search(
            rf"(?m)^{target}:[^\n]*\n(?P<recipe>(?:\t[^\n]*\n)+)", makefile
        )
        assert match is not None, target
        assert "uv run python scripts/refresh_bsee_all.py" in match["recipe"], target
    assert "--dry-run" in match["recipe"]


def test_refresh_dry_run_no_network_regression_pin(monkeypatch, capsys):
    """Regression pin: the complete dry-run CLI issues no request or download."""
    from unittest.mock import Mock

    import requests

    monkeypatch.syspath_prepend(str(REPO_ROOT / "scripts"))
    import refresh_bsee_all

    request = Mock(side_effect=AssertionError("dry run attempted a network request"))
    download = Mock(side_effect=AssertionError("dry run attempted a download"))
    monkeypatch.setattr(requests.sessions.Session, "request", request)
    monkeypatch.setattr(
        refresh_bsee_all.BSEERefreshOrchestrator, "_download_zip", download
    )
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--dry-run"])
    monkeypatch.setattr(sys, "path", sys.path.copy())
    refresh_bsee_all.main()
    request.assert_not_called()
    download.assert_not_called()
    assert "Total downloaded: 0.0 MB" in capsys.readouterr().out


def test_edited_make_data_chain_uses_shared_bootstrap():
    """Each edited chain script delegates source-path setup to the helper."""
    import ast

    for script in (SCRIPT_PATH,):
        tree = ast.parse(script.read_text())
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        assert any(
            isinstance(node.func, ast.Name) and node.func.id == "bootstrap_workspace"
            for node in calls
        ), script.name
        assert any(
            isinstance(node, ast.ImportFrom) and node.module == "workspace_bootstrap"
            for node in ast.walk(tree)
        ), script.name
        assert not any(
            ast.unparse(node.func) in ("sys.path.insert", "sys.path.append")
            for node in calls
        ), script.name
