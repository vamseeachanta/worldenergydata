"""Exercise the daily collection step with real pytest on synthetic suites."""

import copy
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/main-full-run.yml"
TARGETS = "${{ steps.test-targets.outputs.targets }}"


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _contract(workflow):
    job = workflow["jobs"]["full-suite"]
    assert job["strategy"]["matrix"]["python-version"] == ["3.10", "3.11", "3.12"]
    assert not job.get("continue-on-error", False)
    steps = job["steps"]
    collect = next(step for step in steps if step.get("id") == "collection")
    selection = next(step for step in steps if step.get("id") == "test-targets")
    install = next(step for step in steps if step["name"] == "Install dependencies")
    runtime = next(step for step in steps if step["name"] == "Run tests with coverage")
    assert steps.index(install) < steps.index(selection) < steps.index(collect)
    assert steps.index(collect) < steps.index(runtime)
    assert runtime.get("if") == (
        "${{ !cancelled() && steps.test-targets.outcome == 'success' }}"
    )
    assert not collect.get("continue-on-error", False)
    assert "if" not in collect
    assert collect["env"]["TEST_TARGETS"] == runtime["env"]["TEST_TARGETS"] == TARGETS
    assert "find tests" in selection["run"]
    assert sum("find tests" in step.get("run", "") for step in steps) == 1
    assert "$GITHUB_OUTPUT" in selection["run"]
    assert "$TEST_TARGETS tests/integration tests/performance" in collect["run"]
    assert "--collect-only" in collect["run"]
    assert "-p no:cacheprovider" in collect["run"]
    command = (
        collect["run"]
        .split("uv run --frozen pytest", 1)[1]
        .split("pytest_status=", 1)[0]
    )
    assert all(flag not in command for flag in ("--ignore", "-n ", "-o addopts"))
    contract = next(
        step for step in steps if step["name"] == "Check collection contract"
    )
    assert "tests/ci/test_collection_contract.py" in contract["run"]
    assert "!cancelled()" in contract["if"]
    assert "steps.collection.outcome" in contract["if"]
    assert not contract.get("continue-on-error", False)
    upload = next(
        step for step in steps if step["name"] == "Upload collection evidence"
    )
    assert upload["if"] == "always()"
    assert upload["uses"].startswith("actions/upload-artifact@")
    assert upload["with"]["path"] == "${{ runner.temp }}/collection-evidence/"
    assert "${{ matrix.python-version }}" in upload["with"]["name"]
    return collect


def test_daily_matrix_collects_the_runtime_union():
    _contract(_workflow())


@pytest.mark.parametrize(
    "mutation", ["version", "hidden-target", "masked-step", "runtime-condition"]
)
def test_contract_rejects_missing_coverage(mutation):
    workflow = copy.deepcopy(_workflow())
    job = workflow["jobs"]["full-suite"]
    if mutation == "version":
        job["strategy"]["matrix"]["python-version"].pop()
    elif mutation == "runtime-condition":
        runtime = next(
            step for step in job["steps"] if step["name"] == "Run tests with coverage"
        )
        runtime.pop("if", None)
    else:
        collect = next(step for step in job["steps"] if step.get("id") == "collection")
        if mutation == "hidden-target":
            collect["run"] = collect["run"].replace(" tests/integration", "")
        else:
            collect["continue-on-error"] = True
    with pytest.raises(AssertionError):
        _contract(workflow)


