"""Metadata-only Typer groups that load a command family on first dispatch.

Click's "Complex Applications / Lazily Loading Subcommands" documents that
help and completion also call get_command. Returning an unloaded group preserves
those metadata queries; constructing its context is the dispatch boundary.
https://click.palletsprojects.com/en/stable/complex/#lazily-loading-subcommands
"""

from importlib import import_module
from typing import Any

import typer
from typer.core import TyperGroup
from typer.main import get_command


def lazy_app(module_path: str) -> typer.Typer:
    """Register an app by import path while keeping add_typer metadata intact."""

    class CommandFamily(TyperGroup):
        """Expose help metadata immediately and defer the actual child group."""

        _loaded: TyperGroup | None = None

        def _load(self) -> TyperGroup:
            if self._loaded is None:
                # Use normal add_typer conversion to retain child callbacks,
                # context settings, nested commands, and the root help override.
                wrapper = typer.Typer(rich_markup_mode=self.rich_markup_mode)
                wrapper.add_typer(
                    import_module(module_path).app, name=self.name, help=self.help
                )
                self._loaded = get_command(wrapper).commands[self.name]
            return self._loaded

        def make_context(self, *args: Any, **kwargs: Any) -> Any:
            return self._load().make_context(*args, **kwargs)

        def invoke(self, ctx: Any) -> Any:
            # Click versions that invoke the selected proxy (rather than
            # ctx.command) must also execute the loaded group's callback.
            return self._load().invoke(ctx)

        def get_command(self, ctx: Any, cmd_name: str) -> Any:
            return self._load().get_command(ctx, cmd_name)

        def list_commands(self, ctx: Any) -> list[str]:
            return self._load().list_commands(ctx)

        def shell_complete(self, ctx: Any, incomplete: str) -> Any:
            return self._load().shell_complete(ctx, incomplete)

    return typer.Typer(cls=CommandFamily)
