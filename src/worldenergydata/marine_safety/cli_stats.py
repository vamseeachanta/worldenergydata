# ABOUTME: CLI commands for displaying marine safety incident statistics.
# ABOUTME: Provides detailed breakdowns by source, year, incident type, and more.

"""
Marine Safety CLI - Statistics Commands

Commands for displaying statistics about marine safety incident data.
"""

import sys
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import extract, func

from worldenergydata.marine_safety.cli_utils import console, get_source_enum


def _show_year_breakdown(session, source: str) -> None:
    """Display incident counts broken down by year."""
    from worldenergydata.marine_safety.database.models import Incident

    console.print()

    query = session.query(
        extract("year", Incident.incident_date).label("year"),
        func.count(Incident.incident_id).label("count"),
    ).filter(Incident.incident_date.isnot(None))

    if source != "all":
        source_enum = get_source_enum(source)
        if source_enum:
            query = query.filter(Incident.source_agency == source_enum)

    year_counts = (
        query.group_by(extract("year", Incident.incident_date))
        .order_by(extract("year", Incident.incident_date))
        .all()
    )

    if not year_counts:
        console.print("[yellow]No year data available[/yellow]")
        return

    table = Table(title="Incidents by Year", show_header=True, header_style="bold cyan")
    table.add_column("Year", justify="center")
    table.add_column("Count", justify="right")
    table.add_column("Bar", style="green")

    max_count = max(count for _, count in year_counts) if year_counts else 1

    for year, count in year_counts:
        bar_length = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "*" * bar_length
        table.add_row(str(int(year)), f"{count:,}", bar)

    console.print(table)


def _show_source_breakdown(session) -> None:
    """Display detailed statistics by data source."""
    from worldenergydata.marine_safety.database.models import Incident, Location

    console.print()

    # Get all sources with their stats
    source_stats = (
        session.query(
            Incident.source_agency,
            func.count(Incident.incident_id).label("total"),
            func.min(Incident.incident_date).label("min_date"),
            func.max(Incident.incident_date).label("max_date"),
            func.sum(Incident.fatalities).label("fatalities"),
            func.sum(Incident.injuries).label("injuries"),
            func.avg(Incident.data_quality_score).label("avg_quality"),
        )
        .group_by(Incident.source_agency)
        .order_by(func.count(Incident.incident_id).desc())
        .all()
    )

    if not source_stats:
        console.print("[yellow]No source data available[/yellow]")
        return

    table = Table(
        title="Detailed Source Breakdown", show_header=True, header_style="bold cyan"
    )
    table.add_column("Source", style="bold")
    table.add_column("Total", justify="right")
    table.add_column("Date Range", justify="center")
    table.add_column("Fatalities", justify="right")
    table.add_column("Injuries", justify="right")
    table.add_column("Avg Quality", justify="right")

    for stat in source_stats:
        source_name = (
            stat.source_agency.value.upper()
            if hasattr(stat.source_agency, "value")
            else str(stat.source_agency).upper()
        )
        date_range = f"{stat.min_date or 'N/A'} - {stat.max_date or 'N/A'}"
        fatalities = int(stat.fatalities) if stat.fatalities else 0
        injuries = int(stat.injuries) if stat.injuries else 0
        avg_quality = f"{float(stat.avg_quality):.2f}" if stat.avg_quality else "N/A"

        table.add_row(
            source_name,
            f"{stat.total:,}",
            date_range,
            str(fatalities),
            str(injuries),
            avg_quality,
        )

    console.print(table)

    # GPS coverage by source
    console.print()
    gps_table = Table(
        title="GPS Coverage by Source", show_header=True, header_style="bold cyan"
    )
    gps_table.add_column("Source", style="bold")
    gps_table.add_column("With GPS", justify="right")
    gps_table.add_column("Without GPS", justify="right")
    gps_table.add_column("Coverage %", justify="right")

    for stat in source_stats:
        source_name = (
            stat.source_agency.value.upper()
            if hasattr(stat.source_agency, "value")
            else str(stat.source_agency).upper()
        )

        with_gps = (
            session.query(func.count(Incident.incident_id))
            .join(Location, Incident.location_id == Location.location_id)
            .filter(
                Incident.source_agency == stat.source_agency,
                Location.latitude.isnot(None),
                Location.longitude.isnot(None),
            )
            .scalar()
            or 0
        )

        without_gps = stat.total - with_gps
        coverage = (with_gps / stat.total * 100) if stat.total > 0 else 0

        coverage_color = (
            "green" if coverage >= 70 else "yellow" if coverage >= 40 else "red"
        )

        gps_table.add_row(
            source_name,
            f"{with_gps:,}",
            f"{without_gps:,}",
            f"[{coverage_color}]{coverage:.1f}%[/{coverage_color}]",
        )

    console.print(gps_table)


