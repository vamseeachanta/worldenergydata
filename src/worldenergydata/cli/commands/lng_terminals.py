"""
LNG Terminals CLI Commands

Provides command-line interface for global LNG terminal dataset management
including data collection, processing, export, and analysis reports.

Usage:
    worldenergydata lng-terminals <command> [options]

Examples:
    worldenergydata lng-terminals collect --refresh-mode cache_first
    worldenergydata lng-terminals process
    worldenergydata lng-terminals export --formats csv,parquet
    worldenergydata lng-terminals report
    worldenergydata lng-terminals pipeline
"""

from worldenergydata.modules.lng_terminals.cli import app

__all__ = ["app"]