def _run_collection(tmp_path, script, case):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    # The fixture has its own config; the production command retains its config.
    config = "[pytest]\n"
    if case == "deselected":
        config += "addopts=--deselect=tests/unit/test_unit.py\n"
    (checkout / "pytest.ini").write_text(config, encoding="utf-8")
    for target in ("unit", "integration", "performance"):
        directory = checkout / "tests" / target
        directory.mkdir(parents=True)
        if case != "empty":
            body = "def test_sample():\n    assert True\n"
            if case == "broken" and target == "integration":
                body = "raise RuntimeError('synthetic collection failure')\n"
            (directory / f"test_{target}.py").write_text(body, encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "uv"
    wrapper.write_text(
        "#!/bin/sh\n"
        'if [ "$3" = pytest ]; then\n'
        '  shift 3; exec "$COLLECTION_PYTHON" -m pytest "$@"\n'
        "fi\n"
        'shift 3; exec "$COLLECTION_PYTHON" "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    environment = {**os.environ}
    environment.pop("PYTEST_ADDOPTS", None)
    environment.pop("PYTEST_PLUGINS", None)
    environment.update(
        # Installed plugins must not write artifacts into the synthetic checkout.
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PATH=str(bin_dir) + os.pathsep + environment["PATH"],
        COLLECTION_PYTHON=sys.executable,
        RUNNER_TEMP=str(evidence),
        GITHUB_SHA="synthetic-revision",
        GITHUB_STEP_SUMMARY=str(tmp_path / "step-summary"),
        TEST_TARGETS="tests/unit",
    )
    result = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        cwd=checkout,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    summary_path = evidence / "collection-evidence/summary.txt"
    summary = dict(line.split("=", 1) for line in summary_path.read_text().splitlines())
    log = (evidence / "collection-evidence/collection.log").read_text()
    assert sorted(path.name for path in checkout.iterdir()) == ["pytest.ini", "tests"]
    assert summary["revision"] == "synthetic-revision"
    assert summary["interpreter"].startswith("Python ")
    return result, summary, log


@pytest.mark.parametrize("plugin_source", ["autoload", "environment"])
def test_collection_isolates_parent_plugins(tmp_path, monkeypatch, plugin_source):
    plugins = tmp_path / "plugins"
    plugins.mkdir()
    (plugins / "parent_plugin.py").write_text(
        "from pathlib import Path\nPath('.plugin-output').mkdir()\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "PYTHONPATH",
        str(plugins) + os.pathsep + os.environ.get("PYTHONPATH", ""),
    )
    monkeypatch.delenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", raising=False)
    monkeypatch.delenv("PYTEST_PLUGINS", raising=False)
    if plugin_source == "autoload":
        metadata = plugins / "parent_plugin-1.0.dist-info"
        metadata.mkdir()
        (metadata / "METADATA").write_text(
            "Metadata-Version: 2.1\nName: parent-plugin\nVersion: 1.0\n",
            encoding="utf-8",
        )
        (metadata / "entry_points.txt").write_text(
            "[pytest11]\nparent-plugin = parent_plugin\n", encoding="utf-8"
        )
    else:
        monkeypatch.setenv("PYTEST_PLUGINS", "parent_plugin")
    script = _contract(_workflow())["run"]
    result, summary, _ = _run_collection(tmp_path, script, "passing")
    assert result.returncode == 0, result.stdout + result.stderr
    assert summary["selected_tests"] == "3"


@pytest.mark.parametrize(
    "case,expected_status,expected_count",
    [
        ("passing", 0, "3"),
        ("broken", 2, "2"),
        ("empty", 5, "0"),
        ("deselected", 0, "2"),
    ],
)
def test_collection_retains_status_count_and_log(
    tmp_path, case, expected_status, expected_count
):
    script = _contract(_workflow())["run"]
    result, summary, log = _run_collection(tmp_path, script, case)
    assert result.returncode == expected_status, result.stdout + result.stderr
    assert summary["status"] == summary["pytest_status"] == str(expected_status)
    assert summary["selected_tests"] == expected_count
    assert (
        "synthetic collection failure" in log
        if case == "broken"
        else "collected" in log
    )


def test_masked_command_is_detected(tmp_path):
    script = _contract(_workflow())["run"].replace('exit "$status"', "exit 0")
    result, summary, _ = _run_collection(tmp_path, script, "broken")
    assert summary["status"] == "2"
    with pytest.raises(AssertionError):
        assert result.returncode == int(summary["status"])


@pytest.mark.parametrize("missing_summary", [False, True])
def test_success_requires_a_positive_known_count(tmp_path, missing_summary):
    script = _contract(_workflow())["run"]
    if missing_summary:
        script = script.replace("--collect-only -q", "--collect-only -qq")
        case, count = "passing", "unknown"
    else:
        script = script.replace("pytest_status=$?", "pytest_status=0")
        case, count = "empty", "0"
    result, summary, _ = _run_collection(tmp_path, script, case)
    assert summary["pytest_status"] == "0"
    assert summary["selected_tests"] == count
    assert summary["status"] == "5"
    assert result.returncode == 5


def test_shared_selection_keeps_parallel_targets(tmp_path):
    steps = _workflow()["jobs"]["full-suite"]["steps"]
    selection = next(step for step in steps if step.get("id") == "test-targets")
    for name in ("unit", "modules", "ci", "integration", "performance", "__pycache__"):
        (tmp_path / "tests" / name).mkdir(parents=True)
    (tmp_path / "tests/test_top.py").touch()
    output = tmp_path / "outputs"
    result = subprocess.run(
        ["bash", "-eo", "pipefail", "-c", selection["run"]],
        cwd=tmp_path,
        env={**os.environ, "GITHUB_OUTPUT": str(output)},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text().strip().split("=", 1) == [
        "targets",
        "tests/ci tests/modules tests/test_top.py tests/unit",
    ]
