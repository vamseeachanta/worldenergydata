# ABOUTME: CLI commands for cross-source incident correlation and deduplication.
# ABOUTME: Provides matching, linking, and statistics for related incidents.

"""
Marine Safety CLI - Correlation Commands

Commands for cross-source incident correlation and deduplication.
"""

import sys
from typing import Optional

import click
from rich.table import Table
from sqlalchemy import func

from worldenergydata.modules.marine_safety.cli_utils import (
    console,
    create_progress_spinner,
)


@click.group()
def correlate():
    """Cross-source incident correlation and deduplication"""
    pass


@correlate.command(name="find-matches")
@click.option(
    "--source",
    type=click.Choice(["all", "ntsb", "imo", "atsb", "uscg"], case_sensitive=False),
    default="all",
    help="Source to correlate (default: all)",
)
@click.option(
    "--min-confidence",
    type=float,
    default=0.7,
    help="Minimum confidence threshold (default: 0.7)",
)
@click.option(
    "--date-tolerance", type=int, default=3, help="Date tolerance in days (default: 3)"
)
@click.option(
    "--location-threshold",
    type=float,
    default=50.0,
    help="Location threshold in km (default: 50)",
)
@click.option("--limit", type=int, help="Limit number of incidents to process")
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Enable verbose output")
def find_matches(
    source: str,
    min_confidence: float,
    date_tolerance: int,
    location_threshold: float,
    limit: Optional[int],
    db_url: Optional[str],
    verbose: bool,
):
    """
    Find matching incidents across data sources

    Identifies potential duplicate incidents across different data sources
    using IMO number, vessel name similarity, and location/date proximity.

    Examples:
        marine-safety correlate find-matches
        marine-safety correlate find-matches --source ntsb --min-confidence 0.8
        marine-safety correlate find-matches --date-tolerance 5 --verbose
    """
    try:
        from worldenergydata.modules.marine_safety.analysis.correlation import (
            IncidentDeduplicator,
            MatchConfig,
        )
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )

        if verbose:
            console.print(f"[dim]Source filter: {source}[/dim]")
            console.print(f"[dim]Min confidence: {min_confidence}[/dim]")
            console.print(f"[dim]Date tolerance: {date_tolerance} days[/dim]")
            console.print(f"[dim]Location threshold: {location_threshold} km[/dim]")

        # Configure matcher
        config = MatchConfig(
            min_confidence=min_confidence,
            date_tolerance_days=date_tolerance,
            location_threshold_km=location_threshold,
        )

        # Get database session
        session = get_session(db_url)

        # Initialize deduplicator
        deduplicator = IncidentDeduplicator(session=session, config=config)

        with create_progress_spinner("Matching") as progress:
            task = progress.add_task(
                "[cyan]Finding cross-source matches...", total=None
            )

            # Find matches
            matches = list(deduplicator.find_cross_source_matches())

            progress.update(task, completed=True)

        # Display results
        if not matches:
            console.print(
                "\n[yellow]No matches found above confidence threshold[/yellow]"
            )
            return

        console.print(f"\n[green]Found {len(matches)} potential matches[/green]\n")

        # Display match table
        table = Table(
            title="Cross-Source Matches", show_header=True, header_style="bold cyan"
        )
        table.add_column("Incident 1", style="dim")
        table.add_column("Incident 2", style="dim")
        table.add_column("Match Type")
        table.add_column("Confidence", justify="right")
        table.add_column("IMO", justify="center")
        table.add_column("Name", justify="center")
        table.add_column("Loc", justify="center")

        for match in matches[:50]:  # Show first 50
            table.add_row(
                match.incident_1_id[:20] if match.incident_1_id else "N/A",
                match.incident_2_id[:20] if match.incident_2_id else "N/A",
                match.match_type,
                f"{match.confidence:.2f}",
                "Y" if match.imo_score and match.imo_score > 0.5 else "N",
                "Y" if match.name_score and match.name_score > 0.5 else "N",
                "Y" if match.location_score and match.location_score > 0.5 else "N",
            )

        console.print(table)

        if len(matches) > 50:
            console.print(f"\n[dim]Showing 50 of {len(matches)} matches[/dim]")

        # Show summary stats
        metrics = deduplicator.calculate_quality_metrics(matches)
        if metrics:
            console.print("\n[bold]Quality Metrics:[/bold]")
            console.print(f"  Average confidence: {metrics.avg_confidence:.2f}")
            console.print(f"  High confidence (>0.9): {metrics.high_confidence_count}")
            console.print(
                f"  Medium confidence (0.7-0.9): {metrics.medium_confidence_count}"
            )

    except ImportError as e:
        console.print(f"[red]x Import Error:[/red] {str(e)}", style="bold")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


