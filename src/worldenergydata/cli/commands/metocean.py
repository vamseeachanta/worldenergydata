# ABOUTME: CLI commands wrapper for metocean module.
# ABOUTME: Imports and exposes the Typer app from the metocean module.

"""
Metocean CLI Commands

Wrapper module that exposes the metocean module's CLI commands
to the main worldenergydata CLI.
"""

from worldenergydata.metocean.cli import app

__all__ = ["app"]
