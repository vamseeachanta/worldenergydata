# ABOUTME: Typer CLI for HSE Risk Index computation, dashboard, and export.
# flake8: noqa: B008
"""HSE Risk Index CLI - compute scores, generate dashboards, and export data."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="risk-index",
    help="HSE Risk Index computation and visualization.",
    no_args_is_help=True,
)
console = Console()


# ------------------------------------------------------------------
# Shared helpers
# ------------------------------------------------------------------


def _spinner() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    )


def _load_and_score(
    data_dir: str,
) -> Tuple[Any, List[Dict[str, Any]]]:
    """Load data from all available sources and compute risk scores.

    Returns:
        Tuple of (metrics DataFrame, list of score dicts).

    Raises:
        typer.Exit: If no data sources are found or scoring fails.
    """
    import pandas as pd

    from worldenergydata.safety_analysis.risk_index.data_assembler import (
        DataAssembler,
    )
    from worldenergydata.safety_analysis.risk_index.models import (
        RiskCategory,
    )
    from worldenergydata.safety_analysis.risk_index.normalizer import (
        normalize_to_scale,
    )

    root = Path(data_dir)
    assembler = DataAssembler()
    sources: Dict[str, pd.DataFrame] = {}

    # --- Attempt to load each source ---
    # BSEE
    bsee_path = root / "hse" / "bsee" / "mv_acc_investigations.txt"
    if not bsee_path.exists():
        bsee_path = root / "hse" / "raw" / "bsee" / "mv_acc_investigations.txt"
    if bsee_path.exists():
        console.print(f"  Loading BSEE from [dim]{bsee_path}[/dim]")
        sources["bsee"] = assembler.load_bsee_incidents(bsee_path)

    # OSHA
    osha_acc = root / "hse" / "osha" / "osha_accident.csv"
    if not osha_acc.exists():
        osha_acc = root / "hse" / "raw" / "osha" / "osha_accident.csv"
    if osha_acc.exists():
        osha_inj = osha_acc.parent / "osha_accident_injury.csv"
        inj_path = osha_inj if osha_inj.exists() else None
        console.print(f"  Loading OSHA from [dim]{osha_acc}[/dim]")
        sources["osha"] = assembler.load_osha_accidents(osha_acc, inj_path)

    # Marine Safety
    marine_db = root / "marine_safety" / "marine_safety.db"
    if not marine_db.exists():
        marine_db = root / "marine_safety" / "processed" / "marine_safety.db"
    if marine_db.exists():
        console.print(f"  Loading Marine Safety from [dim]{marine_db}[/dim]")
        sources["marine_safety"] = assembler.load_marine_incidents(marine_db)

    # PHMSA
    phmsa_dir = root / "pipeline_safety" / "raw" / "phmsa"
    if not phmsa_dir.exists():
        phmsa_dir = root / "hse" / "phmsa"
    if phmsa_dir.exists() and any(phmsa_dir.glob("*.xlsx")):
        console.print(f"  Loading PHMSA from [dim]{phmsa_dir}[/dim]")
        sources["phmsa"] = assembler.load_phmsa_incidents(phmsa_dir)

    # EPA TRI
    tri_path = root / "hse" / "epa_tri" / "tri_combined.csv"
    if not tri_path.exists():
        tri_path = root / "hse" / "raw" / "epa_tri" / "tri_combined.csv"
    if tri_path.exists():
        console.print(f"  Loading EPA TRI from [dim]{tri_path}[/dim]")
        sources["epa_tri"] = assembler.load_epa_tri(tri_path)

    if not sources:
        console.print(
            "[yellow]No data sources found.[/yellow] "
            f"Searched in: {root / 'hse'}, {root / 'marine_safety'}, "
            f"{root / 'pipeline_safety'}"
        )
        raise typer.Exit(1)

    console.print(
        f"  Sources loaded: [green]{len(sources)}[/green] "
        f"({', '.join(sorted(sources))})"
    )

    # --- Assemble metrics ---
    metrics = assembler.assemble(sources)

    if len(metrics) == 0:
        console.print("[yellow]No activities found after assembly.[/yellow]")
        raise typer.Exit(1)

    # --- Compute dimension scores and composite ---
    fatality_scores = normalize_to_scale(metrics["fatality_rate"])
    injury_scores = normalize_to_scale(metrics["injury_rate"])
    weighted_scores = normalize_to_scale(metrics["weighted_incident_count"])
    chronic_scores = normalize_to_scale(metrics["tri_carcinogen_lbs"])
    compliance_scores = normalize_to_scale(metrics["inc_rate"])

    # Acute dimension: weighted combination
    acute_raw = 0.40 * fatality_scores + 0.35 * injury_scores + 0.25 * weighted_scores
    # Clamp to [1, 10]
    import numpy as np

    acute_clamped = np.clip(np.round(acute_raw), 1, 10)
    chronic_clamped = chronic_scores.fillna(1.0)
    compliance_clamped = compliance_scores.fillna(1.0)

    # Composite: 0.50 * Acute + 0.25 * Chronic + 0.25 * Compliance
    composite_raw = (
        0.50 * acute_clamped + 0.25 * chronic_clamped + 0.25 * compliance_clamped
    )
    composite_final = np.clip(np.round(composite_raw), 1, 10).astype(float)

    # Build score dicts
    score_records: List[Dict[str, Any]] = []
    for idx, row in metrics.iterrows():
        a_score = (
            float(acute_clamped.iloc[idx])
            if not np.isnan(acute_clamped.iloc[idx])
            else 1.0
        )
        c_score = float(chronic_clamped.iloc[idx])
        co_score = float(compliance_clamped.iloc[idx])
        comp = float(composite_final.iloc[idx])
        cat = RiskCategory.from_score(comp)

        score_records.append(
            {
                "activity_code": row["activity_code"],
                "activity_name": row["activity_name"],
                "acute_score": a_score,
                "chronic_score": c_score,
                "compliance_score": co_score,
                "composite_score": comp,
                "category": cat.value,
                "incident_count": int(row["total_incidents"]),
                "confidence": row["confidence"],
                "sources": row["sources"] if isinstance(row["sources"], list) else [],
            }
        )

    return metrics, score_records


def _print_summary_table(score_records: List[Dict[str, Any]]) -> None:
    """Print a Rich summary table of risk scores."""
    table = Table(
        title="HSE Risk Scores",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Activity", style="cyan")
    table.add_column("Acute", justify="right")
    table.add_column("Chronic", justify="right")
    table.add_column("Compliance", justify="right")
    table.add_column("Composite", justify="right", style="bold")
    table.add_column("Category")
    table.add_column("Incidents", justify="right")
    table.add_column("Confidence")

    category_styles = {
        "low": "[green]LOW[/green]",
        "medium": "[yellow]MEDIUM[/yellow]",
        "high": "[red]HIGH[/red]",
        "critical": "[bold magenta]CRITICAL[/bold magenta]",
    }

    for rec in sorted(score_records, key=lambda r: r["composite_score"], reverse=True):
        cat_display = category_styles.get(rec["category"], rec["category"])
        table.add_row(
            rec["activity_name"][:40],
            f"{rec['acute_score']:.0f}",
            f"{rec['chronic_score']:.0f}",
            f"{rec['compliance_score']:.0f}",
            f"{rec['composite_score']:.0f}",
            cat_display,
            f"{rec['incident_count']:,}",
            rec["confidence"],
        )

    console.print(table)


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------


@app.command()
def compute(
    output: str = typer.Option(
        "output/hse/risk_scores.csv", help="Output CSV path"
    ),  # noqa: B008
    data_dir: str = typer.Option(
        "data/modules", help="Root data directory"
    ),  # noqa: B008
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),  # noqa: B008
) -> None:
    """Compute risk scores for all activities and export to CSV."""
    try:
        import pandas as pd

        with _spinner() as progress:
            task = progress.add_task("[cyan]Computing risk scores...", total=100)

            progress.update(
                task, advance=20, description="[cyan]Loading data sources..."
            )
            metrics, score_records = _load_and_score(data_dir)

            progress.update(task, advance=50, description="[cyan]Writing CSV...")
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            scores_df = pd.DataFrame(score_records)
            scores_df.to_csv(out_path, index=False)

            progress.update(task, advance=30, description="[cyan]Done")

        _print_summary_table(score_records)
        console.print(
            Panel(
                f"[green]Risk scores computed[/green]\n"
                f"Activities: {len(score_records)}\n"
                f"Output: {out_path}",
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
def dashboard(
    output: str = typer.Option(
        "reports/hse/wrk014_hse_risk_index.html", help="Output HTML path"
    ),  # noqa: B008
    data_dir: str = typer.Option(
        "data/modules", help="Root data directory"
    ),  # noqa: B008
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),  # noqa: B008
) -> None:
    """Generate interactive HTML risk dashboard."""
    try:
        with _spinner() as progress:
            task = progress.add_task("[cyan]Building risk dashboard...", total=100)

            progress.update(
                task, advance=20, description="[cyan]Loading data sources..."
            )
            metrics, score_records = _load_and_score(data_dir)

            progress.update(
                task,
                advance=30,
                description="[cyan]Generating methodology section...",
            )
            from worldenergydata.safety_analysis.risk_index.methodology import (
                generate_methodology_html,
            )

            meta = {
                "timestamp": datetime.now(timezone.utc),
                "version": "1.0",
                "activities": len(score_records),
            }
            methodology_html = generate_methodology_html(metadata=meta)

            progress.update(
                task, advance=30, description="[cyan]Writing HTML dashboard..."
            )
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            html = _build_dashboard_html(score_records, methodology_html)
            out_path.write_text(html, encoding="utf-8")

            progress.update(task, advance=20, description="[cyan]Done")

        _print_summary_table(score_records)
        console.print(
            Panel(
                f"[green]Dashboard generated[/green]\n"
                f"Activities: {len(score_records)}\n"
                f"Output: {out_path}",
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


@app.command("export")
def export_cmd(
    format: str = typer.Option(
        "csv", help="Export format: csv, json, or parquet"
    ),  # noqa: B008
    output: str = typer.Option(
        "output/hse/risk_scores", help="Output path (extension auto-added)"
    ),  # noqa: B008
    data_dir: str = typer.Option(
        "data/modules", help="Root data directory"
    ),  # noqa: B008
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),  # noqa: B008
) -> None:
    """Export risk scores in various formats."""
    valid_formats = {"csv", "json", "parquet"}
    if format not in valid_formats:
        console.print(
            f"[red]Invalid format:[/red] '{format}'. "
            f"Choose from: {', '.join(sorted(valid_formats))}"
        )
        raise typer.Exit(1)

    try:
        import pandas as pd

        with _spinner() as progress:
            task = progress.add_task(
                f"[cyan]Exporting risk scores ({format})...", total=100
            )

            progress.update(
                task, advance=20, description="[cyan]Loading data sources..."
            )
            metrics, score_records = _load_and_score(data_dir)

            progress.update(
                task,
                advance=40,
                description=f"[cyan]Writing {format} file...",
            )
            scores_df = pd.DataFrame(score_records)

            out_base = Path(output)
            out_base.parent.mkdir(parents=True, exist_ok=True)

            if format == "csv":
                out_path = out_base.with_suffix(".csv")
                scores_df.to_csv(out_path, index=False)
            elif format == "json":
                out_path = out_base.with_suffix(".json")
                scores_df.to_json(out_path, orient="records", indent=2)
            elif format == "parquet":
                out_path = out_base.with_suffix(".parquet")
                scores_df.to_parquet(out_path, index=False)
            else:
                raise typer.Exit(1)

            progress.update(task, advance=40, description="[cyan]Done")

        _print_summary_table(score_records)
        console.print(
            Panel(
                f"[green]Export complete[/green]\n"
                f"Format: {format}\n"
                f"Activities: {len(score_records)}\n"
                f"Output: {out_path}",
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


# ------------------------------------------------------------------
# Dashboard HTML builder
# ------------------------------------------------------------------


def _build_dashboard_html(
    score_records: List[Dict[str, Any]],
    methodology_html: str,
) -> str:
    """Build a complete HTML dashboard page with scores and methodology."""
    timestamp = datetime.now(timezone.utc).isoformat()
    n_activities = len(score_records)

    # Count by category
    cat_counts: Dict[str, int] = {}
    for rec in score_records:
        cat = rec["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    # Build score table rows
    cat_colors = {
        "low": "#27ae60",
        "medium": "#f39c12",
        "high": "#e74c3c",
        "critical": "#8e44ad",
    }
    sorted_scores = sorted(
        score_records, key=lambda r: r["composite_score"], reverse=True
    )
    rows_html = []
    for rec in sorted_scores:
        color = cat_colors.get(rec["category"], "#666")
        rows_html.append(
            "<tr>"
            f"<td>{rec['activity_name']}</td>"
            f"<td style='text-align:right'>{rec['acute_score']:.0f}</td>"
            f"<td style='text-align:right'>{rec['chronic_score']:.0f}</td>"
            f"<td style='text-align:right'>{rec['compliance_score']:.0f}</td>"
            f"<td style='text-align:right;font-weight:bold'>"
            f"{rec['composite_score']:.0f}</td>"
            f"<td><span style='background:{color};color:#fff;"
            f"padding:2px 8px;border-radius:3px;font-size:0.85rem'>"
            f"{rec['category'].upper()}</span></td>"
            f"<td style='text-align:right'>{rec['incident_count']:,}</td>"
            f"<td>{rec['confidence']}</td>"
            "</tr>"
        )

    score_table = "\n".join(rows_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HSE Risk Index Dashboard</title>
<style>
body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    margin: 0; padding: 0;
    background: #f5f6fa; color: #1a1a2e;
}}
.container {{ max-width: 1100px; margin: 0 auto; padding: 2rem; }}
h1 {{ color: #0f3460; border-bottom: 3px solid #0f3460;
     padding-bottom: 0.5rem; }}
.summary-cards {{
    display: flex; gap: 1rem; margin: 1.5rem 0; flex-wrap: wrap;
}}
.card {{
    flex: 1; min-width: 140px; padding: 1rem 1.2rem;
    border-radius: 8px; color: #fff; text-align: center;
}}
.card h3 {{ margin: 0 0 0.3rem; font-size: 2rem; }}
.card p {{ margin: 0; font-size: 0.9rem; opacity: 0.9; }}
table {{
    width: 100%; border-collapse: collapse; margin: 1.5rem 0;
    background: #fff; border-radius: 6px; overflow: hidden;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}}
th {{ background: #0f3460; color: #fff; padding: 0.7rem 0.8rem;
     text-align: left; }}
td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #eee; }}
tr:hover {{ background: #f4f4f8; }}
.meta {{ font-size: 0.85rem; color: #888; margin-top: 2rem; }}
</style>
</head>
<body>
<div class="container">
<h1>HSE Risk Index Dashboard</h1>
<p>Risk scores for <strong>{n_activities}</strong> activities across
{sum(cat_counts.values())} total classifications.</p>

<div class="summary-cards">
    <div class="card" style="background:#27ae60">
        <h3>{cat_counts.get('low', 0)}</h3><p>Low Risk</p>
    </div>
    <div class="card" style="background:#f39c12">
        <h3>{cat_counts.get('medium', 0)}</h3><p>Medium Risk</p>
    </div>
    <div class="card" style="background:#e74c3c">
        <h3>{cat_counts.get('high', 0)}</h3><p>High Risk</p>
    </div>
    <div class="card" style="background:#8e44ad">
        <h3>{cat_counts.get('critical', 0)}</h3><p>Critical Risk</p>
    </div>
</div>

<h2>Activity Risk Scores</h2>
<table>
<thead>
<tr>
    <th>Activity</th>
    <th>Acute</th>
    <th>Chronic</th>
    <th>Compliance</th>
    <th>Composite</th>
    <th>Category</th>
    <th>Incidents</th>
    <th>Confidence</th>
</tr>
</thead>
<tbody>
{score_table}
</tbody>
</table>

<hr style="margin: 2rem 0; border: none; border-top: 1px solid #ddd;">

{methodology_html}

<p class="meta">Generated: {timestamp}</p>
</div>
</body>
</html>"""


@app.callback()
def callback() -> None:
    """HSE Risk Index computation and visualization."""
