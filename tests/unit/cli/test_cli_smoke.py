"""Bounded CLI smoke tests for public entry points."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _cli_command() -> list[str]:
    executable = shutil.which("worldenergydata")
    if executable:
        return [executable]
    return [
        sys.executable,
        "-c",
        (
            "import sys; "
            "from worldenergydata.cli.main import app; "
            "import typer; "
            "raise SystemExit(typer.main.get_command(app)(sys.argv[1:]))"
        ),
    ]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = os.path.abspath("src")
    assetutilities_path = os.path.abspath("../assetutilities/src")
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (src_path, assetutilities_path, env.get("PYTHONPATH", "")) if p
    )
    return subprocess.run(
        [*_cli_command(), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=20,
        env=env,
    )


def test_root_help_info_and_version_are_bounded_safe():
    """Public root commands should execute without data, network, or credentials."""
    commands = [
        ("--help",),
        ("info",),
        ("version",),
    ]

    for command in commands:
        result = _run_cli(*command)
        assert result.returncode == 0, (
            command,
            result.stdout[-500:],
            result.stderr[-500:],
        )


def test_info_lists_all_registered_public_subapps():
    """The CLI's own module list should match the registered public sub-apps."""
    result = _run_cli("info")

    assert result.returncode == 0, result.stderr
    for subapp in (
        "bsee",
        "dashboard",
        "eia",
        "marine-safety",
        "fdas",
        "lower-tertiary",
        "forecast",
        "sodir",
        "metocean",
        "ndbc",
        "texas-rrc",
        "canada",
        "mexico-cnh",
        "landman",
        "lng-terminals",
        "safety-analysis",
    ):
        assert subapp in result.stdout