@click.command()
@click.option(
    "--source",
    type=click.Choice(
        ["all", "uscg", "ntsb", "bsee", "imo", "atsb", "maib", "tsb"],
        case_sensitive=False,
    ),
    default="all",
    help="Data source to show statistics for",
)
@click.option("--by-year", is_flag=True, help="Show breakdown by year")
@click.option("--by-source", is_flag=True, help="Show detailed breakdown by source")
@click.option(
    "--db-url", help="Database connection URL (defaults to configured database)"
)
@click.option("--verbose", is_flag=True, help="Show detailed statistics")
def stats(
    source: str, by_year: bool, by_source: bool, db_url: Optional[str], verbose: bool
):
    """
    Display statistics about marine safety incident data

    Examples:
        marine-safety stats
        marine-safety stats --source ntsb
        marine-safety stats --by-year
        marine-safety stats --by-source --verbose
    """
    try:
        from sqlalchemy.exc import OperationalError

        from worldenergydata.marine_safety.database.db_manager import (
            get_db_manager,
        )
        from worldenergydata.marine_safety.database.models import (
            Incident,
            Location,
        )

        # Get database session
        db_manager = get_db_manager()

        try:
            with db_manager.session() as session:
                # Build base query with optional source filter
                base_query = session.query(Incident)
                if source != "all":
                    source_enum = get_source_enum(source)
                    if source_enum:
                        base_query = base_query.filter(
                            Incident.source_agency == source_enum
                        )

                # Get total count
                total_count = base_query.count()

                if total_count == 0:
                    console.print(
                        Panel(
                            "[yellow]No incident data found in the database.[/yellow]\n\n"
                            "To populate the database:\n"
                            "  1. Scrape data: marine-safety scrape ntsb\n"
                            "  2. Import data: marine-safety import ntsb <file>",
                            title="No Data",
                            border_style="yellow",
                        )
                    )
                    return

                # Main statistics table
                table = Table(
                    title="Marine Safety Incident Statistics",
                    show_header=True,
                    header_style="bold cyan",
                )
                table.add_column("Metric", style="dim")
                table.add_column("Value", justify="right")

                table.add_row(
                    "[bold]Total Incidents[/bold]", f"[bold]{total_count:,}[/bold]"
                )

                # Date range
                min_date = (
                    session.query(func.min(Incident.incident_date))
                    .filter(Incident.incident_date.isnot(None))
                    .scalar()
                )
                max_date = (
                    session.query(func.max(Incident.incident_date))
                    .filter(Incident.incident_date.isnot(None))
                    .scalar()
                )

                if min_date and max_date:
                    table.add_row("Date Range", f"{min_date} to {max_date}")

                # Count by source
                source_counts = (
                    session.query(
                        Incident.source_agency, func.count(Incident.incident_id)
                    )
                    .group_by(Incident.source_agency)
                    .all()
                )

                table.add_row("", "")
                table.add_row("[bold]By Source[/bold]", "")
                for src, count in sorted(
                    source_counts, key=lambda x: x[1], reverse=True
                ):
                    src_name = (
                        src.value.upper() if hasattr(src, "value") else str(src).upper()
                    )
                    table.add_row(f"  {src_name}", f"{count:,}")

                # Incident type distribution
                type_counts = (
                    session.query(
                        Incident.incident_type, func.count(Incident.incident_id)
                    )
                    .group_by(Incident.incident_type)
                    .order_by(func.count(Incident.incident_id).desc())
                    .limit(5)
                    .all()
                )

                if type_counts:
                    table.add_row("", "")
                    table.add_row("[bold]Top Incident Types[/bold]", "")
                    for inc_type, count in type_counts:
                        type_name = (
                            inc_type.value
                            if hasattr(inc_type, "value")
                            else str(inc_type)
                        )
                        table.add_row(
                            f"  {type_name.replace('_', ' ').title()}", f"{count:,}"
                        )

                # Records with GPS coordinates
                incidents_with_location = (
                    session.query(Incident)
                    .join(Location, Incident.location_id == Location.location_id)
                    .filter(
                        Location.latitude.isnot(None), Location.longitude.isnot(None)
                    )
                    .count()
                )

                gps_percentage = (
                    (incidents_with_location / total_count * 100)
                    if total_count > 0
                    else 0
                )
                table.add_row("", "")
                table.add_row(
                    "Records with GPS",
                    f"{incidents_with_location:,} ({gps_percentage:.1f}%)",
                )

                # Average data quality score
                avg_quality = (
                    session.query(func.avg(Incident.data_quality_score))
                    .filter(Incident.data_quality_score.isnot(None))
                    .scalar()
                )

                if avg_quality:
                    table.add_row("Avg Data Quality Score", f"{float(avg_quality):.2f}")

                # Verbose statistics
                if verbose:
                    table.add_row("", "")
                    table.add_row("[bold]Additional Statistics[/bold]", "")

                    # Unique vessels
                    unique_vessels = (
                        session.query(func.count(func.distinct(Incident.vessel_id)))
                        .filter(Incident.vessel_id.isnot(None))
                        .scalar()
                        or 0
                    )
                    table.add_row("Unique Vessels", f"{unique_vessels:,}")

                    # Unique companies
                    unique_companies = (
                        session.query(func.count(func.distinct(Incident.company_id)))
                        .filter(Incident.company_id.isnot(None))
                        .scalar()
                        or 0
                    )
                    table.add_row("Unique Companies", f"{unique_companies:,}")

                    # Total fatalities
                    total_fatalities = (
                        session.query(func.sum(Incident.fatalities)).scalar() or 0
                    )
                    table.add_row("Total Fatalities", f"{int(total_fatalities):,}")

                    # Total injuries
                    total_injuries = (
                        session.query(func.sum(Incident.injuries)).scalar() or 0
                    )
                    table.add_row("Total Injuries", f"{int(total_injuries):,}")

                    # Last updated record
                    last_updated = session.query(func.max(Incident.updated_at)).scalar()
                    if last_updated:
                        table.add_row(
                            "Last Updated", last_updated.strftime("%Y-%m-%d %H:%M")
                        )

                console.print(table)

                # By-year breakdown
                if by_year:
                    _show_year_breakdown(session, source)

                # By-source detailed breakdown
                if by_source:
                    _show_source_breakdown(session)

        except OperationalError as e:
            console.print(
                Panel(
                    f"[red]Database connection error:[/red]\n{str(e)}\n\n"
                    "Ensure the database is initialized:\n"
                    "  marine-safety db init",
                    title="Database Error",
                    border_style="red",
                )
            )
            sys.exit(1)

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        console.print("[yellow]Ensure database dependencies are installed[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)
