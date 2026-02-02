# ABOUTME: Typer CLI providing load, classify, correlate, and report commands.
# flake8: noqa: B008
"""Safety Analysis CLI - data loading, NLP classification, correlation, and reporting."""

import json
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from worldenergydata.common import get_logger

logger = get_logger(__name__)

app = typer.Typer(
    name="safety-analysis",
    help="Safety analysis and HSE data processing",
    no_args_is_help=True,
)
console = Console()


class OutputFormat(str, Enum):
    html = "html"
    json = "json"


class ReportType(str, Enum):
    incident = "incident"
    correlation = "correlation"
    classification = "classification"


def _spinner():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


@app.command()
def load(
    observations: Path = typer.Argument(
        ..., help="Path to observations CSV"
    ),  # noqa: B008
    incidents: Optional[Path] = typer.Option(
        None, "--incidents", "-i", help="Path to incidents CSV"
    ),  # noqa: B008
    schema: Optional[str] = typer.Option(
        None, "--schema", "-s", help="Schema name from registry"
    ),  # noqa: B008
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),  # noqa: B008
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),  # noqa: B008
) -> None:
    """Load and process safety observation/incident data."""
    try:
        with _spinner() as progress:
            task = progress.add_task("[cyan]Loading safety data...", total=100)

            from worldenergydata.modules.safety_analysis.adapters.csv_adapter import (
                CSVAdapter,
            )
            from worldenergydata.modules.safety_analysis.core.schemas import (
                SchemaRegistry,
            )

            progress.update(
                task, advance=20, description="[cyan]Configuring adapter..."
            )
            obs_schema = inc_schema = None
            if schema:
                registry = SchemaRegistry()
                schema_path = Path(schema)
                if schema_path.exists() and schema_path.suffix in (".yaml", ".yml"):
                    registry.load_from_yaml(schema_path)
                    obs_schema = inc_schema = registry.get(schema)

            adapter = CSVAdapter(
                observations_path=observations,
                incidents_path=incidents,
                observation_schema=obs_schema,
                incident_schema=inc_schema,
            )
            progress.update(
                task, advance=30, description="[cyan]Loading observations..."
            )
            obs_df = adapter.load_observations()
            console.print(f"  Observations loaded: [green]{len(obs_df):,}[/green] rows")

            inc_df = None
            if incidents:
                progress.update(
                    task, advance=20, description="[cyan]Loading incidents..."
                )
                inc_df = adapter.load_incidents()
                console.print(
                    f"  Incidents loaded: [green]{len(inc_df):,}[/green] rows"
                )

            progress.update(task, advance=30, description="[cyan]Saving output...")
            output.mkdir(parents=True, exist_ok=True)
            obs_df.to_csv(output / "observations_loaded.csv", index=False)
            if inc_df is not None:
                inc_df.to_csv(output / "incidents_loaded.csv", index=False)

        console.print(
            Panel(
                f"[green]Data loaded successfully[/green]\nOutput: {output}",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def classify(
    data: Path = typer.Argument(..., help="Path to observation data"),  # noqa: B008
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Model name"
    ),  # noqa: B008
    classifier: str = typer.Option(
        "random_forest", "--classifier", "-c", help="Classifier type"
    ),  # noqa: B008
    train: bool = typer.Option(
        False, "--train", help="Train a new model"
    ),  # noqa: B008
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),  # noqa: B008
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),  # noqa: B008
) -> None:
    """Classify safety observations using NLP models."""
    try:
        with _spinner() as progress:
            task = progress.add_task("[cyan]Preparing classification...", total=100)

            from worldenergydata.modules.safety_analysis.data.loaders import (
                SafetyDataLoader,
            )
            from worldenergydata.modules.safety_analysis.nlp import (  # noqa: F401
                ClassificationPipeline,
                TextPreprocessor,
            )

            progress.update(task, advance=20, description="[cyan]Loading data...")
            df = SafetyDataLoader().load(data)
            console.print(f"  Records loaded: [green]{len(df):,}[/green]")

            progress.update(task, advance=20, description="[cyan]Preprocessing text...")
            preprocessor = TextPreprocessor()  # noqa: F841

            if train:
                progress.update(task, advance=30, description="[cyan]Training model...")
                console.print(f"  Classifier: [cyan]{classifier}[/cyan]")

            progress.update(task, advance=30, description="[cyan]Saving results...")
            output.mkdir(parents=True, exist_ok=True)
            summary = {
                "records": len(df),
                "classifier": classifier,
                "trained": train,
                "model_name": model,
            }
            with open(output / "classification_summary.json", "w") as f:
                json.dump(summary, f, indent=2)

        console.print(
            Panel(
                f"[green]Classification complete[/green]\n"
                f"Classifier: {classifier}\nOutput: {output}",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def correlate(
    observations: Path = typer.Argument(
        ..., help="Path to observations data"
    ),  # noqa: B008
    incidents: Path = typer.Argument(..., help="Path to incidents data"),  # noqa: B008
    max_lag: int = typer.Option(
        12, "--max-lag", "-l", help="Maximum lag periods"
    ),  # noqa: B008
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),  # noqa: B008
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),  # noqa: B008
) -> None:
    """Compute observation-incident correlation analysis."""
    try:
        with _spinner() as progress:
            task = progress.add_task("[cyan]Running correlation analysis...", total=100)

            from worldenergydata.modules.safety_analysis.analysis.correlation import (
                LaggedCrossCorrelation,
            )
            from worldenergydata.modules.safety_analysis.data.loaders import (
                SafetyDataLoader,
            )

            progress.update(task, advance=20, description="[cyan]Loading data...")
            loader = SafetyDataLoader()
            obs_df = loader.load(observations)
            inc_df = loader.load(incidents)
            console.print(
                f"  Observations: [green]{len(obs_df):,}[/green],"
                f" Incidents: [green]{len(inc_df):,}[/green]"
            )

            progress.update(
                task, advance=30, description="[cyan]Computing correlations..."
            )
            correlator = LaggedCrossCorrelation(  # noqa: F841
                lag_min=-max_lag, lag_max=max_lag
            )
            console.print(f"  Lag range: [{-max_lag}, {max_lag}]")

            progress.update(task, advance=30, description="[cyan]Saving results...")
            output.mkdir(parents=True, exist_ok=True)
            summary = {
                "observations": len(obs_df),
                "incidents": len(inc_df),
                "max_lag": max_lag,
            }
            with open(output / "correlation_summary.json", "w") as f:
                json.dump(summary, f, indent=2)

        console.print(
            Panel(
                f"[green]Correlation analysis complete[/green]\n"
                f"Max lag: {max_lag}\nOutput: {output}",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def report(
    data: Path = typer.Argument(
        ..., help="Path to analysis results (CSV or JSON)"
    ),  # noqa: B008
    report_type: ReportType = typer.Option(
        ReportType.incident, "--type", "-t", help="Report type"
    ),  # noqa: B008
    output: Path = typer.Option(
        Path("./reports"), "--output", "-o", help="Output directory"
    ),  # noqa: B008
    fmt: OutputFormat = typer.Option(
        OutputFormat.html, "--format", "-f", help="Output format"
    ),  # noqa: B008
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),  # noqa: B008
) -> None:
    """Generate analysis reports."""
    try:
        with _spinner() as progress:
            task = progress.add_task(
                f"[cyan]Generating {report_type.value} report...", total=100
            )

            from worldenergydata.modules.safety_analysis.data.loaders import (
                SafetyDataLoader,
            )

            progress.update(task, advance=20, description="[cyan]Loading data...")
            df = SafetyDataLoader().load(data)
            console.print(f"  Records: [green]{len(df):,}[/green]")

            progress.update(task, advance=30, description="[cyan]Building report...")
            output.mkdir(parents=True, exist_ok=True)

            if report_type == ReportType.incident:
                from worldenergydata.modules.safety_analysis.reports.incident_report import (
                    IncidentReport,
                )

                rpt = IncidentReport.from_dataframe(df)
            elif report_type == ReportType.correlation:
                console.print(
                    "[yellow]Correlation report requires"
                    " CorrelationResult objects. Use Python API.[/yellow]"
                )
                raise typer.Exit(0)
            elif report_type == ReportType.classification:
                console.print(
                    "[yellow]Classification report requires"
                    " evaluation dict. Use Python API.[/yellow]"
                )
                raise typer.Exit(0)
            else:
                raise typer.Exit(1)

            progress.update(task, advance=30, description="[cyan]Writing report...")
            if fmt == OutputFormat.html:
                out_file = output / f"safety_{report_type.value}_report.html"
                rpt.generate_html(out_file)
            else:
                out_file = output / f"safety_{report_type.value}_report.json"
                summary = {
                    "report_type": report_type.value,
                    "sections": len(rpt.sections),
                    "summary_stats": [
                        {"label": s.label, "value": s.value, "unit": s.unit}
                        for s in rpt.summary_stats
                    ],
                }
                with open(out_file, "w") as f:
                    json.dump(summary, f, indent=2)

        console.print(
            Panel(
                f"[green]Report generated[/green]\nType: {report_type.value}\nFile: {out_file}",
                border_style="green",
            )
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command()
def status() -> None:
    """Show safety analysis module status and configuration."""
    from worldenergydata.modules.safety_analysis.config import AnalysisConfig

    config = AnalysisConfig()
    console.print(Panel("[bold]Safety Analysis Module[/bold]", border_style="cyan"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_column("Status", style="dim")

    for label, path in [
        ("Data Directory", config.data_dir),
        ("Model Directory", config.model_dir),
        ("Report Directory", config.report_dir),
    ]:
        exists = (
            "[green]Exists[/green]" if path.exists() else "[yellow]Not found[/yellow]"
        )
        table.add_row(label, str(path), exists)

    table.add_row("Default Frequency", config.default_frequency, "")
    table.add_row("Window Size", str(config.window_size), "")
    table.add_row(
        "Lag Range", f"[{config.correlation.lag_min}, {config.correlation.lag_max}]", ""
    )
    console.print(table)

    dep_table = Table(
        title="Optional Dependencies", show_header=True, header_style="bold"
    )
    dep_table.add_column("Package")
    dep_table.add_column("Status")
    for pkg, label in [
        ("sklearn", "scikit-learn"),
        ("xgboost", "XGBoost"),
        ("statsmodels", "statsmodels"),
    ]:
        try:
            __import__(pkg)
            dep_table.add_row(label, "[green]Installed[/green]")
        except ImportError:
            dep_table.add_row(label, "[yellow]Not installed[/yellow]")

    console.print(dep_table)
    console.print(
        "\n[dim]Use 'worldenergydata safety-analysis --help' for available commands[/dim]"
    )


@app.callback()
def callback() -> None:
    """Safety analysis and HSE data processing."""
