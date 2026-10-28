"""Fresh-process startup contracts for the installed root console.

Expected import counts are hand-derived from issue #926: root-only requests
select no family (empty set); family help selects exactly its named module
(singleton set). The watchdog comes from test_cli_smoke.py, not a performance
claim. No network operation is needed to parse help.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest

# Independent metadata snapshot from cli/main.py at the base revision in
# docs/development/cli-startup.md; changing the live registry cannot change it.
PUBLIC_FAMILIES = {
    "bsee": "BSEE data operations and analysis",
    "dashboard": "Launch the Plotly Dash BSEE/FDAS web dashboard",
    "eia": "EIA API v2 weekly petroleum and gas feed ingestion",
    "marine-safety": "Marine safety incident data management",
    "fdas": "Field Development Analysis System",
    "lower-tertiary": "Lower Tertiary portfolio analyses (10 GoM fields)",
    "sodir": "SODIR (Norwegian Offshore Directorate) data operations",
    "metocean": "Metocean data - buoys, tides, marine weather",
    "ndbc": "NDBC buoy data: scatter matrices, Weibull fits, wave roses",
    "texas-rrc": "Texas Railroad Commission oil & gas data",
    "kansas-kgs": "Kansas Geological Survey well and pressure data",
    "canada": "Canadian oil & gas data (AER/BCER)",
    "mexico-cnh": "Mexico CNH oil & gas data (SIH dashboard)",
    "landman": "Mineral ownership and lease data operations",
    "lng-terminals": "Global LNG terminal dataset with engineering design data",
    "safety-analysis": "Safety analysis and HSE data processing",
    "forecast": "Arps decline curve analysis — fit, EUR, and production forecast",
}

# Existing public-console watchdog: tests/unit/cli/test_cli_smoke.py::_run_cli.
WATCHDOG_SECONDS = 20
AUDIT = """
import atexit
import json
import os
import sys

def audit(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.bind"}:
        raise AssertionError("CLI startup must be offline")

sys.addaudithook(audit)

def record():
    names = sorted(name for name in sys.modules if (
        name.startswith("worldenergydata.cli.commands.")
        or name == "worldenergydata.safety_analysis.cli"
        or name in {"pandas", "numpy", "pydantic", "worldenergydata.bsee",
                    "worldenergydata.common", "worldenergydata.safety_analysis"}
    ))
    with open(os.environ["CLI_IMPORT_REPORT"], "w") as stream:
        json.dump(names, stream)

atexit.register(record)
"""


@pytest.fixture
def installed_console(tmp_path):
    """Use the actual installed script; never fall back to a child Typer app."""
    executable = shutil.which("worldenergydata")
    assert executable, "Install the workspace before running console startup tests"
    (tmp_path / "sitecustomize.py").write_text(AUDIT)
    report = tmp_path / "imports.json"
    env = os.environ.copy()
    env["CLI_IMPORT_REPORT"] = str(report)
    env["PYTHONPATH"] = os.pathsep.join([str(tmp_path), env.get("PYTHONPATH", "")])
    env["COLUMNS"] = "120"
    env["NO_COLOR"] = "1"
    # Do not inherit a caller's shell-completion request.
    env.pop("_WORLDENERGYDATA_COMPLETE", None)

    def run(*args, python_args=None):
        result = subprocess.run(
            [sys.executable, *python_args] if python_args else [executable, *args],
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=WATCHDOG_SECONDS,
            check=False,
        )
        assert report.exists(), "The offline import recorder did not start"
        return result, set(json.loads(report.read_text()))

    return run


@pytest.mark.parametrize("args", [("--help",), ("info",), ("version",), ()])
def test_root_requests_have_no_family_imports(installed_console, args):
    result, imported = installed_console(*args)
    assert result.returncode == (2 if not args else 0), result.stderr
    assert imported == set()


@pytest.mark.parametrize("family", ["landman", "fdas", "eia"])
def test_family_help_imports_only_selected_family(installed_console, family):
    result, imported = installed_console("--verbose", family, "--help")
    assert result.returncode == 0, result.stderr
    assert imported == {f"worldenergydata.cli.commands.{family}"}
    assert f"{family} [OPTIONS]" in result.stdout


def test_root_help_preserves_registration_order_and_descriptions(installed_console):
    """Expected metadata is independently read from the base root registrations."""
    result, _ = installed_console("--help")
    previous = -1
    for name, help_text in PUBLIC_FAMILIES.items():
        position = result.stdout.index(name)
        assert position > previous
        previous = position
        assert help_text in result.stdout


def test_invalid_command_does_not_import_families(installed_console):
    result, imported = installed_console("missing-family")
    assert result.returncode == 2
    assert "No such command" in result.stderr
    assert not imported


# Click recommends loading every registered family's help.
@pytest.mark.parametrize("family", PUBLIC_FAMILIES)
def test_every_registered_family_can_load_help(installed_console, family):
    result, _ = installed_console(family, "--help")
    assert result.returncode == 0, result.stderr
    assert f"{family} [OPTIONS]" in result.stdout


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (
            ("landman", "lookup", "--state", "TX", "--county", "EXAMPLE"),
            "Must provide --document-number",
        ),
        (("eia", "sync", "--help"), "--feed"),
    ],
)
def test_real_nested_command_dispatch_is_offline(installed_console, args, expected):
    result, imported = installed_console(*args)
    assert result.returncode == (1 if args[0] == "landman" else 0)
    assert expected in result.stdout
    assert imported == {f"worldenergydata.cli.commands.{args[0]}"}


def test_bare_root_import_has_no_family_dependencies(installed_console):
    result, imported = installed_console(
        python_args=["-c", "import worldenergydata.cli.main"]
    )
    assert result.returncode == 0, result.stderr
    assert not imported


def test_module_entrypoint_preserves_lazy_dispatch(installed_console):
    result, imported = installed_console(
        python_args=["-m", "worldenergydata", "landman", "--help"]
    )
    assert result.returncode == 0, result.stderr
    assert imported == {"worldenergydata.cli.commands.landman"}
    assert "county-info" in result.stdout
