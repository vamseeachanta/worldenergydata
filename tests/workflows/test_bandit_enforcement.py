"""The full-run security scan propagates findings and execution errors."""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/main-full-run.yml"
COMMAND = "uvx bandit==1.9.4 -r src/ -ll -ii -x tests/"


def _command(workflow):
    job = workflow["jobs"]["security-deep"]
    steps = [
        step
        for step in job["steps"]
        if "bandit" in step.get("run", "") or "bandit" in step.get("name", "").lower()
    ]
    assert len(steps) == 1, "exactly one Bandit step is required"
    step = steps[0]
    for scope in (job, step):
        assert "if" not in scope, "Bandit must run unconditionally"
        assert scope.get("continue-on-error", False) is False, "failure must propagate"
    command = step["run"].strip()
    assert re.fullmatch(r"uvx bandit==\d+\.\d+\.\d+ -r src/ -ll -ii -x tests/", command)
    assert command == COMMAND, "the scanner version must match the tested version"
    return command


def _fixture():
    return {"jobs": {"security-deep": {"steps": [{"run": COMMAND}]}}}


def test_full_run_bandit_enforces_failures():
    _command(yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "suffix",
    [" || true", "; true", " | cat", "\necho done", " --exit-zero"],
)
def test_rejects_command_failure_masking(suffix):
    workflow = _fixture()
    workflow["jobs"]["security-deep"]["steps"][0]["run"] += suffix
    with pytest.raises(AssertionError):
        _command(workflow)


@pytest.mark.parametrize("scope", ["job", "step"])
@pytest.mark.parametrize("key,value", [("continue-on-error", True), ("if", "false")])
def test_rejects_skipped_or_tolerated_scans(scope, key, value):
    workflow = _fixture()
    job = workflow["jobs"]["security-deep"]
    (job if scope == "job" else job["steps"][0])[key] = value
    with pytest.raises(AssertionError):
        _command(workflow)


@pytest.mark.parametrize("count", [0, 2])
def test_rejects_missing_or_duplicate_scans(count):
    workflow = _fixture()
    steps = workflow["jobs"]["security-deep"]["steps"]
    workflow["jobs"]["security-deep"]["steps"] = steps * count
    with pytest.raises(AssertionError):
        _command(workflow)


def test_rejects_unpinned_scanner():
    workflow = _fixture()
    workflow["jobs"]["security-deep"]["steps"][0]["run"] = COMMAND.replace(
        "==1.9.4", ""
    )
    with pytest.raises(AssertionError):
        _command(workflow)


@pytest.mark.parametrize("case,expected", [("clean", 0), ("unsafe", 1), ("error", 2)])
def test_scan_status_propagates(tmp_path, case, expected):
    command = _command(yaml.safe_load(WORKFLOW.read_text(encoding="utf-8")))
    source = tmp_path / "src"
    source.mkdir()
    code = (
        "import pickle\npickle.loads(payload)\n" if case == "unsafe" else "value = 1\n"
    )
    (source / "sample.py").write_text(code, encoding="utf-8")
    if case == "error":
        command += " --format invalid-format"
    result = subprocess.run(
        ["bash", "-c", command],
        cwd=tmp_path,
        env={**os.environ, "UV_OFFLINE": "1"},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == expected, result.stderr
    if case == "unsafe":
        assert "B301" in result.stdout
