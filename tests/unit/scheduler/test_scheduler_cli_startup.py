"""Startup/import-surface tests for scheduler no-op CLI paths.

These tests protect issue #353: scheduler help/no-op imports must not eagerly
load data-source job adapters or their heavy dependencies.
"""

from __future__ import annotations

import builtins
import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

SCHEDULER_CLI_MODULES = (
    "worldenergydata.scheduler.cli",
)

HEAVY_JOB_MODULE_PREFIXES = (
    "worldenergydata.scheduler.jobs.bsee_refresh",
    "worldenergydata.scheduler.jobs.sodir_refresh",
    "worldenergydata.scheduler.jobs.eia_us_refresh",
    "worldenergydata.scheduler.jobs.brazil_anp_refresh",
    "worldenergydata.scheduler.jobs.ukcs_refresh",
    "worldenergydata.scheduler.jobs.metocean_refresh",
    "worldenergydata.scheduler.jobs.lng_terminals_refresh",
)


@contextmanager
def _fresh_modules(prefixes: tuple[str, ...]) -> Iterator[None]:
    """Temporarily remove matching modules so imports exercise startup code."""
    saved = {
        name: module
        for name, module in list(sys.modules.items())
        if name == prefixes or any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes)
    }
    for name in saved:
        sys.modules.pop(name, None)
    try:
        yield
    finally:
        for name in list(sys.modules):
            if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
                sys.modules.pop(name, None)
        sys.modules.update(saved)


@contextmanager
def _forbid_imports(prefixes: tuple[str, ...]) -> Iterator[None]:
    """Raise if any forbidden module prefix is imported."""
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            raise AssertionError(f"forbidden eager import: {name}")
        return original_import(name, globals, locals, fromlist, level)

    builtins.__import__ = guarded_import
    try:
        yield
    finally:
        builtins.__import__ = original_import


def test_scheduler_cli_module_import_does_not_import_refresh_jobs():
    """Importing the scheduler CLI must be cheap and avoid job adapters."""
    prefixes = SCHEDULER_CLI_MODULES + HEAVY_JOB_MODULE_PREFIXES
    with _fresh_modules(prefixes), _forbid_imports(HEAVY_JOB_MODULE_PREFIXES):
        module = importlib.import_module("worldenergydata.scheduler.cli")

    assert hasattr(module, "main")


def test_scheduler_cli_no_args_does_not_import_refresh_jobs():
    """The no-arg usage path must not pay data-source import cost."""
    prefixes = SCHEDULER_CLI_MODULES + HEAVY_JOB_MODULE_PREFIXES
    with _fresh_modules(prefixes), _forbid_imports(HEAVY_JOB_MODULE_PREFIXES):
        module = importlib.import_module("worldenergydata.scheduler.cli")
        with pytest.raises(SystemExit) as exc_info:
            module.main([])

    assert exc_info.value.code == 0
