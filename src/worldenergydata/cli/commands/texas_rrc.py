# ABOUTME: CLI commands for Texas Railroad Commission data operations
# ABOUTME: Provides collect, analyze, and status commands for Texas oil/gas data

"""
Texas RRC CLI Commands

Provides command-line interface for Texas Railroad Commission (RRC)
data operations including data collection, analysis, and validation.

Usage:
    worldenergydata texas-rrc <command> [options]

Examples:
    worldenergydata texas-rrc collect --types production wells
    worldenergydata texas-rrc analyze --district 08
    worldenergydata texas-rrc status --verbose
    worldenergydata texas-rrc validate-api 42-123-12345
"""

from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Initialize console
console = Console()

# Create Texas RRC Typer app
app = typer.Typer(
    name="texas-rrc",
    help="Texas Railroad Commission oil & gas data operations",
    no_args_is_help=True,
)


class DataType(str, Enum):
    """Data type options for collection."""

    production = "production"
    wells = "wells"
    permits = "permits"
    completions = "completions"
    drilling = "drilling"
    all = "all"


class OutputFormat(str, Enum):
    """Output format options."""

    json = "json"
    parquet = "parquet"
    csv = "csv"
    excel = "excel"


# Valid RRC districts
VALID_DISTRICTS = [
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "7B",
    "7C",
    "08",
    "8A",
    "09",
    "10",
]


