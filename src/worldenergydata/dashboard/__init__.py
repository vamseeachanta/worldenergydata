"""
Dashboard package — Plotly Dash web application for BSEE and FDAS data.

Entry points (imported lazily to avoid Dash startup cost on plain data use):
    run_server()   Start the Dash application on localhost.
    app            The Dash application instance (importable for testing).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any


def __getattr__(name: str) -> Any:
    """Lazy-load app and run_server to avoid importing Dash at package import time."""
    if name in ("app", "run_server"):
        from worldenergydata.dashboard.app import app as _app
        from worldenergydata.dashboard.app import run_server as _run_server

        if name == "app":
            return _app
        return _run_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app", "run_server"]
