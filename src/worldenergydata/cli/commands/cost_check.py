"""JSON-only command adapter for the optional cost package."""

import json
from pathlib import Path

import typer


def cost_check(
    scope_file: Path = typer.Argument(..., help="JSON scope file"),
    benchmarks: Path = typer.Option(
        Path("reports/cost/unit_cost_benchmarks.csv"),
        "--benchmarks",
        help="Project unit-cost benchmark CSV",
    ),
) -> None:
    """Return comparable-based scope ranges and quote positions as JSON."""
    from worldenergydata.cost.scope_check import check_scope, load_scope_json

    try:
        try:
            payload = scope_file.read_bytes()
        except OSError:
            raise ValueError("scope JSON file could not be read") from None
        result = check_scope(load_scope_json(payload), benchmarks)
    except (ValueError, UnicodeError, FileNotFoundError) as error:
        typer.echo(json.dumps({"error": str(error)}, allow_nan=False))
        raise typer.Exit(code=1) from error
    except OSError as error:
        typer.echo(json.dumps({"error": "benchmark table could not be read"}))
        raise typer.Exit(code=1) from error
    typer.echo(json.dumps(result, allow_nan=False))
