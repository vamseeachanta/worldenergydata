# ABOUTME: CLI command for NDBC buoy data ingestion and wave scatter matrices (WRK-316).
# ABOUTME: Provides `worldenergydata ndbc` subcommand for station downloads and analysis.
"""
NDBC CLI Command

Downloads NOAA NDBC buoy historical wave data, builds Hs-Tp scatter matrices,
Weibull distribution fits for Hs, and directional wave roses.

Usage examples::

    worldenergydata ndbc --station 42001 --years 2000-2024
    worldenergydata ndbc --station 41001 --years 2020-2023 --output /tmp/42001
    worldenergydata ndbc --station 42001 --years 2023-2023 --hs-bin-size 0.5
"""

from __future__ import annotations

import pathlib
import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="ndbc",
    help="NDBC buoy data ingestion, scatter matrices, Weibull fits, and wave roses",
    no_args_is_help=True,
)
console = Console()


def _parse_years(years_str: str) -> tuple[int, int]:
    """Parse a 'YYYY-YYYY' or 'YYYY' years string into (start, end) ints."""
    if "-" in years_str:
        parts = years_str.split("-", 1)
        return int(parts[0]), int(parts[1])
    year = int(years_str)
    return year, year


@app.callback(invoke_without_command=True)
def ndbc_main(
    ctx: typer.Context,
    station: str = typer.Option(
        ..., "--station", "-s", help="NDBC station ID (e.g. 42001)"
    ),
    years: str = typer.Option(
        ...,
        "--years",
        "-y",
        help="Year range as YYYY-YYYY or single YYYY (e.g. 2000-2024)",
    ),
    output: Optional[pathlib.Path] = typer.Option(
        None, "--output", "-o", help="Directory for output files (default: current dir)"
    ),
    hs_bin_size: float = typer.Option(
        1.0, "--hs-bin-size", help="Hs bin width in metres for scatter matrix"
    ),
    tp_bin_size: float = typer.Option(
        2.0, "--tp-bin-size", help="Tp bin width in seconds for scatter matrix"
    ),
    n_sectors: int = typer.Option(
        8, "--n-sectors", help="Number of directional sectors for wave rose"
    ),
    weibull_params: int = typer.Option(
        2,
        "--weibull-params",
        help="Weibull fit: 2 for 2-parameter, 3 for 3-parameter",
    ),
    sample_file: Optional[pathlib.Path] = typer.Option(
        None,
        "--sample-file",
        help="Parse a local NDBC stdmet text file instead of downloading",
    ),
) -> None:
    """
    Download and analyse NDBC buoy data.

    Downloads standard meteorological data for STATION across the specified
    YEARS range, then produces:

    \b
    - Hs-Tp scatter matrix (CSV)
    - Weibull distribution fit for Hs (JSON summary to stdout)
    - Directional wave rose (JSON summary to stdout)

    When --sample-file is given the download step is skipped and the
    provided file is parsed directly (useful for testing and offline use).
    """
    if ctx.invoked_subcommand is not None:
        return

    from worldenergydata.metocean.ndbc import (
        build_scatter_matrix,
        fit_weibull_hs,
        parse_stdmet_file,
        parse_stdmet_line,
        wave_rose,
    )
    import json
    import numpy as np

    try:
        year_start, year_end = _parse_years(years)
    except (ValueError, IndexError):
        console.print(
            f"[red]Invalid --years value '{years}'. "
            "Use 'YYYY-YYYY' or 'YYYY'.[/red]"
        )
        raise typer.Exit(1)

    out_dir = output or pathlib.Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(
        Panel(
            f"[bold cyan]NDBC Buoy Analysis[/bold cyan]\n"
            f"Station:  {station}\n"
            f"Years:    {year_start}–{year_end}\n"
            f"Output:   {out_dir}",
            border_style="cyan",
        )
    )

    # ---------------------------------------------------------------
    # Collect records
    # ---------------------------------------------------------------
    all_records = []

    if sample_file is not None:
        console.print(f"[dim]Parsing sample file: {sample_file}[/dim]")
        all_records = parse_stdmet_file(sample_file)
    else:
        try:
            from worldenergydata.metocean.ndbc import NDBCClient
            from datetime import datetime

            client = NDBCClient()
            with console.status(
                f"[bold green]Fetching {year_end - year_start + 1} year(s) from NDBC…"
            ):
                for year in range(year_start, year_end + 1):
                    df = client.get_historical(station, year)
                    if not df.empty:
                        records_year = df.to_dict("records")
                        # Rename 'observation_time' -> keep; ensure hs/tp keys
                        all_records.extend(records_year)
                    else:
                        console.print(
                            f"[yellow]  No data for {station} / {year}[/yellow]"
                        )
        except Exception as exc:
            console.print(
                f"[red]Download failed: {exc}[/red]\n"
                "[dim]Hint: use --sample-file to parse a local file instead.[/dim]"
            )
            raise typer.Exit(1)

    if not all_records:
        console.print("[yellow]No records to analyse.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[green]Loaded {len(all_records)} observations.[/green]")

    # ---------------------------------------------------------------
    # Scatter matrix
    # ---------------------------------------------------------------
    hs_max = 20.0
    tp_max = 26.0
    hs_bins = list(np.arange(0, hs_max + hs_bin_size, hs_bin_size))
    tp_bins = list(np.arange(0, tp_max + tp_bin_size, tp_bin_size))

    # Ensure 'tp' key: prefer 'dpd' (dominant period) if available
    for rec in all_records:
        if "tp" not in rec or rec.get("tp") is None:
            rec["tp"] = rec.get("dpd")

    matrix = build_scatter_matrix(
        all_records, hs_bins=hs_bins, tp_bins=tp_bins, normalize=False
    )
    matrix_pct = build_scatter_matrix(
        all_records, hs_bins=hs_bins, tp_bins=tp_bins, normalize=True
    )

    import pandas as pd

    hs_labels = [f"{hs_bins[i]:.1f}-{hs_bins[i+1]:.1f}" for i in range(len(hs_bins) - 1)]
    tp_labels = [f"{tp_bins[j]:.1f}-{tp_bins[j+1]:.1f}" for j in range(len(tp_bins) - 1)]
    scatter_df = pd.DataFrame(matrix, index=hs_labels, columns=tp_labels)
    scatter_pct_df = pd.DataFrame(
        matrix_pct * 100.0, index=hs_labels, columns=tp_labels
    )

    scatter_path = out_dir / f"{station}_scatter_counts.csv"
    scatter_pct_path = out_dir / f"{station}_scatter_pct.csv"
    scatter_df.to_csv(scatter_path)
    scatter_pct_df.to_csv(scatter_pct_path)
    console.print(f"[green]Scatter matrix saved:[/green] {scatter_path}")
    console.print(f"[green]Scatter matrix (%) saved:[/green] {scatter_pct_path}")

    # ---------------------------------------------------------------
    # Weibull fit
    # ---------------------------------------------------------------
    hs_values = [r["hs"] for r in all_records if r.get("hs") is not None]
    weibull_result: dict = {}
    if len(hs_values) >= 3:
        try:
            weibull_result = fit_weibull_hs(hs_values, n_params=weibull_params)
            weibull_path = out_dir / f"{station}_weibull_{weibull_params}p.json"
            with open(weibull_path, "w") as fh:
                json.dump(weibull_result, fh, indent=2)
            console.print(f"[green]Weibull fit saved:[/green] {weibull_path}")
        except Exception as exc:
            console.print(f"[yellow]Weibull fit failed: {exc}[/yellow]")
    else:
        console.print("[yellow]Not enough Hs values for Weibull fit.[/yellow]")

    # ---------------------------------------------------------------
    # Wave rose
    # ---------------------------------------------------------------
    rose_result = wave_rose(all_records, n_sectors=n_sectors)
    rose_path = out_dir / f"{station}_wave_rose_{n_sectors}sec.json"
    with open(rose_path, "w") as fh:
        json.dump(rose_result, fh, indent=2)
    console.print(f"[green]Wave rose saved:[/green] {rose_path}")

    # ---------------------------------------------------------------
    # Print summary
    # ---------------------------------------------------------------
    summary_table = Table(title="Analysis Summary", show_header=True)
    summary_table.add_column("Parameter")
    summary_table.add_column("Value")

    total_valid = int(matrix.sum())
    summary_table.add_row("Station", station)
    summary_table.add_row("Years", f"{year_start}–{year_end}")
    summary_table.add_row("Total records", str(len(all_records)))
    summary_table.add_row("Scatter entries", str(total_valid))
    if weibull_result:
        summary_table.add_row(
            "Weibull shape", f"{weibull_result.get('shape', 'n/a'):.3f}"
        )
        summary_table.add_row(
            "Weibull scale", f"{weibull_result.get('scale', 'n/a'):.3f}"
        )
    if hs_values:
        summary_table.add_row("Mean Hs (m)", f"{np.mean(hs_values):.2f}")
        summary_table.add_row(
            "Max Hs (m)", f"{np.max(hs_values):.2f}"
        )

    console.print(summary_table)


__all__ = ["app"]
