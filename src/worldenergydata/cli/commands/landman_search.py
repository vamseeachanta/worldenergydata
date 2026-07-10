# ABOUTME: Search command for operation-aware fixture-only Landman execution.
# ABOUTME: Emits stable JSON envelopes and preserves table, CSV, and file output.

"""Landman search command registration and execution."""

from pathlib import Path
from typing import Optional

import typer

from worldenergydata.landman.exceptions import LandmanError
from worldenergydata.landman.landman import Landman
from worldenergydata.landman.routing import SourceConfig

from .landman_render import (
    Operation,
    OutputFormat,
    emit_failure,
    emit_search_result,
    record_dicts,
)


def _legal_description(section: str | None, township: str | None, range_: str | None):
    parts = []
    if section:
        parts.append(f"Section {section}")
    if township:
        parts.append(f"T{township}")
    if range_:
        parts.append(f"R{range_}")
    return ", ".join(parts) or None


def _success_payload(result, requested: str, operation: str, source: SourceConfig):
    records = record_dicts(result.ownership_records)
    return {
        "status": "ok",
        "requested_provider": requested,
        "resolved_provider": result.provider,
        "operation": operation,
        "source_mode": source.mode,
        "records": records,
        "total_records": len(records),
        "failures": [],
    }


def _run_search(
    state: str,
    county: str,
    section: str | None,
    township: str | None,
    range_: str | None,
    owner: str | None,
    operation: Operation,
    provider: str,
    output_format: OutputFormat,
    output_file: Path | None,
    verbose: bool,
    sample: bool,
    records_file: str | None,
) -> None:
    try:
        source = SourceConfig.from_keywords(sample, records_file)
        legal = _legal_description(section, township, range_)
        landman = Landman()
        if operation == Operation.ownership:
            result = landman.search_ownership(
                state.upper(),
                county.upper(),
                legal,
                owner,
                provider,
                sample,
                records_file,
            )
            payload = _success_payload(result, provider, operation.value, source)
        else:
            landman.router(
                {
                    "data_types": [operation.value],
                    "provider": provider,
                    "source": {"sample": sample, "records_file": records_file},
                    "state": state.upper(),
                    "county": county.upper(),
                    "search": {"state": state.upper(), "county": county.upper()},
                }
            )
            raise AssertionError(
                "non-ownership provider returned without a result envelope"
            )
        emit_search_result(payload, output_format, output_file)
        if verbose and output_format != OutputFormat.json:
            typer.echo(f"Search ID: {result.search_id}", err=True)
    except LandmanError as error:
        emit_failure(error, provider, operation.value, output_format)
        raise typer.Exit(1)


def register_search_command(app: typer.Typer) -> None:
    @app.command()
    def search(
        state: str = typer.Option(..., "--state", "-s", help="2-letter US state code"),
        county: str = typer.Option(..., "--county", "-c", help="County name"),
        section: Optional[str] = typer.Option(None, "--section", help="Section number"),
        township: Optional[str] = typer.Option(
            None, "--township", "-t", help="Township"
        ),
        range_: Optional[str] = typer.Option(None, "--range", "-r", help="Range"),
        owner: Optional[str] = typer.Option(None, "--owner", "-o", help="Owner name"),
        record_type: Operation = typer.Option(
            Operation.ownership, "--type", help="Record type"
        ),
        provider: str = typer.Option(
            "auto", "--provider", "-p", help="Provider or auto"
        ),
        output_format: OutputFormat = typer.Option(
            OutputFormat.table, "--format", "-f"
        ),
        output_file: Optional[Path] = typer.Option(
            None, "--output", help="Output file"
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
        sample: bool = typer.Option(
            False, "--sample", help="Use packaged public fixture"
        ),
        records_file: Optional[str] = typer.Option(
            None, "--records-file", help="Direct-child JSON fixture"
        ),
    ) -> None:
        """Search mineral and lease records by location."""
        _run_search(
            state,
            county,
            section,
            township,
            range_,
            owner,
            record_type,
            provider,
            output_format,
            output_file,
            verbose,
            sample,
            records_file,
        )
