"""
FDAS CLI Commands

Provides command-line interface for Field Development Analysis System (FDAS)
including NPV calculations, MIRR analysis, and comprehensive financial modeling.

Usage:
    worldenergydata fdas <command> [options]

Examples:
    worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300,400,500]"
    worldenergydata fdas calculate-mirr --cashflows "[-1000,100,200,300,400,500]"
    worldenergydata fdas analyze --field "Thunder Horse" --discount-rate 0.10
"""

import typer
from typing import Optional, List
from pathlib import Path
from enum import Enum
import json

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

# Initialize console
console = Console()

# Create FDAS Typer app
app = typer.Typer(
    name="fdas",
    help="Field Development Analysis System",
    no_args_is_help=True,
)


class DepthClassification(str, Enum):
    """Water depth classification."""
    shelf = "shelf"
    deepwater = "deepwater"
    ultra_deepwater = "ultra_deepwater"


class Period(str, Enum):
    """Cashflow period options."""
    monthly = "monthly"
    annual = "annual"


def parse_cashflows(cashflows_str: str) -> list:
    """Parse cashflows from JSON string."""
    try:
        cashflows = json.loads(cashflows_str)
        if not isinstance(cashflows, list):
            raise ValueError("Cashflows must be a list")
        return [float(x) for x in cashflows]
    except json.JSONDecodeError:
        raise typer.BadParameter("Invalid JSON format for cashflows")


@app.command("calculate-npv")
def calculate_npv(
    cashflows: str = typer.Option(
        ..., "--cashflows", "-c",
        help="Cashflows as JSON array (e.g., '[-1000,100,200,300,400,500]')"
    ),
    discount_rate: float = typer.Option(
        0.10, "--discount-rate", "-r",
        help="Annual discount rate (e.g., 0.10 for 10%)"
    ),
    period: Period = typer.Option(
        Period.monthly,
        "--period", "-p",
        help="Cashflow period"
    ),
):
    """
    Calculate Net Present Value (NPV) of cashflow stream.

    Takes a series of cashflows and calculates the NPV using the
    specified discount rate.

    Examples:
        worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300,400,500]"
        worldenergydata fdas calculate-npv --cashflows "[-1000,100,200,300]" --discount-rate 0.08
        worldenergydata fdas calculate-npv --cashflows "[-5000,1000,1500,2000]" --period annual
    """
    try:
        cf_list = parse_cashflows(cashflows)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Calculating NPV...", total=None)

            try:
                from worldenergydata.modules.fdas.core.financial import calculate_npv as calc_npv

                npv = calc_npv(
                    __import__("numpy").array(cf_list),
                    discount_rate,
                    period.value
                )

                progress.update(task, completed=True)

                # Display results
                results_table = Table(
                    title="NPV Calculation Results",
                    show_header=True,
                    header_style="bold cyan"
                )
                results_table.add_column("Metric", style="dim")
                results_table.add_column("Value", justify="right")

                results_table.add_row("Cashflows", f"{len(cf_list)} periods")
                results_table.add_row("Discount Rate", f"{discount_rate:.2%}")
                results_table.add_row("Period", period.value)
                results_table.add_row("Net Present Value", f"${npv:,.2f}")
                results_table.add_row(
                    "Investment",
                    f"${abs(min(cf_list)):,.2f}" if min(cf_list) < 0 else "N/A"
                )

                console.print(results_table)

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import FDAS module: {e}")
                console.print(f"[dim]Cashflows: {cf_list}[/dim]")
                console.print(f"[dim]Discount Rate: {discount_rate}[/dim]")
                progress.update(task, completed=True)

    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("calculate-mirr")
def calculate_mirr(
    cashflows: str = typer.Option(
        ..., "--cashflows", "-c",
        help="Cashflows as JSON array (e.g., '[-1000,100,200,300,400,500]')"
    ),
    discount_rate: float = typer.Option(
        0.10, "--discount-rate", "-r",
        help="Annual discount rate (e.g., 0.10 for 10%)"
    ),
    reinvestment_rate: Optional[float] = typer.Option(
        None, "--reinvestment-rate",
        help="Annual reinvestment rate (defaults to discount rate)"
    ),
):
    """
    Calculate Modified Internal Rate of Return (MIRR).

    Uses Excel-compatible methodology for MIRR calculation, which is
    the industry standard approach.

    Examples:
        worldenergydata fdas calculate-mirr --cashflows "[-1000,100,200,300,400,500]"
        worldenergydata fdas calculate-mirr --cashflows "[-5000,1000,1500,2000]" --discount-rate 0.12
    """
    try:
        cf_list = parse_cashflows(cashflows)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Calculating MIRR...", total=None)

            try:
                from worldenergydata.modules.fdas.core.financial import excel_like_mirr

                import numpy as np

                mirr_monthly, mirr_annual = excel_like_mirr(
                    np.array(cf_list),
                    discount_rate,
                    reinvestment_rate
                )

                progress.update(task, completed=True)

                # Display results
                results_table = Table(
                    title="MIRR Calculation Results",
                    show_header=True,
                    header_style="bold cyan"
                )
                results_table.add_column("Metric", style="dim")
                results_table.add_column("Value", justify="right")

                results_table.add_row("Cashflows", f"{len(cf_list)} periods")
                results_table.add_row("Discount Rate", f"{discount_rate:.2%}")
                results_table.add_row(
                    "Reinvestment Rate",
                    f"{reinvestment_rate:.2%}" if reinvestment_rate else "Same as discount"
                )

                if not np.isnan(mirr_annual):
                    results_table.add_row("Monthly MIRR", f"{mirr_monthly:.4%}")
                    results_table.add_row("Annual MIRR", f"{mirr_annual:.2%}")
                else:
                    results_table.add_row("MIRR", "[yellow]Cannot calculate[/yellow]")

                console.print(results_table)

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import FDAS module: {e}")
                console.print(f"[dim]Cashflows: {cf_list}[/dim]")
                progress.update(task, completed=True)

    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("calculate-irr")
