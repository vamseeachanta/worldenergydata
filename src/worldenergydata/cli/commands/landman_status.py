# ABOUTME: Contextual provider readiness and module status commands for Landman.
# ABOUTME: Reports implementation state separately from fixture requirements.

"""Landman providers and status command registration."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from worldenergydata.landman.exceptions import LandmanError
from worldenergydata.landman.providers.county_reference import CountyReferenceProvider
from worldenergydata.landman.providers.registry import provider_status_payload
from worldenergydata.landman.routing import SourceConfig

from .landman_render import (
    Operation,
    OutputFormat,
    emit_failure,
    emit_json,
    emit_provider_table,
)


def _payload(operation: Operation, sample: bool, records_file: str | None):
    source = SourceConfig.from_keywords(sample, records_file)
    return provider_status_payload(operation.value, source)


def _county_rows(state: str | None, online_only: bool):
    provider = CountyReferenceProvider()
    return [
        row.to_dict()
        for row in provider.search_counties(state=state, online_only=online_only)
    ]


def _run_providers(
    state: str | None,
    online_only: bool,
    output_format: OutputFormat,
    verbose: bool,
    operation: Operation,
    sample: bool,
    records_file: str | None,
) -> None:
    try:
        payload = _payload(operation, sample, records_file)
        if state or online_only or verbose:
            payload["county_reference"] = _county_rows(state, online_only)
        if output_format == OutputFormat.json:
            emit_json(payload)
        elif output_format == OutputFormat.csv:
            typer.echo("name,implementation_status,routable_now")
            for row in payload["providers"]:
                typer.echo(
                    f"{row['name']},{row['implementation_status']},{row['routable_now']}"
                )
        else:
            emit_provider_table(payload)
    except LandmanError as error:
        emit_failure(error, "auto", operation.value, output_format)
        raise typer.Exit(1)


def _data_status(path: Path) -> dict:
    files = (
        [item for item in path.rglob("*") if item.is_file()] if path.exists() else []
    )
    latest = max((item.stat().st_mtime for item in files), default=None)
    return {
        "path": str(path),
        "file_count": len(files),
        "size_bytes": sum(item.stat().st_size for item in files),
        "last_updated": datetime.fromtimestamp(latest).isoformat() if latest else None,
    }


def _run_status(
    data_path: Path,
    verbose: bool,
    output_format: OutputFormat,
    operation: Operation,
    sample: bool,
    records_file: str | None,
) -> None:
    try:
        payload = _payload(operation, sample, records_file)
        payload.update({"module_loaded": True, "data": _data_status(data_path)})
        if output_format == OutputFormat.json:
            emit_json(payload)
        else:
            emit_provider_table(payload)
            typer.echo(f"Data files: {payload['data']['file_count']}")
            if verbose:
                typer.echo(f"Data path: {payload['data']['path']}")
    except LandmanError as error:
        emit_failure(error, "auto", operation.value, output_format)
        raise typer.Exit(1)


def register_status_commands(app: typer.Typer) -> None:
    @app.command()
    def providers(
        state: Optional[str] = typer.Option(None, "--state", "-s"),
        online_only: bool = typer.Option(False, "--online-only"),
        output_format: OutputFormat = typer.Option(
            OutputFormat.table, "--format", "-f"
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
        operation: Operation = typer.Option(Operation.ownership, "--operation"),
        sample: bool = typer.Option(False, "--sample"),
        records_file: Optional[str] = typer.Option(None, "--records-file"),
    ) -> None:
        """List provider implementation and contextual readiness."""
        _run_providers(
            state, online_only, output_format, verbose, operation, sample, records_file
        )

    @app.command()
    def status(
        data_path: Path = typer.Option(Path("./data/landman"), "--data-path", "-d"),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
        output_format: OutputFormat = typer.Option(
            OutputFormat.table, "--format", "-f"
        ),
        operation: Operation = typer.Option(Operation.ownership, "--operation"),
        sample: bool = typer.Option(False, "--sample"),
        records_file: Optional[str] = typer.Option(None, "--records-file"),
    ) -> None:
        """Show module state and contextual provider readiness."""
        _run_status(data_path, verbose, output_format, operation, sample, records_file)
