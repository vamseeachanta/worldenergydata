"""Exercise lazy groups with independent synthetic command families.

Hand-derived expectations: selecting a nested command executes the root,
family, then leaf callbacks in that order; no other callback can run. A cached
family requires one import regardless of repeated context construction.
"""

from types import SimpleNamespace

import pytest
import typer
from typer.main import get_command
from typer.testing import CliRunner

from worldenergydata.cli.lazy import lazy_app


@pytest.fixture
def synthetic(monkeypatch):
    events = []
    imports = []
    family = typer.Typer(no_args_is_help=True)
    nested = typer.Typer()

    @family.callback()
    def setup(ctx: typer.Context, mode: str = typer.Option("normal", "--mode")):
        events.append(("family", mode, ctx.obj))

    @nested.command()
    def echo(value: str):
        events.append(("leaf", value))
        typer.echo(value)

    family.add_typer(nested, name="nested")

    def load(name):
        imports.append(name)
        return SimpleNamespace(app=family)

    monkeypatch.setattr("worldenergydata.cli.lazy.import_module", load)
    root = typer.Typer()
    root.add_typer(lazy_app("test.family"), name="sample", help="Family help")

    @root.callback()
    def setup_root(ctx: typer.Context):
        ctx.obj = "root context"
        events.append(("root",))

    return root, imports, events


def test_nested_dispatch_preserves_callbacks_options_and_context(synthetic):
    root, imports, events = synthetic
    result = CliRunner().invoke(
        root, ["sample", "--mode", "custom", "nested", "echo", "answer"]
    )
    assert result.exit_code == 0, result.output
    assert result.output.strip() == "answer"
    assert imports == ["test.family"]
    assert events == [
        ("root",),
        ("family", "custom", "root context"),
        ("leaf", "answer"),
    ]


def test_root_completion_uses_metadata_without_loading(synthetic):
    root, imports, _ = synthetic
    command = get_command(root)
    with command.make_context("root", [], resilient_parsing=True) as ctx:
        completions = command.shell_complete(ctx, "sam")
    assert [(item.value, item.help) for item in completions] == [
        ("sample", "Family help")
    ]
    assert not imports


def test_family_completion_and_repeated_contexts_load_once(synthetic):
    root, imports, _ = synthetic
    command = get_command(root)
    with command.make_context("root", [], resilient_parsing=True) as ctx:
        proxy = command.get_command(ctx, "sample")
        with proxy.make_context(
            "sample", [], parent=ctx, resilient_parsing=True
        ) as child:
            assert [item.value for item in proxy.shell_complete(child, "nes")] == [
                "nested"
            ]
            assert proxy.list_commands(child) == ["nested"]
            assert proxy.get_command(child, "nested").name == "nested"
        with proxy.make_context("sample", [], parent=ctx, resilient_parsing=True):
            pass
    assert imports == ["test.family"]


def test_proxy_invoke_supports_click_calling_convention(synthetic):
    root, imports, events = synthetic
    proxy = get_command(root).commands["sample"]
    with proxy.make_context(
        "sample", ["nested", "echo", "answer"], obj="direct"
    ) as ctx:
        proxy.invoke(ctx)
    assert imports == ["test.family"]
    assert events == [("family", "normal", "direct"), ("leaf", "answer")]


def test_missing_family_affects_only_selected_command(monkeypatch):
    def missing(name):
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("worldenergydata.cli.lazy.import_module", missing)
    root = typer.Typer()
    root.add_typer(
        lazy_app("missing.family"), name="missing", help="Unavailable family"
    )
    assert CliRunner().invoke(root, ["--help"]).exit_code == 0
    result = CliRunner().invoke(root, ["missing", "--help"])
    assert isinstance(result.exception, ModuleNotFoundError)


@pytest.mark.parametrize("name", ["lower_tertiary", "production_forecast"])
def test_command_exports_follow_lazy_attribute_path(monkeypatch, name):
    from worldenergydata.cli import commands

    sentinel = object()
    requested = []

    def load(module):
        requested.append(module)
        return sentinel

    monkeypatch.setattr(commands, "import_module", load)
    monkeypatch.setitem(commands.__dict__, name, None)
    assert name in commands.__all__
    assert commands.__getattr__(name) is sentinel
    assert requested == [f"worldenergydata.cli.commands.{name}"]
