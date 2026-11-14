"""Resolve only the selected command family, keeping root help import-free."""

from importlib import import_module
from typing import Any

import typer
from typer.core import TyperGroup
from typer.main import get_command

from worldenergydata.cli.registry import COMMAND_FAMILIES, CommandFamily


class LazyFamilyProxy(TyperGroup):
    """Expose static help until parsing or completion actually uses a family.

    TyperGroup inherits the Click implementation used by the installed Typer,
    including versions that vendor Click rather than importing it separately.
    """

    def __init__(self, name: str, family: CommandFamily) -> None:
        super().__init__(name=name, help=family.help, short_help=family.help)
        self.family = family
        self.registry_name = name
        self._command: TyperGroup | None = None

    def _load(self) -> TyperGroup:
        if self._command is None:
            module = import_module(self.family.module)
            # Build through add_typer just as eager registration did: this keeps
            # single-command families grouped, applies registration help/name,
            # and leaves completion flags on the root only. No app is mutated.
            wrapper = typer.Typer(rich_markup_mode="rich")
            wrapper.add_typer(
                getattr(module, self.family.attr),
                name=self.registry_name,
                help=self.family.help,
            )
            group = get_command(wrapper)
            assert isinstance(group, TyperGroup)
            real = group.commands[self.registry_name]
            assert isinstance(real, TyperGroup)
            real.name = self.registry_name
            self._command = real
        return self._command

    def make_context(
        self, info_name: Any, args: Any, parent: Any = None, **extra: Any
    ) -> Any:
        return self._load().make_context(info_name, args, parent=parent, **extra)

    def invoke(self, ctx: Any) -> Any:
        return self._load().invoke(ctx)

    def get_help(self, ctx: Any) -> str:
        return self._load().get_help(ctx)

    def format_help(self, ctx: Any, formatter: Any) -> None:
        self._load().format_help(ctx, formatter)

    def shell_complete(self, ctx: Any, incomplete: str) -> Any:
        return self._load().shell_complete(ctx, incomplete)


class LazyDispatchGroup(TyperGroup):
    """List registered names without importing any command implementation."""

    def list_commands(self, ctx: Any) -> list[str]:
        eager = [name for name in self.commands if name not in COMMAND_FAMILIES]
        return [*eager, *COMMAND_FAMILIES]

    def get_command(self, ctx: Any, cmd_name: str) -> Any:
        if cmd_name in COMMAND_FAMILIES:
            # Click/Typer may ask repeatedly while formatting help or completing.
            # Cache on this group, not globally across independent invocations.
            if cmd_name not in self.commands:
                self.commands[cmd_name] = LazyFamilyProxy(
                    cmd_name, COMMAND_FAMILIES[cmd_name]
                )
            return self.commands[cmd_name]
        return super().get_command(ctx, cmd_name)
