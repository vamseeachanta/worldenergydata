# ABOUTME: Reference and legacy lookup commands for the Landman CLI.
# ABOUTME: Keeps county reference data distinct from executable router providers.

"""Landman county-reference and title lookup commands."""

from typing import Optional

import typer

from worldenergydata.landman.exceptions import LandmanError
from worldenergydata.landman.landman import Landman, LandmanValidationError
from worldenergydata.landman.providers.county_reference import CountyReferenceProvider

from .landman_render import OutputFormat, emit_failure, emit_json


def _run_lookup(
    state: str,
    county: str,
    document_number: str | None,
    book: str | None,
    page: str | None,
    legal_description: str | None,
    output_format: OutputFormat,
    verbose: bool,
) -> None:
    try:
        if not any((document_number, book and page, legal_description)):
            raise LandmanValidationError(
                message=(
                    "Provide --document-number, --book and --page, "
                    "or --legal-description"
                ),
                error_code="LANDMAN_LOOKUP_SELECTOR_REQUIRED",
            )
        records = Landman().get_title_records(
            state.upper(),
            county.upper(),
            legal_description=legal_description,
            document_number=document_number,
        )
        payload = {"status": "ok", "records": [row.to_dict() for row in records]}
        if output_format == OutputFormat.json:
            emit_json(payload)
        else:
            typer.echo(f"Records found: {len(records)}")
    except LandmanError as error:
        emit_failure(error, "auto", "title", output_format)
        raise typer.Exit(1)


def _run_county_info(
    state: str,
    county: str,
    output_format: OutputFormat,
    show_instructions: bool,
    verbose: bool,
) -> None:
    try:
        provider = CountyReferenceProvider()
        info = provider.get_county_clerk_info(state.upper(), county.upper())
        if output_format == OutputFormat.json:
            payload = info.to_dict()
            if show_instructions:
                payload["instructions"] = provider.get_search_instructions(
                    state.upper(), county.upper()
                )
            emit_json(payload)
        else:
            typer.echo(
                f"{info.office_name or 'County Clerk'}\n{info.county} County, {info.state}"
            )
            if info.phone:
                typer.echo(f"Phone: {info.phone}")
        if show_instructions and output_format != OutputFormat.json:
            typer.echo(provider.get_search_instructions(state.upper(), county.upper()))
    except LandmanError as error:
        emit_failure(error, "county_reference", "county_info", output_format)
        raise typer.Exit(1)


def register_reference_commands(app: typer.Typer) -> None:
    @app.command()
    def lookup(
        state: str = typer.Option(..., "--state", "-s", help="2-letter US state code"),
        county: str = typer.Option(..., "--county", "-c", help="County name"),
        document_number: Optional[str] = typer.Option(None, "--document-number", "-d"),
        book: Optional[str] = typer.Option(None, "--book", "-b"),
        page: Optional[str] = typer.Option(None, "--page", "-p"),
        legal_description: Optional[str] = typer.Option(
            None, "--legal-description", "-l"
        ),
        output_format: OutputFormat = typer.Option(
            OutputFormat.table, "--format", "-f"
        ),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
    ) -> None:
        """Look up a title record by document or legal description."""
        _run_lookup(
            state,
            county,
            document_number,
            book,
            page,
            legal_description,
            output_format,
            verbose,
        )

    @app.command("county-info")
    def county_info(
        state: str = typer.Option(..., "--state", "-s", help="2-letter US state code"),
        county: str = typer.Option(..., "--county", "-c", help="County name"),
        output_format: OutputFormat = typer.Option(
            OutputFormat.table, "--format", "-f"
        ),
        show_instructions: bool = typer.Option(False, "--instructions", "-i"),
        verbose: bool = typer.Option(False, "--verbose", "-v"),
    ) -> None:
        """Show embedded county clerk reference information."""
        _run_county_info(state, county, output_format, show_instructions, verbose)