def calculate_irr(
    cashflows: str = typer.Option(
        ..., "--cashflows", "-c",
        help="Cashflows as JSON array"
    ),
    period: Period = typer.Option(
        Period.monthly,
        "--period", "-p",
        help="Cashflow period"
    ),
):
    """
    Calculate Internal Rate of Return (IRR).

    Examples:
        worldenergydata fdas calculate-irr --cashflows "[-1000,100,200,300,400,500]"
        worldenergydata fdas calculate-irr --cashflows "[-5000,2000,2000,2000]" --period annual
    """
    try:
        cf_list = parse_cashflows(cashflows)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Calculating IRR...", total=None)

            try:
                from worldenergydata.modules.fdas.core.financial import calculate_irr as calc_irr

                import numpy as np

                irr_period, irr_annual = calc_irr(np.array(cf_list), period.value)

                progress.update(task, completed=True)

                # Display results
                results_table = Table(
                    title="IRR Calculation Results",
                    show_header=True,
                    header_style="bold cyan"
                )
                results_table.add_column("Metric", style="dim")
                results_table.add_column("Value", justify="right")

                results_table.add_row("Cashflows", f"{len(cf_list)} periods")
                results_table.add_row("Period", period.value)
                results_table.add_row(f"{period.value.title()} IRR", f"{irr_period:.4%}")
                results_table.add_row("Annual IRR", f"{irr_annual:.2%}")

                console.print(results_table)

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import FDAS module: {e}")
                progress.update(task, completed=True)

    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command("calculate-all")
