# ABOUTME: CLI commands wrapper for production forecast module.
# ABOUTME: Imports and exposes the Typer app from the forecast module.

"""Production Forecast CLI Commands

Wrapper module that exposes the production forecast module's CLI commands
to the main worldenergydata CLI.
"""

from worldenergydata.production.forecast.cli import app

__all__ = ["app"]
