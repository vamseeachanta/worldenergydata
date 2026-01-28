# ABOUTME: Marine Safety CLI Interface - Main entry point.
# ABOUTME: Registers all command groups from split modules for managing incident data.

"""
Marine Safety CLI Interface

Provides command-line tools for managing marine safety incident data.
Uses Click for CLI framework and Rich for beautiful terminal output.

This is the main entry point that registers all command groups from
their respective modules:
- cli_scrape: Scraping commands (uscg, ntsb, bsee, imo, emsa, atsb)
- cli_import: Import commands (ntsb, uscg, bsee, emsa, imo, atsb, tsb, maib, noaa, boating)
- cli_correlate: Correlation commands (find-matches, link, stats)
- cli_refresh: Refresh commands (ntsb, atsb, tsb, maib, noaa, boating, imo, all)
- cli_db: Database commands (init, migrate, seed)
- cli_stats: Statistics command
- cli_export: Export and info commands
"""

import sys

import click

from worldenergydata.modules.marine_safety.cli_correlate import correlate
from worldenergydata.modules.marine_safety.cli_db import db
from worldenergydata.modules.marine_safety.cli_export import export, info
from worldenergydata.modules.marine_safety.cli_import import import_cmd
from worldenergydata.modules.marine_safety.cli_refresh import refresh

# Import command groups from split modules
from worldenergydata.modules.marine_safety.cli_scrape import scrape
from worldenergydata.modules.marine_safety.cli_stats import stats
from worldenergydata.modules.marine_safety.cli_utils import console


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Marine Safety Incident Data Management CLI

    Manage USCG and NTSB marine incident data: scraping, database operations,
    statistics, and data export.
    """
    pass


# Register command groups
cli.add_command(scrape)
cli.add_command(import_cmd, name="import")
cli.add_command(correlate)
cli.add_command(refresh)
cli.add_command(db)

# Register standalone commands
cli.add_command(stats)
cli.add_command(export)
cli.add_command(info)


def main():
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Fatal error:[/red] {str(e)}", style="bold")
        sys.exit(1)


if __name__ == "__main__":
    main()
