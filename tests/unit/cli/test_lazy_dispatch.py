"""Network-free startup budget and public lazy-dispatch compatibility."""

import json
import subprocess
import sys

import pytest

EXPECTED_FAMILIES = (
    "bsee", "dashboard", "eia", "marine-safety", "fdas", "hse",
    "lower-tertiary", "sodir", "metocean", "ndbc", "texas-rrc",
    "kansas-kgs", "canada", "mexico-cnh", "landman", "lng-terminals",
    "safety-analysis", "forecast",
)
EXPECTED_INFO_ORDER = (
    "bsee", "dashboard", "eia", "marine-safety", "fdas", "hse",
    "lower-tertiary", "forecast", "sodir", "metocean", "ndbc", "texas-rrc",
    "kansas-kgs", "canada", "mexico-cnh", "landman", "lng-terminals",
    "safety-analysis",
)
DENIED_MODULES = {
    "pandas", "numpy", "pydantic", "worldenergydata.common",
    "worldenergydata.safety_analysis", "worldenergydata.cli.commands.bsee",
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
