# ABOUTME: CLI commands for Landman module mineral ownership and lease data operations
# ABOUTME: Provides search, lookup, county-info, providers, and status commands

"""
Landman CLI Commands

Provides command-line interface for Landman module operations including
mineral ownership searches, lease record lookups, county clerk information,
and provider status.

Usage:
    worldenergydata landman <command> [options]

Examples:
    worldenergydata landman search --state TX --county MIDLAND
    worldenergydata landman lookup --state TX --county MIDLAND --document-number 12345
    worldenergydata landman county-info --state TX --county MIDLAND
    worldenergydata landman providers
    worldenergydata landman status --verbose
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize console
console = Console()

# Create Landman Typer app
app = typer.Typer(
    name="landman",
    help="Mineral ownership and lease data operations",
    no_args_is_help=True,
)


class RecordType(str, Enum):
    """Record type options for searches."""

    ownership = "ownership"
    leases = "leases"
    title = "title"
    deeds = "deeds"
    all = "all"


class OutputFormat(str, Enum):
    """Output format options."""

    table = "table"
    json = "json"
    csv = "csv"


@app.command()
def search(
    state: str = typer.Option(
        ..., "--state", "-s", help="2-letter US state code (e.g., TX, NM, OK)"
    ),
    county: str = typer.Option(
        ..., "--county", "-c", help="County name (e.g., MIDLAND, REEVES)"
    ),
    section: Optional[str] = typer.Option(
        None, "--section", help="Section number for legal description"
    ),
    township: Optional[str] = typer.Option(
        None, "--township", "-t", help="Township designation"
    ),
    range_: Optional[str] = typer.Option(
        None, "--range", "-r", help="Range designation"
    ),
    owner: Optional[str] = typer.Option(
        None, "--owner", "-o", help="Owner name to search"
    ),
    record_type: RecordType = typer.Option(
        RecordType.all, "--type", help="Type of records to search"
    ),
    provider: str = typer.Option(
        "auto", "--provider", "-p", help="Data provider to use (auto, county_records)"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format"
    ),
    output_file: Optional[Path] = typer.Option(
        None, "--output", help="Save results to file"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Search for mineral/lease records by location.

    Searches county records for mineral ownership, leases, and title documents
    based on location criteria (state, county, section-township-range).

    Examples:
        worldenergydata landman search --state TX --county MIDLAND
        worldenergydata landman search --state TX --county REEVES --owner "SMITH"
        worldenergydata landman search --state NM --county LEA --section 12 --township 24S --range 36E
        worldenergydata landman search --state TX --county MIDLAND --format json --output results.json
    """
    try:
        # Display search parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("State", state.upper())
        params_table.add_row("County", county.upper())
        if section:
            params_table.add_row("Section", section)
        if township:
            params_table.add_row("Township", township)
        if range_:
            params_table.add_row("Range", range_)
        if owner:
            params_table.add_row("Owner", owner)
        params_table.add_row("Record Type", record_type.value)
        params_table.add_row("Provider", provider)

        console.print(
            Panel(params_table, title="Search Parameters", border_style="cyan")
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Searching mineral/lease records...", total=100
            )

            try:
                from worldenergydata.landman.landman import Landman

                progress.update(
                    task, advance=10, description="[cyan]Loading Landman module..."
                )

                landman = Landman()

                # Build legal description if components provided
                legal_description = None
                if section or township or range_:
                    parts = []
                    if section:
                        parts.append(f"Section {section}")
                    if township:
                        parts.append(f"T{township}")
                    if range_:
                        parts.append(f"R{range_}")
                    legal_description = ", ".join(parts)

                progress.update(
                    task, advance=20, description="[cyan]Querying provider..."
                )

                # Perform search
                result = landman.search_ownership(
                    state=state.upper(),
                    county=county.upper(),
                    legal_description=legal_description,
                    owner_name=owner,
                    provider=provider,
                )

                progress.update(
                    task, advance=50, description="[cyan]Processing results..."
                )

                if verbose:
                    console.print(f"\n[dim]Search ID: {result.search_id}[/dim]")
                    console.print(f"[dim]Duration: {result.search_duration_ms}ms[/dim]")

                progress.update(
                    task, advance=20, description="[cyan]Formatting output..."
                )

                # Handle output
                if output_format == OutputFormat.json:
                    result_dict = result.to_dict()
                    if output_file:
                        with open(output_file, "w") as f:
                            json.dump(result_dict, f, indent=2, default=str)
                        console.print(f"[green]Results saved to {output_file}[/green]")
                    else:
                        console.print_json(data=result_dict)
                else:
                    # Display as table
                    _display_search_results(result, verbose)

                # Show warnings/errors
                if result.warnings:
                    for warning in result.warnings:
                        console.print(f"[yellow]Warning:[/yellow] {warning}")
                if result.errors:
                    for error in result.errors:
                        console.print(f"[red]Error:[/red] {error}")

                console.print(
                    f"\n[dim]Total records found: {result.total_records}[/dim]"
                )

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import Landman module: {e}"
                )
                console.print("[dim]Ensure all dependencies are installed.[/dim]")
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def lookup(
    state: str = typer.Option(..., "--state", "-s", help="2-letter US state code"),
    county: str = typer.Option(..., "--county", "-c", help="County name"),
    document_number: Optional[str] = typer.Option(
        None, "--document-number", "-d", help="Document/instrument number"
    ),
    book: Optional[str] = typer.Option(
        None, "--book", "-b", help="Recording book number"
    ),
    page: Optional[str] = typer.Option(
        None, "--page", "-p", help="Recording page number"
    ),
    legal_description: Optional[str] = typer.Option(
        None, "--legal-description", "-l", help="Full legal description"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Look up specific record by ID or legal description.

    Retrieves detailed information about a specific document using
    document number, book/page reference, or legal description.

    Examples:
        worldenergydata landman lookup --state TX --county MIDLAND --document-number 2024-12345
        worldenergydata landman lookup --state TX --county REEVES --book 123 --page 456
        worldenergydata landman lookup --state TX --county MIDLAND --legal-description "Section 12, T1S, R1E"
    """
    try:
        # Validate that at least one lookup method is provided
        if not any([document_number, (book and page), legal_description]):
            console.print(
                "[red]Error:[/red] Must provide --document-number, --book and --page, "
                "or --legal-description"
            )
            raise typer.Exit(1)

        # Display lookup parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("State", state.upper())
        params_table.add_row("County", county.upper())
        if document_number:
            params_table.add_row("Document Number", document_number)
        if book:
            params_table.add_row("Book", book)
        if page:
            params_table.add_row("Page", page)
        if legal_description:
            params_table.add_row("Legal Description", legal_description)

        console.print(
            Panel(params_table, title="Lookup Parameters", border_style="cyan")
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Looking up record...", total=100)

            try:
                from worldenergydata.landman.landman import Landman

                progress.update(
                    task, advance=20, description="[cyan]Loading Landman module..."
                )

                landman = Landman()

                progress.update(
                    task, advance=30, description="[cyan]Querying records..."
                )

                # Build search criteria for title records
                records = landman.get_title_records(
                    state=state.upper(),
                    county=county.upper(),
                    document_number=document_number,
                    legal_description=legal_description,
                )

                progress.update(
                    task, advance=50, description="[cyan]Processing results..."
                )

                if not records:
                    console.print("[yellow]No records found matching criteria[/yellow]")
                    raise typer.Exit(0)

                # Display results
                if output_format == OutputFormat.json:
                    result_list = [r.to_dict() for r in records]
                    console.print_json(data=result_list)
                else:
                    _display_title_records(records, verbose)

                console.print(f"\n[dim]Records found: {len(records)}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import Landman module: {e}"
                )
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command("county-info")
def county_info(
    state: str = typer.Option(..., "--state", "-s", help="2-letter US state code"),
    county: str = typer.Option(..., "--county", "-c", help="County name"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format"
    ),
    show_instructions: bool = typer.Option(
        False, "--instructions", "-i", help="Show detailed search instructions"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Get county clerk office information for a state/county.

    Retrieves contact information, office hours, and online search
    availability for a county clerk's office.

    Examples:
        worldenergydata landman county-info --state TX --county MIDLAND
        worldenergydata landman county-info --state NM --county LEA --instructions
        worldenergydata landman county-info --state TX --county REEVES --format json
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Retrieving county information...", total=100
            )

            try:
                from worldenergydata.landman.exceptions import (
                    CountyNotFoundError,
                    StateNotSupportedError,
                )
                from worldenergydata.landman.providers.county_reference import (
                    CountyReferenceProvider,
                )

                progress.update(
                    task, advance=30, description="[cyan]Loading provider..."
                )

                provider = CountyReferenceProvider()

                progress.update(
                    task, advance=40, description="[cyan]Fetching county data..."
                )

                try:
                    info = provider.get_county_clerk_info(state.upper(), county.upper())
                except StateNotSupportedError as e:
                    progress.update(task, completed=100)
                    console.print(f"[red]Error:[/red] {e.message}")
                    console.print(
                        f"[dim]Supported states: {', '.join(provider.SUPPORTED_STATES)}[/dim]"
                    )
                    raise typer.Exit(1)
                except CountyNotFoundError as e:
                    progress.update(task, completed=100)
                    console.print(f"[red]Error:[/red] {e.message}")
                    available_counties = provider.get_counties_for_state(state.upper())
                    if available_counties:
                        console.print(
                            f"[dim]Available counties in {state.upper()}: "
                            f"{', '.join(available_counties)}[/dim]"
                        )
                    raise typer.Exit(1)

                progress.update(
                    task, advance=30, description="[cyan]Formatting output..."
                )

                # Display results
                if output_format == OutputFormat.json:
                    console.print_json(data=info.to_dict())
                else:
                    _display_county_info(info)

                # Show search instructions if requested
                if show_instructions:
                    instructions = provider.get_search_instructions(
                        state.upper(), county.upper()
                    )
                    console.print("\n")
                    console.print(
                        Panel(
                            instructions,
                            title="Search Instructions",
                            border_style="blue",
                        )
                    )

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import provider: {e}"
                )
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def providers(
    state: Optional[str] = typer.Option(
        None, "--state", "-s", help="Filter by state code"
    ),
    online_only: bool = typer.Option(
        False, "--online-only", help="Show only counties with online search"
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--format", "-f", help="Output format"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    List available data providers and their coverage.

    Displays information about available data providers, supported states,
    and counties with reference data in the system.

    Examples:
        worldenergydata landman providers
        worldenergydata landman providers --state TX
        worldenergydata landman providers --online-only
        worldenergydata landman providers --format json
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading provider information...", total=100)

            try:
                from worldenergydata.landman.landman import Landman
                from worldenergydata.landman.providers.county_reference import (
                    CountyReferenceProvider,
                )

                progress.update(
                    task, advance=30, description="[cyan]Gathering provider data..."
                )

                landman = Landman()
                county_ref = CountyReferenceProvider()

                progress.update(task, advance=40, description="[cyan]Processing...")

                # Get provider information
                valid_providers = landman.get_valid_providers()
                valid_data_types = landman.get_valid_data_types()
                supported_states = county_ref.get_supported_states()

                progress.update(
                    task, advance=30, description="[cyan]Formatting output..."
                )

                if output_format == OutputFormat.json:
                    # Get county data
                    counties = county_ref.search_counties(
                        state=state, online_only=online_only
                    )
                    result = {
                        "providers": valid_providers,
                        "data_types": valid_data_types,
                        "supported_states": supported_states,
                        "counties": [c.to_dict() for c in counties],
                    }
                    console.print_json(data=result)
                else:
                    # Display providers table
                    providers_table = Table(
                        title="Available Providers",
                        show_header=True,
                        header_style="bold cyan",
                    )
                    providers_table.add_column("Provider")
                    providers_table.add_column("Description")
                    providers_table.add_column("Status")

                    provider_descriptions = {
                        "county_records": "Public county clerk records",
                        "drillinginfo": "Enverus/DrillingInfo (subscription)",
                        "txdir": "Texas Direct (subscription)",
                        "ogorgs": "Oil & Gas OGS",
                        "auto": "Auto-select best available",
                    }

                    for prov in valid_providers:
                        desc = provider_descriptions.get(prov, "Data provider")
                        if prov in ["county_records", "auto"]:
                            status = "[green]Available[/green]"
                        else:
                            status = "[yellow]Subscription Required[/yellow]"
                        providers_table.add_row(prov, desc, status)

                    console.print(providers_table)

                    # Display supported states
                    console.print(f"\n[bold]Supported States:[/bold]")
                    console.print(f"[dim]{', '.join(supported_states)}[/dim]")

                    # Display data types
                    console.print(f"\n[bold]Available Data Types:[/bold]")
                    console.print(f"[dim]{', '.join(valid_data_types)}[/dim]")

                    # Display counties with reference data
                    counties = county_ref.search_counties(
                        state=state, online_only=online_only
                    )

                    if counties:
                        console.print("\n")
                        county_table = Table(
                            title="County Reference Data",
                            show_header=True,
                            header_style="bold cyan",
                        )
                        county_table.add_column("State")
                        county_table.add_column("County")
                        county_table.add_column("Online Search")
                        if verbose:
                            county_table.add_column("Phone")
                            county_table.add_column("Website")

                        for c in counties:
                            online = (
                                "[green]Yes[/green]"
                                if c.online_search_available
                                else "[yellow]No[/yellow]"
                            )
                            if verbose:
                                county_table.add_row(
                                    c.state,
                                    c.county,
                                    online,
                                    c.phone or "-",
                                    c.website or "-",
                                )
                            else:
                                county_table.add_row(c.state, c.county, online)

                        console.print(county_table)
                        console.print(
                            f"\n[dim]Total counties with reference data: {len(counties)}[/dim]"
                        )

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import Landman module: {e}"
                )
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def status(
    data_path: Path = typer.Option(
        Path("./data/landman"),
        "--data-path",
        "-d",
        help="Path to Landman data directory",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed status information"
    ),
) -> None:
    """
    Show module status, cache info, and provider availability.

    Displays information about the Landman module status including
    cached data, provider availability, and system health.

    Examples:
        worldenergydata landman status
        worldenergydata landman status --verbose
        worldenergydata landman status --data-path ./custom/path
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Loading Landman status...", total=100)

            status_data = {
                "module_loaded": False,
                "providers_available": [],
                "supported_states": [],
                "data_files": 0,
                "data_size_mb": 0,
                "last_updated": "Unknown",
                "cache_status": "Not initialized",
            }

            progress.update(
                task, advance=30, description="[cyan]Checking module status..."
            )

            # Try to load module
            try:
                from worldenergydata.landman.landman import Landman
                from worldenergydata.landman.providers.county_reference import (
                    CountyReferenceProvider,
                )

                landman = Landman()
                county_ref = CountyReferenceProvider()

                status_data["module_loaded"] = True
                status_data["providers_available"] = landman.get_valid_providers()
                status_data["supported_states"] = county_ref.get_supported_states()
                status_data["data_types"] = landman.get_valid_data_types()

                # Check provider health
                if county_ref.health_check():
                    status_data["cache_status"] = "Available"

            except ImportError as e:
                status_data["import_error"] = str(e)

            progress.update(
                task, advance=30, description="[cyan]Checking data directories..."
            )

            # Check data directory
            if data_path.exists():
                total_files = 0
                total_size = 0

                for f in data_path.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_size += f.stat().st_size

                        # Get most recent modification time
                        mtime = datetime.fromtimestamp(f.stat().st_mtime)
                        if status_data["last_updated"] == "Unknown":
                            status_data["last_updated"] = mtime.isoformat()
                        else:
                            existing = datetime.fromisoformat(
                                status_data["last_updated"]
                            )
                            if mtime > existing:
                                status_data["last_updated"] = mtime.isoformat()

                status_data["data_files"] = total_files
                status_data["data_size_mb"] = total_size / (1024 * 1024)

            progress.update(task, advance=40, description="[cyan]Formatting results...")

        # Create status table
        table = Table(
            title="Landman Module Status", show_header=True, header_style="bold cyan"
        )
        table.add_column("Component", style="dim")
        table.add_column("Status")
        table.add_column("Details", justify="right")

        # Module status
        if status_data["module_loaded"]:
            table.add_row(
                "Module", "[green]Loaded[/green]", "worldenergydata.landman"
            )
        else:
            table.add_row(
                "Module",
                "[red]Not Loaded[/red]",
                status_data.get("import_error", "Import error"),
            )

        # Provider status
        providers_count = len(status_data.get("providers_available", []))
        table.add_row(
            "Providers",
            (
                "[green]Available[/green]"
                if providers_count > 0
                else "[yellow]None[/yellow]"
            ),
            f"{providers_count} providers",
        )

        # Supported states
        states_count = len(status_data.get("supported_states", []))
        table.add_row(
            "Supported States",
            (
                "[green]Configured[/green]"
                if states_count > 0
                else "[yellow]None[/yellow]"
            ),
            f"{states_count} states",
        )

        # Cache status
        table.add_row(
            "Reference Data",
            f"[green]{status_data['cache_status']}[/green]",
            "County clerk info",
        )

        table.add_row("", "", "")

        # Data directory status
        if status_data["data_files"] > 0:
            table.add_row("Data Files", f"{status_data['data_files']:,}", "")
            table.add_row("Data Size", f"{status_data['data_size_mb']:.2f} MB", "")
            table.add_row(
                "Last Updated",
                (
                    status_data["last_updated"][:19]
                    if status_data["last_updated"] != "Unknown"
                    else "Unknown"
                ),
                "",
            )
        else:
            table.add_row("Data Files", "[yellow]No data files found[/yellow]", "")

        table.add_row("Data Directory", str(data_path), "")

        console.print(table)

        # Show detailed provider info if verbose
        if verbose and status_data.get("providers_available"):
            console.print("\n")
            providers_table = Table(
                title="Available Providers", show_header=True, header_style="bold cyan"
            )
            providers_table.add_column("Provider")
            providers_table.add_column("Type")
            providers_table.add_column("Status")

            for prov in status_data["providers_available"]:
                if prov in ["county_records", "auto"]:
                    providers_table.add_row(prov, "Free", "[green]Ready[/green]")
                else:
                    providers_table.add_row(
                        prov, "Subscription", "[yellow]Requires API Key[/yellow]"
                    )

            console.print(providers_table)

        # Show supported states if verbose
        if verbose and status_data.get("supported_states"):
            console.print(f"\n[bold]Supported States:[/bold]")
            console.print(f"[dim]{', '.join(status_data['supported_states'])}[/dim]")

        # Show data types if verbose
        if verbose and status_data.get("data_types"):
            console.print(f"\n[bold]Available Data Types:[/bold]")
            console.print(f"[dim]{', '.join(status_data['data_types'])}[/dim]")

        console.print(
            "\n[dim]Use 'worldenergydata landman search' to search records[/dim]"
        )
        console.print(
            "[dim]Use 'worldenergydata landman county-info' to get county details[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.callback()
def callback() -> None:
    """
    Mineral ownership and lease data operations.

    Access mineral ownership records, lease data, and county clerk
    information for oil and gas producing regions across the United States.
    """
    pass


def _display_search_results(result, verbose: bool = False) -> None:
    """Display search results in table format."""
    from worldenergydata.landman.models import OwnerSearchResult

    if isinstance(result, OwnerSearchResult):
        # Display ownership records
        if result.ownership_records:
            ownership_table = Table(
                title="Ownership Records",
                show_header=True,
                header_style="bold cyan",
            )
            ownership_table.add_column("Owner")
            ownership_table.add_column("Interest Type")
            ownership_table.add_column("Interest %", justify="right")
            ownership_table.add_column("Net Acres", justify="right")
            ownership_table.add_column("Legal Description")

            for record in result.ownership_records:
                ownership_table.add_row(
                    record.owner_name,
                    record.interest_type.value if record.interest_type else "-",
                    (
                        f"{record.mineral_interest_percent:.2f}%"
                        if record.mineral_interest_percent
                        else "-"
                    ),
                    (
                        f"{record.net_mineral_acres:.2f}"
                        if record.net_mineral_acres
                        else "-"
                    ),
                    (
                        record.legal_description[:40] + "..."
                        if len(record.legal_description) > 40
                        else record.legal_description
                    ),
                )

            console.print(ownership_table)

        # Display lease records
        if result.lease_records:
            lease_table = Table(
                title="Lease Records",
                show_header=True,
                header_style="bold cyan",
            )
            lease_table.add_column("Lessor")
            lease_table.add_column("Lessee")
            lease_table.add_column("Status")
            lease_table.add_column("Royalty", justify="right")
            lease_table.add_column("Acres", justify="right")

            for record in result.lease_records:
                lease_table.add_row(
                    record.lessor,
                    record.lessee,
                    record.status.value if record.status else "-",
                    f"{record.royalty_rate:.4f}" if record.royalty_rate else "-",
                    f"{record.gross_acres:.2f}" if record.gross_acres else "-",
                )

            console.print(lease_table)

        # Display title records
        if result.title_records:
            title_table = Table(
                title="Title Records",
                show_header=True,
                header_style="bold cyan",
            )
            title_table.add_column("Type")
            title_table.add_column("Grantor")
            title_table.add_column("Grantee")
            title_table.add_column("Recorded")
            title_table.add_column("Instrument #")

            for record in result.title_records:
                title_table.add_row(
                    record.record_type.value if record.record_type else "-",
                    record.grantor,
                    record.grantee,
                    record.recorded_date.isoformat() if record.recorded_date else "-",
                    record.instrument_number or "-",
                )

            console.print(title_table)


def _display_title_records(records, verbose: bool = False) -> None:
    """Display title records in table format."""
    table = Table(
        title="Title/Deed Records",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Document ID")
    table.add_column("Type")
    table.add_column("Grantor")
    table.add_column("Grantee")
    table.add_column("Recorded Date")
    if verbose:
        table.add_column("Legal Description")
        table.add_column("Consideration")

    for record in records:
        if verbose:
            table.add_row(
                record.document_id,
                record.record_type.value if record.record_type else "-",
                record.grantor,
                record.grantee,
                record.recorded_date.isoformat() if record.recorded_date else "-",
                (
                    record.legal_description[:30] + "..."
                    if len(record.legal_description) > 30
                    else record.legal_description
                ),
                f"${record.consideration:,.2f}" if record.consideration else "-",
            )
        else:
            table.add_row(
                record.document_id,
                record.record_type.value if record.record_type else "-",
                record.grantor,
                record.grantee,
                record.recorded_date.isoformat() if record.recorded_date else "-",
            )

    console.print(table)


def _display_county_info(info) -> None:
    """Display county clerk information in formatted panel."""
    from worldenergydata.landman.models import CountyClerkInfo

    if isinstance(info, CountyClerkInfo):
        lines = []
        lines.append(f"[bold]{info.office_name or 'County Clerk'}[/bold]")
        lines.append(f"{info.county} County, {info.state}")
        lines.append("")

        if info.address:
            lines.append(f"[dim]Address:[/dim]")
            lines.append(f"  {info.address}")
            if info.city and info.zip_code:
                lines.append(f"  {info.city}, {info.state} {info.zip_code}")
            lines.append("")

        if info.phone:
            lines.append(f"[dim]Phone:[/dim] {info.phone}")
        if info.fax:
            lines.append(f"[dim]Fax:[/dim] {info.fax}")
        if info.email:
            lines.append(f"[dim]Email:[/dim] {info.email}")

        if info.office_hours:
            lines.append(f"[dim]Hours:[/dim] {info.office_hours}")

        lines.append("")

        if info.website:
            lines.append(f"[dim]Website:[/dim] {info.website}")
        if info.online_search_url:
            lines.append(f"[dim]Online Search:[/dim] {info.online_search_url}")

        online_status = (
            "[green]Available[/green]"
            if info.online_search_available
            else "[yellow]Not Available[/yellow]"
        )
        lines.append(f"[dim]Online Search Status:[/dim] {online_status}")

        if info.notes:
            lines.append("")
            lines.append(f"[dim]Notes:[/dim] {info.notes}")

        console.print(
            Panel(
                "\n".join(lines),
                title="County Clerk Information",
                border_style="cyan",
            )
        )