@app.command()
def collect(
    data_types: List[DataType] = typer.Option(
        [DataType.production],
        "--types",
        "-t",
        help="Data types: production, wells, permits, completions, drilling, all",
    ),
    districts: Optional[List[str]] = typer.Option(
        None,
        "--districts",
        "-d",
        help="RRC districts: 01-10, 7B, 7C, 8A (omit for all districts)",
    ),
    output: Path = typer.Option(
        Path("./data/texas_rrc"),
        "--output",
        "-o",
        help="Output directory for collected data",
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.csv, "--format", "-f", help="Output format for collected data"
    ),
    start_date: Optional[str] = typer.Option(
        None, "--start-date", help="Start date for data collection (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(
        None, "--end-date", help="End date for data collection (YYYY-MM-DD)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Collect data from Texas RRC.

    Downloads oil and gas data from the Texas Railroad Commission
    for the specified data types and districts.

    Examples:
        worldenergydata texas-rrc collect --types production
        worldenergydata texas-rrc collect --types wells permits --districts 08 8A
        worldenergydata texas-rrc collect --types all --format csv
    """
    try:
        # Validate districts
        if districts:
            for d in districts:
                if d.upper() not in [x.upper() for x in VALID_DISTRICTS]:
                    console.print(f"[red]Error:[/red] Invalid district '{d}'")
                    console.print(
                        f"[dim]Valid districts: {', '.join(VALID_DISTRICTS)}[/dim]"
                    )
                    raise typer.Exit(1)

        # Convert 'all' to all data types
        types_to_collect = []
        for t in data_types:
            if t == DataType.all:
                types_to_collect = [
                    DataType.production.value,
                    DataType.wells.value,
                    DataType.permits.value,
                    DataType.completions.value,
                    DataType.drilling.value,
                ]
                break
            else:
                types_to_collect.append(t.value)

        # Display collection parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        params_table.add_row("Data Types", ", ".join(types_to_collect))
        params_table.add_row("Districts", ", ".join(districts) if districts else "All")
        params_table.add_row("Output Directory", str(output))
        params_table.add_row("Output Format", format.value)
        if start_date:
            params_table.add_row("Start Date", start_date)
        if end_date:
            params_table.add_row("End Date", end_date)

        console.print(
            Panel(params_table, title="Collection Parameters", border_style="cyan")
        )

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Initializing Texas RRC data collection...", total=100
            )

            try:
                from worldenergydata.texas_rrc.texas_rrc import TexasRRC

                progress.update(
                    task, advance=10, description="[cyan]Loading Texas RRC module..."
                )

                # Build configuration
                cfg = {
                    "basename": "texas_rrc",
                    "module": "texas_rrc",
                    "data_types": types_to_collect,
                    "districts": districts or VALID_DISTRICTS,
                    "output": {
                        "directory": str(output),
                        "format": format.value,
                    },
                    "date_range": {
                        "start": start_date,
                        "end": end_date,
                    },
                }

                progress.update(
                    task, advance=20, description="[cyan]Connecting to Texas RRC..."
                )

                # Run the collection through Texas RRC router
                texas_rrc = TexasRRC()
                result_cfg = texas_rrc.router(cfg)

                progress.update(
                    task, advance=50, description="[cyan]Processing data..."
                )

                collected = result_cfg.get("texas_rrc", {}).get("data_collected", [])

                progress.update(
                    task, advance=20, description="[cyan]Completing collection..."
                )

                if verbose:
                    console.print(f"\n[dim]Configuration result: {result_cfg}[/dim]")

                # Create results table
                results_table = Table(
                    title="Collection Results",
                    show_header=True,
                    header_style="bold cyan",
                )
                results_table.add_column("Data Type", style="dim")
                results_table.add_column("Status")
                results_table.add_column("Records", justify="right")

                for dt in types_to_collect:
                    if dt in collected:
                        results_table.add_row(
                            dt, "[green]Collected[/green]", "See output"
                        )
                    else:
                        results_table.add_row(dt, "[yellow]Pending[/yellow]", "-")

                console.print(results_table)
                console.print("\n[green]Data collection completed successfully[/green]")
                console.print(f"[dim]Data saved to: {output}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import Texas RRC module: {e}"
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


def _print_refresh_plans(plans) -> None:
    table = Table(
        title="Texas RRC Raw Refresh Sources",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Source", style="dim", no_wrap=True)
    table.add_column("Strategy", no_wrap=True)
    table.add_column("Status")
    table.add_column("Target", overflow="fold")

    for plan in plans:
        status = "planned" if plan.refreshable else plan.skip_reason or "skipped"
        table.add_row(
            plan.source_id,
            plan.download_strategy,
            status,
            str(plan.target_path),
        )

    console.print(table)


def _print_directory_refresh_plans(plans) -> None:
    table = Table(
        title="Texas RRC GoDrive Directory Refresh",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Source", style="dim", no_wrap=True)
    table.add_column("Rows", justify="right")
    table.add_column("Selected", justify="right")
    table.add_column("Files", overflow="fold")

    for plan in plans:
        table.add_row(
            plan.source_id,
            str(plan.row_count),
            str(len(plan.selected_files)),
            ", ".join(file.filename for file in plan.selected_files),
        )

    console.print(table)


def _validate_refresh_selection(
    source: Optional[List[str]],
    all_sources: bool,
) -> None:
    if source and all_sources:
        console.print("[red]Error:[/red] Use either --source or --all, not both")
        raise typer.Exit(1)
    if not source and not all_sources:
        console.print("[red]Error:[/red] Use --source, --all, or --list-sources")
        raise typer.Exit(1)


def _execute_refresh_plans(refresher, plans, explicit_sources: bool) -> None:
    refreshed = []
    for plan in plans:
        if not plan.refreshable:
            if explicit_sources:
                console.print(
                    f"[red]Error:[/red] {plan.source_id} is not refreshable: "
                    f"{plan.skip_reason}"
                )
                raise typer.Exit(1)
            continue
        refreshed.append(refresher.refresh_source(plan.source_id))

    if not refreshed:
        console.print(
            "[yellow]No refreshable direct-source snapshots selected[/yellow]"
        )
        return

    for manifest in refreshed:
        console.print(
            f"[green]Downloaded[/green] {manifest.source_id}: "
            f"{manifest.byte_size} bytes -> {manifest.raw_path}"
        )


def _is_directory_source(refresher, source_id: str) -> bool:
    return (
        refresher.catalog[source_id]["download_strategy"]
        == "official_godrive_directory"
    )


def _validate_directory_options(
    refresher, source_ids, since_date, through_date
) -> None:
    if not (since_date or through_date):
        return
    if any(not _is_directory_source(refresher, source_id) for source_id in source_ids):
        console.print(
            "[red]Error:[/red] date-window options only apply to directory sources"
        )
        raise typer.Exit(1)
    if any(
        refresher.catalog[source_id].get("directory_refresh_policy") == "all_files"
        for source_id in source_ids
    ):
        console.print(
            "[red]Error:[/red] date-window options only apply to dated directory "
            "sources"
        )
        raise typer.Exit(1)


def _parse_refresh_date(value: str | None, option_name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        console.print(f"[red]Error:[/red] {option_name} must use YYYY-MM-DD")
        raise typer.Exit(1) from None


def _normalize_selection_mode(selection: str) -> str:
    mode = selection.replace("-", "_")
    if mode not in {"catalog_default", "latest", "all"}:
        console.print(
            "[red]Error:[/red] selection must be one of: catalog_default, latest, all"
        )
        raise typer.Exit(1)
    return mode


def _validate_rows_per_page(rows_per_page: int) -> None:
    if rows_per_page < 1:
        console.print("[red]Error:[/red] --rows-per-page must be at least 1")
        raise typer.Exit(1)


@app.command()
def refresh(
    source: Optional[List[str]] = typer.Option(
        None,
        "--source",
        "-s",
        help="Source ID to refresh; repeat for multiple sources",
    ),
    all_sources: bool = typer.Option(
        False,
        "--all",
        help="Refresh every direct-source catalog entry",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Plan refresh actions without downloading data",
    ),
    list_sources: bool = typer.Option(
        False,
        "--list-sources",
        help="List configured Texas RRC refresh sources",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Raw data output root",
    ),
    since_date: Optional[str] = typer.Option(
        None,
        "--since-date",
        help="First filename date to include for directory sources",
    ),
    through_date: Optional[str] = typer.Option(
        None,
        "--through-date",
        help="Last filename date to include for directory sources",
    ),
    selection: str = typer.Option(
        "catalog_default",
        "--selection",
        help="Directory selection: catalog_default, latest, or all",
    ),
    rows_per_page: int = typer.Option(
        1000,
        "--rows-per-page",
        help="GoDrive directory rows requested per page",
    ),
) -> None:
    """Refresh official Texas RRC raw snapshots into the /mnt/ace contract."""
    from worldenergydata.texas_rrc.raw_refresh import (
        DirectorySelection,
        RawSnapshotRefresher,
    )

    selection = _normalize_selection_mode(selection)
    _validate_rows_per_page(rows_per_page)
    refresher = RawSnapshotRefresher(output_root=output_root)

    if list_sources:
        _print_refresh_plans(refresher.plan_sources())
        return

    _validate_refresh_selection(source, all_sources)
    source_ids = source if source else sorted(refresher.catalog)
    _validate_directory_options(refresher, source_ids, since_date, through_date)
    directory_selection = DirectorySelection(
        since_date=_parse_refresh_date(since_date, "--since-date"),
        through_date=_parse_refresh_date(through_date, "--through-date"),
        mode=selection,
    )

    if source and any(_is_directory_source(refresher, item) for item in source):
        directory_source_ids = [
            item for item in source if _is_directory_source(refresher, item)
        ]
        file_source_ids = [
            item for item in source if not _is_directory_source(refresher, item)
        ]
        directory_plans = [
            refresher.discover_directory_source(
                item, directory_selection, rows_per_page
            )
            for item in directory_source_ids
        ]
        file_plans = refresher.plan_sources(file_source_ids) if file_source_ids else []
        if dry_run:
            _print_directory_refresh_plans(directory_plans)
            if file_plans:
                _print_refresh_plans(file_plans)
            return
        for plan in directory_plans:
            manifest = refresher.refresh_source(
                plan.source_id,
                directory_selection,
                rows_per_page,
            )
            console.print(
                f"[green]Downloaded[/green] {manifest.source_id}: "
                f"{manifest.byte_size} bytes -> {manifest.raw_path}"
            )
        if file_plans:
            _execute_refresh_plans(refresher, file_plans, explicit_sources=True)
        return

    plans = refresher.plan_sources(source_ids if source else None)
    if dry_run:
        _print_refresh_plans(plans)
        return

    _execute_refresh_plans(refresher, plans, explicit_sources=bool(source))


def _lifecycle_input_paths(raw_root: Path) -> list[str]:
    raw_path = raw_root / "raw"
    if not raw_path.exists():
        return []
    return [
        str(path.relative_to(raw_root))
        for path in sorted(raw_path.rglob("*"))
        if path.is_file()
    ]


def _print_lifecycle_summary(row_count: int, source_gaps) -> None:
    table = Table(
        title="Texas RRC Lifecycle Normalization",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Lifecycle rows", str(row_count))
    table.add_row("Source gaps", ", ".join(source_gaps) if source_gaps else "None")
    console.print(table)


@app.command("normalize-lifecycle")
def normalize_lifecycle(
    raw_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--raw-root",
        help="Root containing Texas RRC raw lifecycle snapshots",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Root for curated lifecycle outputs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build the lifecycle spine summary without writing curated outputs",
    ),
    require_sources: bool = typer.Option(
        False,
        "--require-sources",
        help="Fail when any lifecycle source directory is missing or empty",
    ),
    allow_non_ace_output: bool = typer.Option(
        False,
        "--allow-non-ace-output",
        help="Allow non-/mnt/ace output roots for isolated tests or sandboxes",
    ),
) -> None:
    """Normalize local official Texas RRC raw snapshots into a lifecycle spine."""
    from worldenergydata.texas_rrc.lifecycle.io import write_lifecycle_outputs
    from worldenergydata.texas_rrc.lifecycle.quality import assess_lifecycle_quality
    from worldenergydata.texas_rrc.lifecycle.sources import load_lifecycle_inputs
    from worldenergydata.texas_rrc.lifecycle.spine import build_lifecycle_spine

    try:
        inputs = load_lifecycle_inputs(raw_root)
        if require_sources and inputs.source_gaps:
            console.print(
                "[red]Error:[/red] missing lifecycle sources: "
                f"{', '.join(inputs.source_gaps)}"
            )
            raise typer.Exit(1)

        spine = build_lifecycle_spine(inputs)
        quality = assess_lifecycle_quality(spine, source_gaps=inputs.source_gaps)
        _print_lifecycle_summary(len(spine), inputs.source_gaps)

        if dry_run:
            console.print("[yellow]Dry run:[/yellow] no lifecycle outputs written")
            return

        manifest = write_lifecycle_outputs(
            spine,
            quality,
            output_root=output_root,
            input_paths=_lifecycle_input_paths(raw_root),
            allow_non_ace_root=allow_non_ace_output,
        )
        console.print(
            "[green]Wrote lifecycle spine[/green] "
            f"{manifest.row_count} rows -> {manifest.spine_path}"
        )
        console.print(f"[dim]Quality report: {manifest.quality_path}[/dim]")
        console.print(f"[dim]Manifest: {manifest.manifest_path}[/dim]")
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


def _print_production_atlas_summary(row_count: int, source_gaps) -> None:
    table = Table(
        title="Texas RRC Production Field Atlas",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Production atlas rows", str(row_count))
    table.add_row("Source gaps", ", ".join(source_gaps) if source_gaps else "None")
    console.print(table)


def _print_production_atlas_outputs(manifest) -> None:
    console.print(
        "[green]Wrote production atlas[/green] "
        f"{manifest.row_count} rows -> {manifest.csv_path}"
    )
    console.print(f"[dim]Parquet: {manifest.parquet_path}[/dim]")
    console.print(f"[dim]Quality report: {manifest.quality_path}[/dim]")
    console.print(f"[dim]Manifest: {manifest.manifest_path}[/dim]")


def _run_build_production_atlas(
    raw_root: Path,
    output_root: Path,
    dry_run: bool,
    require_sources: bool,
    allow_non_ace_output: bool,
    chunksize: int,
) -> None:
    from worldenergydata.texas_rrc.production_atlas import atlas as atlas_mod
    from worldenergydata.texas_rrc.production_atlas import io as atlas_io
    from worldenergydata.texas_rrc.production_atlas import sources as atlas_sources

    inputs = atlas_sources.iter_production_input_chunks(raw_root, chunksize=chunksize)
    source_gaps = tuple(inputs.source_gaps)
    if source_gaps and (require_sources or not dry_run):
        console.print(
            "[red]Error:[/red] missing production sources: " f"{', '.join(source_gaps)}"
        )
        raise typer.Exit(1)

    atlas = atlas_mod.build_production_atlas_from_chunks(inputs.chunks)
    if atlas.empty and not source_gaps:
        source_gaps = ("production_pdq",)
    if source_gaps and (require_sources or not dry_run):
        console.print(
            "[red]Error:[/red] missing production sources: " f"{', '.join(source_gaps)}"
        )
        raise typer.Exit(1)

    _print_production_atlas_summary(len(atlas), source_gaps)
    if dry_run:
        console.print("[yellow]Dry run:[/yellow] no production atlas outputs written")
        return

    manifest = atlas_io.write_production_atlas_outputs(
        atlas,
        output_root=output_root,
        input_paths=inputs.input_paths,
        source_gaps=source_gaps,
        allow_non_ace_root=allow_non_ace_output,
        command=(
            "worldenergydata texas-rrc build-production-atlas "
            f"--raw-root {raw_root} --output-root {output_root} "
            f"--chunksize {chunksize}"
        ),
    )
    _print_production_atlas_outputs(manifest)


@app.command("build-production-atlas")
def build_production_atlas_command(
    raw_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--raw-root",
        help="Root containing Texas RRC raw PDQ production snapshots",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Root for curated production atlas outputs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build the production atlas summary without writing curated outputs",
    ),
    require_sources: bool = typer.Option(
        False,
        "--require-sources",
        help="Fail when the production PDQ source directory is missing or empty",
    ),
    allow_non_ace_output: bool = typer.Option(
        False,
        "--allow-non-ace-output",
        help="Allow non-/mnt/ace output roots for isolated tests or sandboxes",
    ),
    chunksize: int = typer.Option(
        1_000_000,
        "--chunksize",
        min=1,
        help="Rows per PDQ production chunk while building the atlas",
    ),
) -> None:
    """Build the Texas RRC production field atlas from local official PDQ data."""
    try:
        _run_build_production_atlas(
            raw_root,
            output_root,
            dry_run,
            require_sources,
            allow_non_ace_output,
            chunksize,
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


def _field_development_input_paths(root: Path) -> list[str]:
    from worldenergydata.texas_rrc.field_development import io as field_io
    from worldenergydata.texas_rrc.lifecycle import io as lifecycle_io
    from worldenergydata.texas_rrc.production_atlas import io as atlas_io

    candidates = [
        lifecycle_io.LIFECYCLE_SPINE_DIR / lifecycle_io.SPINE_FILENAME,
        lifecycle_io.LIFECYCLE_SPINE_DIR / lifecycle_io.QUALITY_FILENAME,
        atlas_io.PRODUCTION_ATLAS_DIR / atlas_io.PARQUET_FILENAME,
        atlas_io.PRODUCTION_ATLAS_DIR / atlas_io.CSV_FILENAME,
        atlas_io.PRODUCTION_ATLAS_DIR / atlas_io.QUALITY_FILENAME,
    ]
    output_candidates = {
        field_io.FIELD_DEVELOPMENT_METRICS_DIR / field_io.CSV_FILENAME,
        field_io.FIELD_DEVELOPMENT_METRICS_DIR / field_io.PARQUET_FILENAME,
        field_io.FIELD_DEVELOPMENT_METRICS_DIR / field_io.QUALITY_FILENAME,
        field_io.FIELD_DEVELOPMENT_METRICS_DIR / field_io.MANIFEST_FILENAME,
    }
    return [
        str(path)
        for path in candidates
        if (root / path).exists() and path not in output_candidates
    ]


def _print_field_development_summary(row_count: int, source_gaps) -> None:
    table = Table(
        title="Texas RRC Field Development Metrics",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Field-development rows", str(row_count))
    table.add_row("Source gaps", ", ".join(source_gaps) if source_gaps else "None")
    console.print(table)


def _print_field_development_outputs(manifest) -> None:
    console.print(
        "[green]Wrote field-development metrics[/green] "
        f"{manifest.row_count} rows -> {manifest.csv_path}"
    )
    console.print(f"[dim]Parquet: {manifest.parquet_path}[/dim]")
    console.print(f"[dim]Quality report: {manifest.quality_path}[/dim]")
    console.print(f"[dim]Manifest: {manifest.manifest_path}[/dim]")


def _build_missing_lifecycle(root: Path, allow_non_ace_output: bool) -> None:
    from worldenergydata.texas_rrc.lifecycle.io import write_lifecycle_outputs
    from worldenergydata.texas_rrc.lifecycle.quality import assess_lifecycle_quality
    from worldenergydata.texas_rrc.lifecycle.sources import load_lifecycle_inputs
    from worldenergydata.texas_rrc.lifecycle.spine import build_lifecycle_spine

    inputs = load_lifecycle_inputs(root)
    if inputs.source_gaps:
        console.print(
            "[red]Error:[/red] missing lifecycle sources: "
            f"{', '.join(inputs.source_gaps)}"
        )
        raise typer.Exit(1)

    spine = build_lifecycle_spine(inputs)
    quality = assess_lifecycle_quality(spine, source_gaps=inputs.source_gaps)
    manifest = write_lifecycle_outputs(
        spine,
        quality,
        output_root=root,
        input_paths=_lifecycle_input_paths(root),
        allow_non_ace_root=allow_non_ace_output,
    )
    console.print(
        "[green]Wrote lifecycle spine[/green] "
        f"{manifest.row_count} rows -> {manifest.spine_path}"
    )


def _build_missing_production(
    root: Path,
    allow_non_ace_output: bool,
    chunksize: int,
) -> None:
    _run_build_production_atlas(
        raw_root=root,
        output_root=root,
        dry_run=False,
        require_sources=True,
        allow_non_ace_output=allow_non_ace_output,
        chunksize=chunksize,
    )


def _run_build_field_development_metrics(
    root: Path,
    output_root: Path,
    dry_run: bool,
    require_sources: bool,
    build_missing_lifecycle: bool,
    build_missing_production: bool,
    allow_non_ace_output: bool,
    chunksize: int,
) -> None:
    from worldenergydata.texas_rrc.field_development import (
        assess_field_development_quality,
        build_field_development_metrics,
        load_field_development_inputs,
        write_field_development_outputs,
    )

    inputs = load_field_development_inputs(root)
    if "well_lifecycle_spine" in inputs.source_gaps and build_missing_lifecycle:
        _build_missing_lifecycle(root, allow_non_ace_output)
        inputs = load_field_development_inputs(root)
    if "production_field_atlas" in inputs.source_gaps and build_missing_production:
        _build_missing_production(root, allow_non_ace_output, chunksize)
        inputs = load_field_development_inputs(root)

    source_gaps = tuple(inputs.source_gaps)
    if source_gaps and (require_sources or not dry_run):
        console.print(
            "[red]Error:[/red] missing field-development sources: "
            f"{', '.join(source_gaps)}"
        )
        raise typer.Exit(1)

    metrics = build_field_development_metrics(inputs)
    quality = assess_field_development_quality(metrics, inputs)
    _print_field_development_summary(len(metrics), source_gaps)

    if dry_run:
        console.print("[yellow]Dry run:[/yellow] no field-development outputs written")
        return

    manifest = write_field_development_outputs(
        metrics,
        quality,
        output_root=output_root,
        input_paths=_field_development_input_paths(root),
        allow_non_ace_root=allow_non_ace_output,
        command=(
            "worldenergydata texas-rrc build-field-development-metrics "
            f"--root {root} --output-root {output_root}"
        ),
    )
    _print_field_development_outputs(manifest)


@app.command("build-field-development-metrics")
def build_field_development_metrics_command(
    root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--root",
        help="Root containing curated Texas RRC lifecycle and production artifacts",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Root for curated field-development metric outputs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build the field-development summary without writing outputs",
    ),
    require_sources: bool = typer.Option(
        False,
        "--require-sources",
        help="Fail when any curated lifecycle or production input is missing",
    ),
    build_missing_lifecycle: bool = typer.Option(
        False,
        "--build-missing-lifecycle",
        help="Build missing lifecycle spine from local raw snapshots",
    ),
    build_missing_production: bool = typer.Option(
        False,
        "--build-missing-production",
        help="Build missing production atlas from local raw snapshots",
    ),
    allow_non_ace_output: bool = typer.Option(
        False,
        "--allow-non-ace-output",
        help="Allow non-/mnt/ace output roots for isolated tests or sandboxes",
    ),
    chunksize: int = typer.Option(
        1_000_000,
        "--chunksize",
        min=1,
        help="Rows per PDQ production chunk when building a missing atlas",
    ),
) -> None:
    """Build Texas RRC field-development metrics from curated direct sources."""
    try:
        _run_build_field_development_metrics(
            root,
            output_root,
            dry_run,
            require_sources,
            build_missing_lifecycle,
            build_missing_production,
            allow_non_ace_output,
            chunksize,
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


def _print_infrastructure_access_summary(row_count: int, source_gaps) -> None:
    table = Table(
        title="Texas RRC Infrastructure Access Metrics",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Infrastructure access rows", str(row_count))
    table.add_row("Source gaps", ", ".join(source_gaps) if source_gaps else "None")
    console.print(table)


def _print_infrastructure_access_outputs(manifest) -> None:
    console.print(
        "[green]Wrote infrastructure access metrics[/green] "
        f"{manifest.row_count} rows -> {manifest.csv_path}"
    )
    console.print(f"[dim]Parquet: {manifest.parquet_path}[/dim]")
    console.print(f"[dim]Quality report: {manifest.quality_path}[/dim]")
    console.print(f"[dim]Manifest: {manifest.manifest_path}[/dim]")


@app.command("build-infrastructure-access-metrics")
def build_infrastructure_access_metrics_command(
    root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--root",
        help="Root containing Texas RRC curated metrics and raw GIS layers",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Root for curated infrastructure access metric outputs",
    ),
    refresh_gis: bool = typer.Option(
        False,
        "--refresh-gis",
        help="Refresh official RRC well and pipeline GIS layers before building",
    ),
    require_sources: bool = typer.Option(
        False,
        "--require-sources",
        help="Fail when any curated or GIS input source is missing",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build the infrastructure access summary without writing outputs",
    ),
    nearby_radius_miles: float = typer.Option(
        25.0,
        "--nearby-radius-miles",
        min=1.0,
        help="Maximum distance used for nearby pipeline screening",
    ),
    allow_non_ace_output: bool = typer.Option(
        False,
        "--allow-non-ace-output",
        help="Allow non-/mnt/ace output roots for isolated tests or sandboxes",
    ),
    rows_per_page: int = typer.Option(
        1000,
        "--rows-per-page",
        min=1,
        help="GoDrive directory rows requested per page when refreshing GIS",
    ),
) -> None:
    """Build Texas RRC field-level infrastructure access metrics."""
    from worldenergydata.texas_rrc.infrastructure.cli_support import (
        run_build_infrastructure_access_metrics,
    )

    try:
        result = run_build_infrastructure_access_metrics(
            root=root,
            output_root=output_root,
            dry_run=dry_run,
            require_sources=require_sources,
            refresh_gis=refresh_gis,
            nearby_radius_miles=nearby_radius_miles,
            allow_non_ace_output=allow_non_ace_output,
            rows_per_page=rows_per_page,
        )
        _print_infrastructure_access_summary(result.row_count, result.source_gaps)
        if result.dry_run:
            console.print(
                "[yellow]Dry run:[/yellow] no infrastructure access outputs written"
            )
            return
        _print_infrastructure_access_outputs(result.manifest)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


def _print_field_atlas_report_summary(
    row_count: int, page_count: int, source_gaps
) -> None:
    table = Table(
        title="Texas RRC Field Atlas Reports",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Summary rows", str(row_count))
    table.add_row("Field pages", str(page_count))
    table.add_row("Source gaps", ", ".join(source_gaps) if source_gaps else "None")
    console.print(table)


def _print_field_atlas_report_outputs(manifest) -> None:
    console.print(
        "[green]Wrote field-atlas reports[/green] "
        f"{manifest.page_count} pages -> {manifest.output_dir}"
    )
    console.print(f"[dim]Index: {manifest.index_path}[/dim]")
    console.print(f"[dim]Summary CSV: {manifest.summary_csv_path}[/dim]")
    console.print(f"[dim]Summary Parquet: {manifest.summary_parquet_path}[/dim]")
    console.print(f"[dim]Quality report: {manifest.quality_path}[/dim]")
    console.print(f"[dim]Manifest: {manifest.manifest_path}[/dim]")


def _print_field_opportunity_summary(row_count: int, source_gaps) -> None:
    table = Table(
        title="Texas RRC Field Opportunity Rankings",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Ranked fields", str(row_count))
    table.add_row("Source gaps", ", ".join(source_gaps) if source_gaps else "None")
    console.print(table)


def _print_field_opportunity_outputs(manifest) -> None:
    console.print(
        "[green]Wrote field-opportunity rankings[/green] "
        f"{manifest.row_count} rows -> {manifest.output_dir}"
    )
    console.print(f"[dim]Rankings CSV: {manifest.rankings_csv_path}[/dim]")
    console.print(f"[dim]Rankings Parquet: {manifest.rankings_parquet_path}[/dim]")
    console.print(f"[dim]HTML summary: {manifest.html_path}[/dim]")
    console.print(f"[dim]Quality report: {manifest.quality_path}[/dim]")
    console.print(f"[dim]Manifest: {manifest.manifest_path}[/dim]")


def _print_field_architecture_dossier_summary(
    row_count: int,
    blocking_source_gaps,
    informational_source_gaps,
) -> None:
    table = Table(
        title="Texas RRC Field Architecture Dossiers",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Metric", style="dim")
    table.add_column("Value")
    table.add_row("Selected dossiers", str(row_count))
    table.add_row(
        "Blocking source gaps",
        ", ".join(blocking_source_gaps) if blocking_source_gaps else "None",
    )
    table.add_row(
        "Informational source gaps",
        ", ".join(informational_source_gaps) if informational_source_gaps else "None",
    )
    console.print(table)


def _print_field_architecture_dossier_outputs(manifest) -> None:
    console.print(
        "[green]Wrote field-architecture dossiers[/green] "
        f"{manifest.row_count} rows -> {manifest.output_dir}"
    )
    console.print(f"[dim]Index CSV: {manifest.index_csv_path}[/dim]")
    console.print(f"[dim]Index Parquet: {manifest.index_parquet_path}[/dim]")
    console.print(f"[dim]HTML summary: {manifest.summary_html_path}[/dim]")
    console.print(f"[dim]Quality report: {manifest.quality_path}[/dim]")
    console.print(f"[dim]Manifest: {manifest.manifest_path}[/dim]")


@app.command("publish-field-atlas-reports")
def publish_field_atlas_reports_command(
    root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--root",
        help="Root containing curated Texas RRC field, production, and access inputs",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Root for curated field-atlas report outputs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build the report model without writing outputs",
    ),
    require_sources: bool = typer.Option(
        False,
        "--require-sources",
        help="Fail when any curated field-atlas report input is missing",
    ),
    allow_non_ace_output: bool = typer.Option(
        False,
        "--allow-non-ace-output",
        help="Allow non-/mnt/ace output roots for isolated tests or sandboxes",
    ),
    max_fields: int | None = typer.Option(
        None,
        "--max-fields",
        min=1,
        help="Limit generated field pages after rank sorting",
    ),
) -> None:
    """Publish Texas RRC field-atlas index and field deep-dive reports."""
    from worldenergydata.texas_rrc.reports.cli_support import (
        run_publish_field_atlas_reports,
    )

    try:
        result = run_publish_field_atlas_reports(
            root=root,
            output_root=output_root,
            dry_run=dry_run,
            require_sources=require_sources,
            allow_non_ace_output=allow_non_ace_output,
            max_fields=max_fields,
        )
        _print_field_atlas_report_summary(
            result.row_count,
            result.page_count,
            result.source_gaps,
        )
        if result.dry_run:
            console.print("[yellow]Dry run:[/yellow] no field-atlas reports written")
            return
        _print_field_atlas_report_outputs(result.manifest)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("build-field-opportunities")
def build_field_opportunities_command(
    root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--root",
        help="Root containing curated Texas RRC field-atlas report inputs",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Root for curated field-opportunity ranking outputs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build the ranking model without writing outputs",
    ),
    require_sources: bool = typer.Option(
        False,
        "--require-sources",
        help="Fail when any curated field-opportunity input is missing",
    ),
    allow_non_ace_output: bool = typer.Option(
        False,
        "--allow-non-ace-output",
        help="Allow non-/mnt/ace output roots for isolated tests or sandboxes",
    ),
    max_fields: int | None = typer.Option(
        None,
        "--max-fields",
        min=1,
        help="Limit ranked fields after score sorting",
    ),
) -> None:
    """Build Texas RRC field opportunity and architecture-signal rankings."""
    from worldenergydata.texas_rrc.opportunities.cli_support import (
        run_build_field_opportunities,
    )

    try:
        result = run_build_field_opportunities(
            root=root,
            output_root=output_root,
            dry_run=dry_run,
            require_sources=require_sources,
            allow_non_ace_output=allow_non_ace_output,
            max_fields=max_fields,
        )
        _print_field_opportunity_summary(result.row_count, result.source_gaps)
        if result.dry_run:
            console.print(
                "[yellow]Dry run:[/yellow] no field-opportunity outputs written"
            )
            return
        _print_field_opportunity_outputs(result.manifest)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("build-field-architecture-dossiers")
def build_field_architecture_dossiers_command(
    root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--root",
        help="Root containing curated Texas RRC opportunity and context inputs",
    ),
    output_root: Path = typer.Option(
        Path("/mnt/ace/worldenergydata/data/modules/texas_rrc"),
        "--output-root",
        help="Root for curated field-architecture dossier outputs",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build dossier models without writing outputs",
    ),
    require_sources: bool = typer.Option(
        False,
        "--require-sources",
        help="Fail when any curated dossier input is missing",
    ),
    allow_non_ace_output: bool = typer.Option(
        False,
        "--allow-non-ace-output",
        help="Allow non-/mnt/ace output roots for isolated tests or sandboxes",
    ),
    max_fields: int = typer.Option(
        25,
        "--max-fields",
        min=1,
        help="Top-ranked opportunity rows to include before class coverage",
    ),
    class_coverage_limit: int = typer.Option(
        3,
        "--class-coverage-limit",
        min=0,
        help="Rows to add for each architecture class absent from top-ranked rows",
    ),
) -> None:
    """Build Texas RRC field architecture dossier packets."""
    from worldenergydata.texas_rrc.dossiers.cli_support import (
        run_build_field_architecture_dossiers,
    )

    try:
        result = run_build_field_architecture_dossiers(
            root=root,
            output_root=output_root,
            dry_run=dry_run,
            require_sources=require_sources,
            allow_non_ace_output=allow_non_ace_output,
            max_fields=max_fields,
            class_coverage_limit=class_coverage_limit,
        )
        _print_field_architecture_dossier_summary(
            result.row_count,
            result.blocking_source_gaps,
            result.informational_source_gaps,
        )
        if result.dry_run:
            console.print(
                "[yellow]Dry run:[/yellow] no field-architecture dossier outputs written"
            )
            return
        _print_field_architecture_dossier_outputs(result.manifest)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def analyze(
    district: Optional[str] = typer.Option(
        None, "--district", "-d", help="RRC district to analyze (e.g., '08', '7B')"
    ),
    county: Optional[str] = typer.Option(
        None, "--county", "-c", help="County name to analyze"
    ),
    operator: Optional[str] = typer.Option(
        None, "--operator", help="Operator name to filter analysis"
    ),
    include_economics: bool = typer.Option(
        False,
        "--include-economics",
        help="Include economic analysis (production value, etc.)",
    ),
    output: Path = typer.Option(
        Path("./reports/texas_rrc"),
        "--output",
        "-o",
        help="Output directory for analysis results",
    ),
    data_path: Path = typer.Option(
        Path("./data/texas_rrc"),
        "--data-path",
        help="Input directory containing Texas RRC data",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
) -> None:
    """
    Run Texas RRC analysis.

    Performs analysis on Texas oil and gas data including production
    statistics, well counts, and optionally economic metrics.

    Examples:
        worldenergydata texas-rrc analyze
        worldenergydata texas-rrc analyze --district 08
        worldenergydata texas-rrc analyze --county "MIDLAND" --include-economics
    """
    try:
        # Validate district if provided
        if district and district.upper() not in [x.upper() for x in VALID_DISTRICTS]:
            console.print(f"[red]Error:[/red] Invalid district '{district}'")
            console.print(f"[dim]Valid districts: {', '.join(VALID_DISTRICTS)}[/dim]")
            raise typer.Exit(1)

        # Display analysis parameters
        params_table = Table(show_header=False)
        params_table.add_column("Parameter", style="dim")
        params_table.add_column("Value")

        if district:
            params_table.add_row("District", district)
        if county:
            params_table.add_row("County", county)
        if operator:
            params_table.add_row("Operator", operator)
        params_table.add_row("Include Economics", "Yes" if include_economics else "No")
        params_table.add_row("Data Path", str(data_path))
        params_table.add_row("Output", str(output))

        console.print(
            Panel(params_table, title="Analysis Parameters", border_style="cyan")
        )

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Running Texas RRC analysis...", total=100)

            try:
                from worldenergydata.texas_rrc.analysis import TexasRRCAnalysis

                progress.update(
                    task, advance=20, description="[cyan]Loading analysis module..."
                )

                # Build analysis configuration
                config = {
                    "input_path": str(data_path),
                    "output_path": str(output),
                    "district": district,
                    "county": county,
                    "operator": operator,
                    "include_economics": include_economics,
                }

                progress.update(task, advance=20, description="[cyan]Loading data...")

                analysis = TexasRRCAnalysis(config)
                results = analysis.run()

                progress.update(
                    task, advance=40, description="[cyan]Generating report..."
                )

                # Save results
                import json

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results_file = output / f"texas_rrc_analysis_{timestamp}.json"

                with open(results_file, "w") as f:
                    json.dump(results, f, indent=2, default=str)

                progress.update(
                    task, advance=20, description="[cyan]Completing analysis..."
                )

                if verbose:
                    console.print(f"\n[dim]Results: {results}[/dim]")

                console.print("\n[green]Analysis completed successfully[/green]")
                console.print(f"[dim]Results saved to: {results_file}[/dim]")

            except ImportError as e:
                progress.update(task, completed=100)
                console.print(
                    f"[yellow]Warning:[/yellow] Could not import analysis module: {e}"
                )
                console.print(
                    "[dim]Run 'worldenergydata texas-rrc collect' first to download data.[/dim]"
                )
                raise typer.Exit(1)
            except FileNotFoundError:
                progress.update(task, completed=100)
                console.print(
                    "[yellow]Warning:[/yellow] No Texas RRC data found. "
                    "Run 'worldenergydata texas-rrc collect' first."
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
        Path("./data/texas_rrc"),
        "--data-path",
        "-d",
        help="Path to Texas RRC data directory",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed status information"
    ),
) -> None:
    """
    Show Texas RRC data status.

    Displays information about available Texas RRC data including
    file counts, data freshness, and district coverage.

    Examples:
        worldenergydata texas-rrc status
        worldenergydata texas-rrc status --verbose
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Loading Texas RRC data status...", total=100
            )

            status_data = {
                "data_files": 0,
                "data_size_mb": 0,
                "data_types": {},
                "districts_covered": [],
                "last_updated": "Unknown",
            }

            progress.update(
                task, advance=30, description="[cyan]Checking data directories..."
            )

            if data_path.exists():
                total_files = 0
                total_size = 0
                data_types_found = {}
                districts_found = set()

                for f in data_path.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_size += f.stat().st_size

                        stem = f.stem.lower()
                        for dtype in [
                            "production",
                            "wells",
                            "permits",
                            "completions",
                            "drilling",
                        ]:
                            if dtype in stem:
                                data_types_found[dtype] = (
                                    data_types_found.get(dtype, 0) + 1
                                )
                                break

                        # Check for district in filename
                        for dist in VALID_DISTRICTS:
                            if (
                                dist.lower() in stem
                                or f"district_{dist.lower()}" in stem
                            ):
                                districts_found.add(dist)

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
                status_data["data_types"] = data_types_found
                status_data["districts_covered"] = sorted(list(districts_found))

            progress.update(task, advance=70, description="[cyan]Formatting results...")

        # Create status table
        table = Table(
            title="Texas RRC Data Status", show_header=True, header_style="bold cyan"
        )

        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        if status_data["data_files"] > 0:
            table.add_row("Data Files", f"{status_data['data_files']:,}")
            table.add_row("Data Size", f"{status_data['data_size_mb']:.2f} MB")
            table.add_row(
                "Last Updated",
                (
                    status_data["last_updated"][:19]
                    if status_data["last_updated"] != "Unknown"
                    else "Unknown"
                ),
            )
            if status_data["districts_covered"]:
                table.add_row(
                    "Districts Covered", ", ".join(status_data["districts_covered"])
                )
        else:
            table.add_row("Data Files", "[yellow]No data files found[/yellow]")

        table.add_row("", "")
        table.add_row("Data Directory", str(data_path))

        console.print(table)

        # Show data types breakdown
        if status_data["data_types"] and verbose:
            types_table = Table(
                title="Data Types Breakdown", show_header=True, header_style="bold cyan"
            )
            types_table.add_column("Data Type")
            types_table.add_column("Files", justify="right")
            types_table.add_column("Status")

            all_types = ["production", "wells", "permits", "completions", "drilling"]
            for dtype in all_types:
                count = status_data["data_types"].get(dtype, 0)
                if count > 0:
                    types_table.add_row(
                        dtype.capitalize(), str(count), "[green]Available[/green]"
                    )
                else:
                    types_table.add_row(
                        dtype.capitalize(), "0", "[yellow]Not collected[/yellow]"
                    )

            console.print(types_table)

        # Show districts table if verbose
        if verbose:
            districts_table = Table(
                title="RRC Districts", show_header=True, header_style="bold cyan"
            )
            districts_table.add_column("District")
            districts_table.add_column("Region")
            districts_table.add_column("Status")

            district_regions = {
                "01": "San Antonio Area",
                "02": "Refugio Area",
                "03": "Southeast Texas",
                "04": "Deep South Texas",
                "05": "East Central Texas",
                "06": "East Texas",
                "7B": "West Central Texas",
                "7C": "West Central Texas",
                "08": "Permian Basin - Midland",
                "8A": "Permian Basin - Lubbock",
                "09": "North Texas",
                "10": "Panhandle",
            }

            for dist in VALID_DISTRICTS:
                region = district_regions.get(dist, "Unknown")
                if dist in status_data["districts_covered"]:
                    districts_table.add_row(
                        dist, region, "[green]Data Available[/green]"
                    )
                else:
                    districts_table.add_row(dist, region, "[yellow]No data[/yellow]")

            console.print(districts_table)

        console.print(
            "\n[dim]Use 'worldenergydata texas-rrc collect' to download data[/dim]"
        )
        console.print(
            "[dim]Use 'worldenergydata texas-rrc analyze' to run analysis[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command("validate-api")
def validate_api(
    api_number: str = typer.Argument(
        ..., help="Texas API number to validate (e.g., '42-123-12345' or '4212312345')"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed validation information"
    ),
) -> None:
    """
    Validate a Texas API number.

    Checks if the provided API number follows Texas RRC format
    and displays parsed components.

    Examples:
        worldenergydata texas-rrc validate-api 42-123-12345
        worldenergydata texas-rrc validate-api 4212312345
        worldenergydata texas-rrc validate-api 42-123-12345-00-00
    """
    try:
        # Remove dashes and spaces for parsing
        cleaned = api_number.replace("-", "").replace(" ", "")

        # Texas API format: 42-CCC-WWWWW[-SS-EE]
        # 42 = Texas state code
        # CCC = County code (3 digits)
        # WWWWW = Well number (5 digits)
        # SS = Sidetrack (optional, 2 digits)
        # EE = Completion (optional, 2 digits)

        validation_result = {
            "valid": False,
            "state_code": None,
            "county_code": None,
            "well_number": None,
            "sidetrack": None,
            "completion": None,
            "errors": [],
        }

        if len(cleaned) < 10:
            validation_result["errors"].append(
                f"API number too short: {len(cleaned)} digits (minimum 10)"
            )
        elif len(cleaned) > 14:
            validation_result["errors"].append(
                f"API number too long: {len(cleaned)} digits (maximum 14)"
            )
        else:
            # Check if all digits
            if not cleaned.isdigit():
                validation_result["errors"].append(
                    "API number must contain only digits"
                )
            else:
                validation_result["state_code"] = cleaned[:2]
                validation_result["county_code"] = cleaned[2:5]
                validation_result["well_number"] = cleaned[5:10]

                if validation_result["state_code"] != "42":
                    validation_result["errors"].append(
                        f"Invalid state code: {validation_result['state_code']} (Texas = 42)"
                    )

                if len(cleaned) >= 12:
                    validation_result["sidetrack"] = cleaned[10:12]
                if len(cleaned) >= 14:
                    validation_result["completion"] = cleaned[12:14]

                if not validation_result["errors"]:
                    validation_result["valid"] = True

        # Display results
        if validation_result["valid"]:
            console.print(
                Panel(
                    f"[bold green]Valid Texas API Number[/bold green]\n\n"
                    f"Input: {api_number}",
                    border_style="green",
                )
            )
        else:
            console.print(
                Panel(
                    f"[bold red]Invalid API Number[/bold red]\n\n"
                    f"Input: {api_number}\n"
                    f"Errors: {'; '.join(validation_result['errors'])}",
                    border_style="red",
                )
            )

        # Show parsed components
        components_table = Table(
            title="API Number Components", show_header=True, header_style="bold cyan"
        )
        components_table.add_column("Component")
        components_table.add_column("Value")
        components_table.add_column("Description")

        if validation_result["state_code"]:
            components_table.add_row(
                "State Code",
                validation_result["state_code"],
                (
                    "42 = Texas"
                    if validation_result["state_code"] == "42"
                    else "[red]Invalid[/red]"
                ),
            )
        if validation_result["county_code"]:
            components_table.add_row(
                "County Code",
                validation_result["county_code"],
                "3-digit county identifier",
            )
        if validation_result["well_number"]:
            components_table.add_row(
                "Well Number",
                validation_result["well_number"],
                "5-digit well identifier",
            )
        if validation_result["sidetrack"]:
            components_table.add_row(
                "Sidetrack", validation_result["sidetrack"], "Sidetrack number"
            )
        if validation_result["completion"]:
            components_table.add_row(
                "Completion", validation_result["completion"], "Completion number"
            )

        console.print(components_table)

        # Format examples
        if verbose or not validation_result["valid"]:
            console.print("\n[dim]Valid Texas API formats:[/dim]")
            console.print("[dim]  42-CCC-WWWWW       (10 digits)[/dim]")
            console.print("[dim]  42-CCC-WWWWW-SS    (12 digits with sidetrack)[/dim]")
            console.print("[dim]  42-CCC-WWWWW-SS-EE (14 digits with completion)[/dim]")

        if not validation_result["valid"]:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.callback()
def callback() -> None:
    """
    Texas Railroad Commission data operations.

    Access Texas oil and gas data including production statistics,
    well information, drilling permits, and completions from the
    Texas Railroad Commission.
    """
    pass
