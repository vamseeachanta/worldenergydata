"""Tests for the executable CLI smoke verification harness."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from subprocess import CompletedProcess


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit" / "cli_smoke_verify.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_cli_smoke_verify", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_smoke_command_matrix_covers_registered_subapp_help():
    module = _load_module()

    commands = [" ".join(case.command) for case in module.build_smoke_cases()]

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
        assert f"worldenergydata {subapp} --help" in commands


def test_smoke_report_records_exit_code_and_classification(tmp_path):
    module = _load_module()

    def fake_runner(command, *, timeout, env):
        del timeout, env
        if tuple(command[:2]) == ("worldenergydata", "info"):
            return CompletedProcess(command, 1, "partial info", "boom")
        return CompletedProcess(command, 0, "usage text", "")

    report_path = tmp_path / "cli-smoke-report.md"
    results = module.run_smoke_cases(
        [
            module.SmokeCase(("worldenergydata", "--help"), "bounded-safe"),
            module.SmokeCase(("worldenergydata", "info"), "bounded-safe"),
        ],
        runner=fake_runner,
        report_path=report_path,
    )

    assert [result.status for result in results] == ["pass", "fail"]
    content = report_path.read_text()
    assert "| `worldenergydata --help` | bounded-safe | 0 | pass |" in content
    assert "| `worldenergydata info` | bounded-safe | 1 | fail |" in content
    assert "boom" in content
