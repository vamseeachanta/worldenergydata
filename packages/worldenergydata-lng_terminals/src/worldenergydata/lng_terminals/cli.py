"""CLI for the LNG Terminals module.

Usage:
    uv run python -m worldenergydata.lng_terminals.cli collect
    uv run python -m worldenergydata.lng_terminals.cli collect --refresh-mode full
    uv run python -m worldenergydata.lng_terminals.cli process
    uv run python -m worldenergydata.lng_terminals.cli export
    uv run python -m worldenergydata.lng_terminals.cli report
    uv run python -m worldenergydata.lng_terminals.cli pipeline
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer

from .analysis.capacity_analysis import CapacityAnalysis
from .analysis.timeline_analysis import TimelineAnalysis
from .collectors.seed_collector import SeedCollector
from .config import PROCESSED_DIR, REPORTS_DIR
from .constants import RefreshMode
from .exporters.csv_exporter import CSVExporter
from .models.terminal import LNGTerminal
from .processors.deduplicator import Deduplicator
from .processors.enricher import Enricher
from .processors.normalizer import Normalizer
from .processors.quality_scorer import QualityScorer
from .reports.quality_dashboard import QualityDashboard

app = typer.Typer(
    name="lng-terminals",
    help="Global LNG Terminal Dataset with Engineering Design Data",
)

logger = logging.getLogger(__name__)

# Typer enum choices for --refresh-mode
_REFRESH_MODE_HELP = (
    "Data refresh strategy: "
    "full (re-fetch everything), "
    "incremental (only new/updated), "
    "cache_first (use cache if valid, else fetch), "
    "force_cache (cache only, error if missing)"
)


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _resolve_refresh_mode(mode_str: str) -> RefreshMode:
    """Convert CLI string to RefreshMode enum."""
    return RefreshMode(mode_str)


@app.command()
def collect(
    refresh_mode: str = typer.Option(  # noqa: B008
        "cache_first",
        "--refresh-mode",
        "-r",
        help=_REFRESH_MODE_HELP,
    ),
    verbose: bool = typer.Option(  # noqa: B008
        False, "--verbose", "-v", help="Enable debug logging"
    ),
) -> list[LNGTerminal]:
    """Collect LNG terminal data from all sources."""
    _setup_logging(verbose)
    mode = _resolve_refresh_mode(refresh_mode)
    typer.echo(f"Collecting LNG terminal data (mode={mode.value})...")

    # Seed collector (always available — ignores cache since it's embedded)
    seed = SeedCollector(refresh_mode=RefreshMode.FULL)
    terminals = seed.collect()
    typer.echo(f"  Seed: {len(terminals)} terminals")

    # Try FERC (if configured)
    try:
        from .collectors.ferc_collector import FERCCollector

        ferc = FERCCollector(refresh_mode=mode)
        ferc_terminals = ferc.collect()
        if ferc_terminals:
            enricher = Enricher()
            terminals = enricher.enrich(terminals, ferc_terminals, source_name="ferc")
            typer.echo(f"  FERC: {len(ferc_terminals)} terminals")
    except Exception as e:
        logger.debug(f"FERC collection skipped: {e}")

    # Try GIE (if configured)
    try:
        from .collectors.gie_collector import GIECollector

        gie = GIECollector(refresh_mode=mode)
        gie_terminals = gie.collect()
        if gie_terminals:
            enricher = Enricher()
            terminals = enricher.enrich(terminals, gie_terminals, source_name="gie")
            typer.echo(f"  GIE: {len(gie_terminals)} terminals")
    except Exception as e:
        logger.debug(f"GIE collection skipped: {e}")

    # Try GIIGNL (if configured)
    try:
        from .collectors.giignl_collector import GIIGNLCollector

        giignl = GIIGNLCollector(refresh_mode=mode)
        giignl_terminals = giignl.collect()
        if giignl_terminals:
            enricher = Enricher()
            terminals = enricher.enrich(
                terminals, giignl_terminals, source_name="giignl"
            )
            typer.echo(f"  GIIGNL: {len(giignl_terminals)} terminals")
    except Exception as e:
        logger.debug(f"GIIGNL collection skipped: {e}")

    typer.echo(f"Total collected: {len(terminals)} terminals")
    return terminals


@app.command()
def process(
    refresh_mode: str = typer.Option(  # noqa: B008
        "cache_first",
        "--refresh-mode",
        "-r",
        help=_REFRESH_MODE_HELP,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),  # noqa: B008
) -> list[LNGTerminal]:
    """Collect and process LNG terminal data."""
    _setup_logging(verbose)
    terminals = collect(refresh_mode=refresh_mode, verbose=verbose)

    typer.echo("\nProcessing...")

    # Normalize
    normalizer = Normalizer()
    terminals = normalizer.normalize_terminals(terminals)
    typer.echo(f"  Normalized: {len(terminals)} terminals")

    # Deduplicate
    dedup = Deduplicator()
    terminals = dedup.deduplicate(terminals)
    typer.echo(f"  Deduplicated: {len(terminals)} terminals")

    # Score quality
    scorer = QualityScorer()
    terminals = scorer.score_terminals(terminals)
    typer.echo("  Quality scores computed")

    return terminals


@app.command()
def export(
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o"),  # noqa: B008
    formats: str = typer.Option(  # noqa: B008
        "csv", "--formats", "-f", help="Comma-separated: csv,parquet"
    ),
    refresh_mode: str = typer.Option(  # noqa: B008
        "cache_first",
        "--refresh-mode",
        "-r",
        help=_REFRESH_MODE_HELP,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),  # noqa: B008
) -> None:
    """Collect, process, and export LNG terminal data."""
    _setup_logging(verbose)
    terminals = process(refresh_mode=refresh_mode, verbose=verbose)

    out_dir = output_dir or PROCESSED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt_list = [f.strip() for f in formats.split(",")]

    typer.echo(f"\nExporting to {out_dir}...")

    if "csv" in fmt_list:
        csv_exp = CSVExporter(output_dir=out_dir)
        path = csv_exp.export(terminals)
        typer.echo(f"  CSV: {path}")
        meta_path = csv_exp.export_metadata(terminals)
        typer.echo(f"  Metadata: {meta_path}")

    if "parquet" in fmt_list:
        try:
            from .exporters.parquet_exporter import ParquetExporter

            pq_exp = ParquetExporter(output_dir=out_dir)
            path = pq_exp.export(terminals)
            typer.echo(f"  Parquet: {path}")
        except Exception as e:
            typer.echo(f"  Parquet export skipped: {e}", err=True)


@app.command()
def report(
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o"),  # noqa: B008
    refresh_mode: str = typer.Option(  # noqa: B008
        "cache_first",
        "--refresh-mode",
        "-r",
        help=_REFRESH_MODE_HELP,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),  # noqa: B008
) -> None:
    """Generate analysis reports."""
    _setup_logging(verbose)
    terminals = process(refresh_mode=refresh_mode, verbose=verbose)

    out_dir = output_dir or REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    typer.echo("\nGenerating reports...")

    # Capacity analysis
    cap = CapacityAnalysis(terminals)
    summary = cap.summary()
    typer.echo(f"  Total capacity: {summary['total_capacity_mtpa']:.1f} MTPA")
    typer.echo(
        f"  Top country: {summary['top_countries'][0]['country']} "
        f"({summary['top_countries'][0]['capacity_mtpa']:.1f} MTPA)"
    )

    # Timeline analysis
    timeline = TimelineAnalysis(terminals)
    t_summary = timeline.summary()
    uc = t_summary["under_construction"]
    typer.echo(f"  Under construction: {len(uc)} terminals")

    # Quality dashboard
    dashboard = QualityDashboard(terminals)
    qr_path = dashboard.export_json(output_path=out_dir / "quality_report.json")
    typer.echo(f"  Quality report: {qr_path}")

    # Terminal map (optional, needs plotly)
    try:
        from .reports.terminal_map import TerminalMap

        tmap = TerminalMap(terminals)
        map_path = tmap.generate(output_path=out_dir / "terminal_map.html")
        typer.echo(f"  Terminal map: {map_path}")
    except ImportError:
        typer.echo("  Map skipped (plotly not installed)", err=True)


@app.command()
def pipeline(
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o"),  # noqa: B008
    refresh_mode: str = typer.Option(  # noqa: B008
        "cache_first",
        "--refresh-mode",
        "-r",
        help=_REFRESH_MODE_HELP,
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v"),  # noqa: B008
) -> None:
    """Run the full pipeline: collect -> process -> export -> report."""
    _setup_logging(verbose)
    export(
        output_dir=output_dir, formats="csv", refresh_mode=refresh_mode, verbose=verbose
    )
    report(output_dir=output_dir, refresh_mode=refresh_mode, verbose=verbose)
    typer.echo("\nPipeline complete!")


def main() -> None:
    """Entry point for direct module execution."""
    app()


if __name__ == "__main__":
    main()
