"""Lower Tertiary CLI commands.

Surface for portfolio-level analyses across the LT-2026 field roster.

Usage:
    worldenergydata lower-tertiary portfolio-economics --output-csv ... --output-html ...
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from worldenergydata.lower_tertiary.portfolio_analytics import (
    portfolio_analytics_to_csv,
    portfolio_analytics_to_html,
    run_portfolio_analytics,
)
from worldenergydata.lower_tertiary.portfolio_economics import (
    portfolio_to_csv,
    portfolio_to_html,
    run_portfolio,
)

console = Console()
app = typer.Typer(
    name="lower-tertiary",
    help="Lower Tertiary portfolio analyses (10 GoM fields)",
    no_args_is_help=True,
)


@app.command("portfolio-economics")
def portfolio_economics(
    output_csv: Path = typer.Option(
        ...,
        "--output-csv",
        help="Path to write the per-field summary CSV",
    ),
    output_html: Optional[Path] = typer.Option(
        None,
        "--output-html",
        help="Optional path to write the buyer-presentable HTML report",
    ),
    discount_rate: float = typer.Option(
        0.10, "--discount-rate", help="Annual discount rate (e.g. 0.10 for 10%)"
    ),
    oil_price: float = typer.Option(
        70.0, "--oil-price", help="Base-case oil price in USD/bbl"
    ),
) -> None:
    """Run portfolio-level economics across all 10 LT-2026 fields."""
    run = run_portfolio(
        discount_rate=discount_rate,
        oil_price_usd_per_bbl=oil_price,
    )
    csv_path = portfolio_to_csv(run, output_csv)
    console.print(f"[green]Wrote CSV:[/] {csv_path}")
    if output_html is not None:
        html_path = portfolio_to_html(run, output_html)
        console.print(f"[green]Wrote HTML:[/] {html_path}")
    console.print(
        f"[bold]Fields analyzed:[/] {len(run.results)} &middot; "
        f"[bold]Total cum capex:[/] ${sum(r.capex_mm_usd for r in run.results):,.0f} M"
    )


@app.command("portfolio-analytics")
def portfolio_analytics(
    output_dir: Path = typer.Option(
        ...,
        "--output-dir",
        help="Directory to write the four section CSVs",
    ),
    output_html: Optional[Path] = typer.Option(
        None,
        "--output-html",
        help="Optional path to write the combined HTML report",
    ),
    section: str = typer.Option(
        "all",
        "--section",
        help="Which section(s) to render: technology|operator|hse|cost_benchmark|all",
    ),
) -> None:
    """Run cross-field analytics across all 10 LT-2026 fields (#376)."""
    run = run_portfolio_analytics()
    csv_paths = portfolio_analytics_to_csv(run, output_dir)
    if section == "all":
        for name, path in csv_paths.items():
            console.print(f"[green]Wrote {name} CSV:[/] {path}")
    elif section in csv_paths:
        console.print(f"[green]Wrote {section} CSV:[/] {csv_paths[section]}")
    else:
        console.print(
            f"[red]Unknown section {section!r}. Valid: {sorted(csv_paths.keys()) + ['all']}[/]"
        )
        raise typer.Exit(code=1)
    if output_html is not None:
        html_path = portfolio_analytics_to_html(run, output_html)
        console.print(f"[green]Wrote HTML:[/] {html_path}")
    console.print(
        f"[bold]Sections rendered:[/] {section} &middot; "
        f"[bold]Fields:[/] {len(run.field_ids)}"
    )
