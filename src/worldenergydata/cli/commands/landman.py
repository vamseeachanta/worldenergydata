# ABOUTME: Thin Typer registration surface for the independently executable Landman CLI.
# ABOUTME: Keeps root CLI integration stable without importing the root command dispatcher.

"""Landman command group and standalone module entry point."""

import typer

from .landman_reference import register_reference_commands
from .landman_search import register_search_command
from .landman_status import register_status_commands


app = typer.Typer(
    name="landman",
    help="Mineral ownership and lease data operations",
    no_args_is_help=True,
)

register_search_command(app)
register_reference_commands(app)
register_status_commands(app)


@app.callback()
def callback() -> None:
    """Mineral ownership and lease data operations."""


if __name__ == "__main__":
    app()