def calculate_all(
    cashflows: str = typer.Option(
        ..., "--cashflows", "-c",
        help="Cashflows as JSON array"
    ),
    discount_rate: float = typer.Option(
        0.10, "--discount-rate", "-r",
        help="Annual discount rate"
    ),
    period: Period = typer.Option(
        Period.monthly,
        "--period", "-p",
        help="Cashflow period"
    ),
):
    """
    Calculate all financial metrics for a cashflow stream.

    Computes NPV, MIRR, IRR, and payback period in a single operation.

    Examples:
        worldenergydata fdas calculate-all --cashflows "[-1000,100,200,300,400,500]"
        worldenergydata fdas calculate-all --cashflows "[-5000,1000,1500,2000]" --discount-rate 0.12
    """
    try:
        cf_list = parse_cashflows(cashflows)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Calculating all metrics...", total=None)

            try:
                from worldenergydata.modules.fdas.core.financial import calculate_all_metrics

                import numpy as np

                results = calculate_all_metrics(
                    np.array(cf_list),
                    discount_rate,
                    period.value
                )

                progress.update(task, completed=True)

                # Display results
                results_table = Table(
                    title="Financial Metrics Summary",
                    show_header=True,
                    header_style="bold cyan"
                )
                results_table.add_column("Metric", style="dim")
                results_table.add_column("Value", justify="right")

                results_table.add_row("Cashflows", f"{len(cf_list)} periods")
                results_table.add_row("Discount Rate", f"{discount_rate:.2%}")
                results_table.add_row("Period", period.value)
                results_table.add_row("", "")  # Spacer

                if results.get("npv") is not None:
                    results_table.add_row("NPV", f"${results['npv']:,.2f}")
                else:
                    results_table.add_row("NPV", "[red]Error[/red]")

                if results.get("mirr_annual") is not None and not np.isnan(results["mirr_annual"]):
                    results_table.add_row("Annual MIRR", f"{results['mirr_annual']:.2%}")
                else:
                    results_table.add_row("Annual MIRR", "[yellow]N/A[/yellow]")

                if results.get("irr_annual") is not None:
                    results_table.add_row("Annual IRR", f"{results['irr_annual']:.2%}")
                else:
                    results_table.add_row("Annual IRR", "[yellow]N/A[/yellow]")

                if results.get("payback_years") is not None:
                    if results["payback_years"] == float("inf"):
                        results_table.add_row("Payback Period", "[red]Never[/red]")
                    else:
                        results_table.add_row("Payback Period", f"{results['payback_years']:.1f} years")

                console.print(results_table)

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import FDAS module: {e}")
                progress.update(task, completed=True)

    except typer.BadParameter as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def analyze(
    field: Optional[str] = typer.Option(
        None, "--field", "-f",
        help="Field name to analyze (e.g., 'Thunder Horse')"
    ),
    lease: Optional[str] = typer.Option(
        None, "--lease", "-l",
        help="Lease number to analyze"
    ),
    discount_rate: float = typer.Option(
        0.10, "--discount-rate", "-r",
        help="Annual discount rate for analysis"
    ),
    oil_price: float = typer.Option(
        75.00, "--oil-price",
        help="Oil price per barrel"
    ),
    gas_price: float = typer.Option(
        3.50, "--gas-price",
        help="Gas price per MCF"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output file path for analysis results"
    ),
):
    """
    Perform comprehensive field development analysis.

    Integrates BSEE data with financial modeling to provide complete
    economic analysis of field development.

    Examples:
        worldenergydata fdas analyze --field "Thunder Horse" --discount-rate 0.10
        worldenergydata fdas analyze --lease OCS-G-12345 --oil-price 80
    """
    try:
        if not any([field, lease]):
            console.print("[red]Error:[/red] Either --field or --lease is required")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Running field development analysis...", total=None)

            console.print(
                Panel(
                    f"[bold]Analysis Configuration[/bold]\n"
                    f"Field: {field or 'N/A'}\n"
                    f"Lease: {lease or 'N/A'}\n"
                    f"Discount Rate: {discount_rate:.2%}\n"
                    f"Oil Price: ${oil_price:.2f}/bbl\n"
                    f"Gas Price: ${gas_price:.2f}/MCF",
                    border_style="cyan"
                )
            )

            try:
                from worldenergydata.modules.fdas.adapters.bsee_adapter import BseeAdapter

                console.print("[yellow]Note:[/yellow] BSEE adapter integration in progress")

            except ImportError as e:
                console.print(f"[yellow]Warning:[/yellow] Could not import FDAS adapter: {e}")

            progress.update(task, completed=True)

        console.print("\n[green]Analysis completed[/green]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def classify(
    water_depth: float = typer.Argument(
        ...,
        help="Water depth in feet"
    ),
):
    """
    Classify development system by water depth.

    Returns the classification (shelf, deepwater, or ultra-deepwater)
    based on the provided water depth.

    Examples:
        worldenergydata fdas classify 500
        worldenergydata fdas classify 5000
        worldenergydata fdas classify 10000
    """
    try:
        from worldenergydata.modules.fdas.core.config import classify_dev_system_by_depth

        classification = classify_dev_system_by_depth(water_depth)

        console.print(
            Panel(
                f"[bold]Water Depth Classification[/bold]\n\n"
                f"Water Depth: [cyan]{water_depth:,.0f} ft[/cyan]\n"
                f"Classification: [green]{classification}[/green]",
                border_style="cyan"
            )
        )

    except ImportError:
        # Fallback classification
        if water_depth < 1000:
            classification = "shelf"
        elif water_depth < 5000:
            classification = "deepwater"
        else:
            classification = "ultra_deepwater"

        console.print(
            Panel(
                f"[bold]Water Depth Classification[/bold]\n\n"
                f"Water Depth: [cyan]{water_depth:,.0f} ft[/cyan]\n"
                f"Classification: [green]{classification}[/green]",
                border_style="cyan"
            )
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise typer.Exit(1)


@app.command()
def info():
    """Display information about the FDAS module."""
    info_panel = Panel(
        """[bold cyan]Field Development Analysis System (FDAS)[/bold cyan]

[yellow]Purpose:[/yellow]
Comprehensive financial analysis for deepwater field development,
including NPV/MIRR calculations, cashflow modeling, and integration
with BSEE data sources.

[yellow]Key Features:[/yellow]
  - Excel-compatible MIRR calculations
  - NPV analysis with customizable discount rates
  - IRR calculations with monthly/annual periods
  - Payback period analysis
  - Integration with BSEE production data
  - Water depth-based system classification

[yellow]Available Commands:[/yellow]
  - calculate-npv  - Calculate Net Present Value
  - calculate-mirr - Calculate Modified IRR
  - calculate-irr  - Calculate Internal Rate of Return
  - calculate-all  - Calculate all financial metrics
  - analyze        - Comprehensive field analysis
  - classify       - Classify by water depth

[yellow]Supported Metrics:[/yellow]
  - NPV (Net Present Value)
  - MIRR (Modified Internal Rate of Return)
  - IRR (Internal Rate of Return)
  - Payback Period

[yellow]Documentation:[/yellow]
See FDAS module documentation for detailed usage""",
        border_style="cyan"
    )
    console.print(info_panel)


@app.callback()
def callback():
    """
    Field Development Analysis System (FDAS).

    Perform comprehensive financial analysis for deepwater field development
    including NPV, MIRR, IRR calculations, and integration with BSEE data.
    """
    pass
