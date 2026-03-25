"""
Dashboard CLI command — launch the Plotly Dash web application.

Usage:
    worldenergydata dashboard [--port 8050] [--host 127.0.0.1] [--debug]

The server starts on localhost by default and opens at
http://127.0.0.1:<port>/
"""

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()

app = typer.Typer(
    name="dashboard",
    help="Launch the Plotly Dash BSEE/FDAS web dashboard",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def dashboard(
    port: int = typer.Option(8050, "--port", "-p", help="TCP port to listen on"),
    host: str = typer.Option(
        "127.0.0.1", "--host", help="Bind address (default: localhost)"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable Dash debug mode"),
) -> None:
    """Start the interactive GOM dashboard (BSEE production + FDAS incidents)."""
    from worldenergydata.dashboard.app import run_server

    console.print(
        Panel(
            f"[bold cyan]WorldEnergyData Dashboard[/bold cyan]\n"
            f"Open [link=http://{host}:{port}/]http://{host}:{port}/[/link] "
            f"in your browser.\n\n"
            f"[dim]Press Ctrl+C to stop the server.[/dim]",
            border_style="cyan",
        )
    )
    run_server(host=host, port=port, debug=debug)
