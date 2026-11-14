"""Network-free startup budget and public lazy-dispatch compatibility."""

import subprocess
import sys

import pytest

EXPECTED_FAMILIES = (
    "bsee",
    "dashboard",
    "eia",
    "marine-safety",
    "fdas",
    "hse",
    "lower-tertiary",
    "sodir",
    "metocean",
    "ndbc",
    "texas-rrc",
    "kansas-kgs",
    "canada",
    "mexico-cnh",
    "landman",
    "lng-terminals",
    "safety-analysis",
    "forecast",
)
EXPECTED_INFO_ORDER = (
    "bsee",
    "dashboard",
    "eia",
    "marine-safety",
    "fdas",
    "hse",
    "lower-tertiary",
    "forecast",
    "sodir",
    "metocean",
    "ndbc",
    "texas-rrc",
    "kansas-kgs",
    "canada",
    "mexico-cnh",
    "landman",
    "lng-terminals",
    "safety-analysis",
)
DENIED_MODULES = {
    "pandas",
    "numpy",
    "pydantic",
    "worldenergydata.common",
    "worldenergydata.safety_analysis",
    "worldenergydata.cli.commands.bsee",
}


def _startup_probe(args, expected_family=None):
    script = f"""
import json
import sys

def deny_network(event, args):
    if event in {{'socket.connect', 'socket.getaddrinfo'}}:
        raise AssertionError('Startup attempted network access')
sys.addaudithook(deny_network)
from worldenergydata.cli.main import app
import typer
args = {args!r}
if args is not None:
    try:
        typer.main.get_command(app)(args, prog_name='worldenergydata')
    except SystemExit as exc:
        assert exc.code == 0, exc.code
loaded = set(sys.modules)
assert not loaded.intersection({DENIED_MODULES!r}), sorted(
    loaded.intersection({DENIED_MODULES!r}))
families = {{name for name in loaded
            if name.startswith('worldenergydata.cli.commands.')}}
expected = {{'worldenergydata.cli.commands.' + {expected_family!r}}} \
    if {expected_family!r} else set()
assert families == expected, sorted(families)
"""
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_bare_import_stays_within_startup_budget():
    _startup_probe(None)


@pytest.mark.parametrize("family", ["landman", "fdas"])
def test_family_help_loads_only_selected_family(family):
    _startup_probe([family, "--help"], family)


def test_root_help_stays_lazy_and_lists_every_family():
    output = _startup_probe(["--help"])
    for name in EXPECTED_FAMILIES:
        assert name in output
    assert "install-completion" in output
    assert "show-completion" in output


def test_registry_preserves_names_orders_and_info_text():
    import typer
    from typer.testing import CliRunner

    from worldenergydata.cli.main import app
    from worldenergydata.cli.registry import COMMAND_FAMILIES, INFO_ROW_ORDER

    assert isinstance(app, typer.Typer)
    assert tuple(COMMAND_FAMILIES) == EXPECTED_FAMILIES
    assert INFO_ROW_ORDER == EXPECTED_INFO_ORDER
    assert set(INFO_ROW_ORDER) == set(COMMAND_FAMILIES)
    assert len(INFO_ROW_ORDER) == len(set(INFO_ROW_ORDER))
    result = CliRunner().invoke(app, ["info"])
    assert result.exit_code == 0, result.output
    for name in COMMAND_FAMILIES:
        assert name in result.output
    assert "Kansas Geological Survey" in result.output
    assert COMMAND_FAMILIES["forecast"].help != COMMAND_FAMILIES["forecast"].info_desc


@pytest.mark.parametrize(
    ("family", "commands"),
    [
        ("landman", ("search", "lookup", "county-info", "providers", "status")),
        ("fdas", ("calculate-npv", "calculate-mirr", "analyze")),
    ],
)
def test_dispatch_reaches_native_family_commands(family, commands):
    from typer.testing import CliRunner

    from worldenergydata.cli.main import app

    result = CliRunner().invoke(app, [family, "--help"])
    assert result.exit_code == 0, result.output
    for command in commands:
        assert command in result.output
    assert "install-completion" not in result.output
    missing = CliRunner().invoke(app, [family, "no-such-command"])
    assert missing.exit_code == 2
    assert "No such command" in missing.output


def test_help_and_completion_do_not_duplicate_cached_names():
    from typer.main import get_command

    from worldenergydata.cli.main import app

    root = get_command(app)
    with root.make_context("worldenergydata", [], resilient_parsing=True) as ctx:
        expected = ["version", "info", "status", *EXPECTED_FAMILIES]
        assert root.list_commands(ctx) == expected
        root.get_help(ctx)
        assert root.list_commands(ctx) == expected
        root.get_help(ctx)
        assert root.list_commands(ctx) == expected
        completions = root.shell_complete(ctx, "land")
        assert [item.value for item in completions] == ["landman"]
        proxy = root.get_command(ctx, "landman")
        assert proxy is root.get_command(ctx, "landman")
        with proxy.make_context(
            "landman", [], parent=ctx, resilient_parsing=True
        ) as family_ctx:
            assert "search" in [
                item.value for item in proxy.shell_complete(family_ctx, "s")
            ]


def test_lazy_family_preserves_eager_typer_registration(monkeypatch):
    """A one-command family remains grouped; registry help overrides app help."""
    import sys
    from types import ModuleType

    import typer
    from typer.testing import CliRunner

    from worldenergydata.cli.main import app
    from worldenergydata.cli.registry import COMMAND_FAMILIES

    module = ModuleType(COMMAND_FAMILIES["marine-safety"].module)
    module.app = typer.Typer(name="internal_name", help="Internal help")

    @module.app.command()
    def example():
        typer.echo("command dispatched")

    monkeypatch.setitem(sys.modules, module.__name__, module)
    eager = typer.Typer(rich_markup_mode="rich")
    eager.add_typer(
        module.app, name="marine-safety", help=COMMAND_FAMILIES["marine-safety"].help
    )
    runner = CliRunner()
    for args in (
        ["marine-safety", "--help"],
        ["marine-safety", "example"],
        ["marine-safety"],
    ):
        actual = runner.invoke(app, args, prog_name="worldenergydata")
        expected = runner.invoke(eager, args, prog_name="worldenergydata")
        assert actual.exit_code == expected.exit_code
        assert actual.output == expected.output
