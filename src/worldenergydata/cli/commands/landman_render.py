# ABOUTME: Output envelopes and renderers shared by Landman CLI commands.
# ABOUTME: Keeps JSON stdout machine-parseable and Rich limited to table mode.

"""Landman CLI output types and rendering helpers."""

import csv
import io
import json
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import typer
from rich.console import Console
from rich.table import Table

from worldenergydata.landman.exceptions import CapabilityUnavailableError, LandmanError


console = Console()


class Operation(str, Enum):
    ownership = "ownership"
    leases = "leases"
    title = "title"
    deeds = "deeds"
    mortgages = "mortgages"
    assignments = "assignments"
    all = "all"


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    csv = "csv"


def emit_json(payload: dict[str, Any], output_file: Path | None = None) -> None:
    """Write one JSON object to stdout and optionally to a file."""
    rendered = json.dumps(payload, indent=2, sort_keys=True, default=str)
    if output_file:
        output_file.write_text(rendered + "\n", encoding="utf-8")
    typer.echo(rendered)


def failure_envelope(
    error: LandmanError, requested_provider: str, operation: str
) -> dict[str, Any]:
    """Convert runtime errors to the stable plural-failure envelope."""
    if isinstance(error, CapabilityUnavailableError):
        return {
            "status": "error",
            "requested_provider": error.requested_provider,
            "resolved_provider": None,
            "failures": error.failures,
        }
    return {
        "status": "error",
        "requested_provider": requested_provider,
        "resolved_provider": None,
        "failures": [
            {
                "operation": operation,
                "code": error.code,
                "candidate_statuses": [],
                "message": error.message,
            }
        ],
    }


def emit_failure(
    error: LandmanError,
    requested_provider: str,
    operation: str,
    output_format: OutputFormat,
) -> None:
    payload = failure_envelope(error, requested_provider, operation)
    if output_format == OutputFormat.json:
        emit_json(payload)
    else:
        typer.echo(f"Error: {error.message}", err=True)


def record_dicts(records: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        record.to_dict() if hasattr(record, "to_dict") else dict(record)
        for record in records
    ]


def _ownership_table(records: list[dict[str, Any]]) -> Table:
    table = Table(title="Ownership Records", header_style="bold cyan")
    table.add_column("Record ID")
    table.add_column("Owner")
    table.add_column("Interest")
    table.add_column("Net Acres", justify="right")
    table.add_column("Legal Description")
    for row in records:
        table.add_row(
            str(row.get("record_id", "-")),
            str(row.get("owner_name", "-")),
            str(row.get("interest_type", "-")),
            str(row.get("net_mineral_acres") or "-"),
            str(row.get("legal_description", "-")),
        )
    return table


def _table_text(records: list[dict[str, Any]]) -> str:
    stream = io.StringIO()
    local_console = Console(file=stream, force_terminal=False, color_system=None)
    local_console.print(_ownership_table(records))
    return stream.getvalue()


def _emit_csv(records: list[dict[str, Any]], output_file: Path | None) -> None:
    fields = list(records[0]) if records else ["record_id"]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    rendered = stream.getvalue()
    if output_file:
        output_file.write_text(rendered, encoding="utf-8")
    else:
        typer.echo(rendered, nl=False)


def emit_search_result(
    payload: dict[str, Any],
    output_format: OutputFormat,
    output_file: Path | None,
) -> None:
    records = payload["records"]
    if output_format == OutputFormat.json:
        emit_json(payload, output_file)
    elif output_format == OutputFormat.csv:
        _emit_csv(records, output_file)
    else:
        rendered = _table_text(records)
        if output_file:
            output_file.write_text(rendered, encoding="utf-8")
        else:
            typer.echo(rendered, nl=False)
        typer.echo(f"Total records found: {len(records)}")


def emit_provider_table(payload: dict[str, Any]) -> None:
    table = Table(title="Landman Providers", header_style="bold cyan")
    table.add_column("Provider")
    table.add_column("Implementation")
    table.add_column("Operations")
    table.add_column("Requirements")
    table.add_column("Routable Now")
    for row in payload["providers"]:
        table.add_row(
            row["name"],
            row["implementation_status"],
            ", ".join(row["router_operations"]) or "-",
            "satisfied" if row["requirements_satisfied"] else "unmet",
            "yes" if row["routable_now"] else "no",
        )
    console.print(table)
