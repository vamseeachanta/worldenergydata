# ABOUTME: Typer CLI for Arps decline curve production forecasting.
# ABOUTME: Provides the `forecast` subcommand for worldenergydata CLI.

"""
Arps Decline Curve CLI

Fit historical production data to an Arps decline model, compute EUR,
and output forecast tables and interactive HTML charts.

Usage:
    worldenergydata forecast --help
    worldenergydata forecast --model hyperbolic --months 120
    worldenergydata forecast --input production.csv --model exponential
    worldenergydata forecast --output report.html --econ-limit 10.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from worldenergydata.production.forecast.decline import ArpsDeclineCurve

console = Console()

app = typer.Typer(
    name="forecast",
    help="Arps decline curve analysis — fit, EUR, and production forecast",
    no_args_is_help=False,
    invoke_without_command=True,
)

_SAMPLE_QI = 5000.0
_SAMPLE_DI = 0.07
_SAMPLE_B = 1.1
_SAMPLE_MONTHS_HIST = 36


def _sample_production() -> pd.DataFrame:
    """Generate a representative synthetic production profile."""
    t = range(1, _SAMPLE_MONTHS_HIST + 1)
    rates = [
        _SAMPLE_QI * (1.0 + _SAMPLE_B * _SAMPLE_DI * m) ** (-1.0 / _SAMPLE_B) for m in t
    ]
    return pd.DataFrame({"month": list(t), "rate_bbl": rates})


@app.callback()
def run(
    ctx: typer.Context,
    model: str = typer.Option(
        "hyperbolic",
        "--model",
        "-m",
        help="Decline model: exponential | hyperbolic | harmonic",
    ),
    months: int = typer.Option(
        120,
        "--months",
        "-n",
        help="Forecast horizon (months)",
    ),
    econ_limit: float = typer.Option(
        10.0,
        "--econ-limit",
        "-e",
        help="Economic limit rate (bbl/month) for EUR calculation",
    ),
    input_path: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="CSV input file with columns: month, rate_bbl",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output HTML report path",
    ),
) -> None:
    """Fit an Arps decline curve and generate a production forecast."""
    if ctx.invoked_subcommand is not None:
        return

    if input_path is not None:
        if not input_path.exists():
            console.print(f"[red]Input file not found:[/red] {input_path}")
            raise typer.Exit(code=1)
        production = pd.read_csv(input_path)
        if "month" not in production.columns or "rate_bbl" not in production.columns:
            console.print("[red]CSV must contain columns: month, rate_bbl[/red]")
            raise typer.Exit(code=1)
    else:
        console.print(
            "[dim]No --input provided; using synthetic sample data "
            f"(qi={_SAMPLE_QI:,.0f} bbl/mo, {_SAMPLE_MONTHS_HIST} months)[/dim]"
        )
        production = _sample_production()

    console.print(f"\nFitting [bold cyan]{model}[/bold cyan] decline curve …")
    adc = ArpsDeclineCurve()
    try:
        result = adc.fit(
            production, model=model, economic_limit=econ_limit, months=months
        )
    except ValueError as exc:
        console.print(f"[red]Fit error:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    # Summary table
    summary = Table(title="Arps Decline Curve — Fit Summary", show_header=True)
    summary.add_column("Parameter", style="bold")
    summary.add_column("Value")
    summary.add_row("Model", result.model)
    summary.add_row("qi (bbl/month)", f"{result.qi:,.1f}")
    summary.add_row("Di (1/month)", f"{result.Di:.4f}")
    summary.add_row("b (exponent)", f"{result.b:.4f}")
    summary.add_row("R²", f"{result.r_squared:.4f}")
    summary.add_row("EUR (bbl)", f"{result.eur_bbl:,.0f}")
    console.print(summary)

    # Forecast table (first 12 months)
    fc_table = Table(title=f"Forecast — First 12 of {months} months", show_header=True)
    fc_table.add_column("Month", style="dim")
    fc_table.add_column("Rate (bbl/mo)", justify="right")
    fc_table.add_column("Cumulative (bbl)", justify="right")
    for _, row in result.forecast_df.head(12).iterrows():
        fc_table.add_row(
            str(int(row["month"])),
            f"{row['rate_bbl']:,.0f}",
            f"{row['cumulative_bbl']:,.0f}",
        )
    console.print(fc_table)

    # HTML report
    if output_path is not None:
        fig = adc.plot(production, result)
        fig.write_html(str(output_path))
        console.print(f"\n[green]HTML report saved:[/green] {output_path}")
