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
