"""HSE incident queries against an explicitly selected database or demo."""

import typer
from sqlalchemy.exc import SQLAlchemyError

app = typer.Typer(help="Query HSE records", no_args_is_help=True)
incidents_app = typer.Typer(help="Query incidents", no_args_is_help=True)
app.add_typer(incidents_app, name="incidents")


@incidents_app.command("query")
def query_incidents(
    operator: str | None = typer.Option(None, help="Exact operator name"),
    year: int | None = typer.Option(None, help="Incident calendar year"),
    severity: str | None = typer.Option(None, help="Stored incident severity"),
    source: str | None = typer.Option(None, help="bsee_inc or osha"),
    database_url: str | None = typer.Option(None, envvar="HSE_DATABASE_URL"),
    demo: bool = typer.Option(False, help="Use labeled synthetic data"),
    output: str = typer.Option("json", help="json or csv"),
):
    """Return matching records; configured database errors never select samples."""
    from worldenergydata.hse.api import HSEApi, HSEQueryConfig, IncidentsQuery

    if output not in {"json", "csv"}:
        raise typer.BadParameter("output must be json or csv")
    if demo == (database_url is not None):
        raise typer.BadParameter("Select --database-url or --demo")
    filters = {
        "operator": operator,
        "year": year,
        "severity": severity,
        "source": source,
    }
    try:
        if demo:
            query = IncidentsQuery()
            try:
                frame = query.query(**filters)
            finally:
                query.close()
            typer.echo("Synthetic demonstration data.", err=True)
        else:
            with HSEApi(HSEQueryConfig(database_url=database_url)) as client:
                frame = client.incidents.query(**filters)
    except (SQLAlchemyError, ValueError, FileNotFoundError):
        # Database exceptions may contain credentials or local filesystem details.
        typer.echo(
            "HSE query failed; check the database schema and query options.", err=True
        )
        raise typer.Exit(code=1) from None
    text = (
        frame.to_json(orient="records", date_format="iso")
        if output == "json"
        else frame.to_csv(index=False)
    )
    typer.echo(text.strip())