@correlate.command(name="link")
@click.argument("incident_id_1", type=str)
@click.argument("incident_id_2", type=str)
@click.option(
    "--confidence",
    type=float,
    default=1.0,
    help="Confidence score (default: 1.0 for manual links)",
)
@click.option(
    "--match-type",
    type=click.Choice(["manual", "imo", "name", "location", "combined"]),
    default="manual",
    help="Match type (default: manual)",
)
@click.option("--db-url", help="Database connection URL")
def link_incidents(
    incident_id_1: str,
    incident_id_2: str,
    confidence: float,
    match_type: str,
    db_url: Optional[str],
):
    """
    Manually link two incidents as related/duplicate

    Examples:
        marine-safety correlate link MAR22MA001 MO-2022-001
        marine-safety correlate link MAR22MA001 MO-2022-001 --match-type imo
    """
    try:
        from worldenergydata.modules.marine_safety.analysis.correlation import (
            IncidentDeduplicator,
        )
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )

        session = get_session(db_url)
        deduplicator = IncidentDeduplicator(session=session)

        # Create link
        link = deduplicator.link_incidents(
            incident_id_1, incident_id_2, match_type=match_type, confidence=confidence
        )

        if link:
            console.print("[green]v Linked incidents:[/green]")
            console.print(f"  {incident_id_1} <-> {incident_id_2}")
            console.print(f"  Confidence: {confidence:.2f}")
            console.print(f"  Match type: {match_type}")
        else:
            console.print("[yellow]Failed to create link (may already exist)[/yellow]")

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)


@correlate.command(name="stats")
@click.option("--db-url", help="Database connection URL")
@click.option("--verbose", is_flag=True, help="Show detailed statistics")
def correlation_stats(db_url: Optional[str], verbose: bool):
    """
    Display correlation statistics

    Examples:
        marine-safety correlate stats
        marine-safety correlate stats --verbose
    """
    try:
        from worldenergydata.modules.marine_safety.database.db_manager import (
            get_session,
        )
        from worldenergydata.modules.marine_safety.database.models import IncidentLink

        session = get_session(db_url)

        # Count links
        total_links = session.query(func.count(IncidentLink.link_id)).scalar() or 0
        verified_links = (
            session.query(func.count(IncidentLink.link_id))
            .filter(IncidentLink.verified == True)  # noqa: E712
            .scalar()
            or 0
        )

        # Count by match type
        type_counts = (
            session.query(IncidentLink.match_type, func.count(IncidentLink.link_id))
            .group_by(IncidentLink.match_type)
            .all()
        )

        # Confidence distribution
        avg_confidence = (
            session.query(func.avg(IncidentLink.confidence_score)).scalar() or 0
        )

        # Display
        table = Table(
            title="Correlation Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Total Links", str(total_links))
        table.add_row("Verified Links", str(verified_links))
        table.add_row("Avg Confidence", f"{float(avg_confidence):.2f}")

        if type_counts:
            table.add_row("", "")
            table.add_row("[bold]By Match Type[/bold]", "")
            for match_type, count in type_counts:
                table.add_row(f"  {match_type}", str(count))

        console.print(table)

    except Exception as e:
        console.print(f"[red]x Error:[/red] {str(e)}", style="bold")
        sys.exit(1)
