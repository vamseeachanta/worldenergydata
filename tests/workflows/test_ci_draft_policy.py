"""Preserve ready-PR checks while keeping expensive jobs off draft PRs."""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
SNAPSHOT = json.loads(Path(__file__).with_name("ci_workflow_names.json").read_text())
DRAFT_GUARD = (
    "github.event_name != 'pull_request' || github.event.pull_request.draft == false"
)
# These jobs install dependencies, run tests or analysis, or build artifacts.
HEAVY_JOBS = {
    "ci.yml": {
        "domain-tests",
        "test",
        "lint",
        "type-check",
        "security",
        "build",
        "docs",
    },
    "docs.yml": {"docs"},
}
# Required aggregates must reject skipped dependencies, including on drafts.
AGGREGATES = {
    "ci.yml": {
        "lint-gate",
        "type-check-gate",
        "security-gate",
        "docs-gate",
        "pr-gate",
    },
}
PR_WORKFLOWS = ("brand-guard.yml", "ci.yml", "docs.yml", "pr-validation.yml")
PR_EVENTS = ["opened", "synchronize", "reopened", "ready_for_review"]


def load_workflow(filename):
    # BaseLoader preserves the Actions key 'on' as a string.
    return yaml.load(
        (WORKFLOWS / filename).read_text(encoding="utf-8"), Loader=yaml.BaseLoader
    )


def condition(expression):
    """Normalize folding and optional expression delimiters, preserving logic."""
    expression = (expression or "").strip()
    if expression.startswith("${{") and expression.endswith("}}"):
        expression = expression[3:-2].strip()
    return " ".join(expression.split())


def guarded_jobs(filename):
    return HEAVY_JOBS.get(filename, set())


def assert_draft_guard(filename, job_id, job):
    original = condition(SNAPSHOT[filename]["jobs"][job_id]["if"])
    expected = f"({DRAFT_GUARD}) && ({original})" if original else DRAFT_GUARD
    assert condition(job.get("if")) == expected, f"{filename}:{job_id}: draft guard"


def test_workflow_inventory():
    paths = {*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")}
    assert {path.name for path in paths} == set(SNAPSHOT)


def assert_workflow_and_job_names(filename, workflow):
    baseline = SNAPSHOT[filename]
    assert workflow["name"] == baseline["name"], f"{filename}: workflow name"
    assert {job_id: job.get("name") for job_id, job in workflow["jobs"].items()} == {
        job_id: job["name"] for job_id, job in baseline["jobs"].items()
    }, f"{filename}: job names"


def assert_triggers(filename, workflow):
    expected = json.loads(json.dumps(SNAPSHOT[filename]["on"]))
    if "pull_request" in expected:
        pull_request = expected["pull_request"] or {}
        # Keep edited events for title validation and metadata-result replay.
        old_types = pull_request.get("types", PR_EVENTS[:3])
        pull_request["types"] = PR_EVENTS + [
            event for event in old_types if event not in PR_EVENTS
        ]
        expected["pull_request"] = pull_request
    assert workflow["on"] == expected, f"{filename}: triggers"


@pytest.mark.parametrize("filename", sorted(SNAPSHOT))
def test_workflow_and_job_names_are_preserved(filename):
    assert_workflow_and_job_names(filename, load_workflow(filename))


@pytest.mark.parametrize("filename", PR_WORKFLOWS)
def test_triggers_preserve_existing_events_and_filters(filename):
    assert_triggers(filename, load_workflow(filename))


@pytest.mark.parametrize("filename", sorted(set(SNAPSHOT) - set(PR_WORKFLOWS)))
def test_non_pr_snapshot_only_pins_names(filename):
    baseline = SNAPSHOT[filename]
    assert set(baseline) == {"name", "jobs"}
    assert all(set(job) == {"name"} for job in baseline["jobs"].values())


@pytest.mark.parametrize("filename", sorted(HEAVY_JOBS))
def test_heavy_workflows_allow_manual_runs(filename):
    assert "workflow_dispatch" in load_workflow(filename)["on"]


@pytest.mark.parametrize(
    "filename,job_id",
    [
        (filename, job_id)
        for filename in sorted(SNAPSHOT)
        for job_id in sorted(guarded_jobs(filename))
    ],
)
def test_heavy_jobs_skip_drafts(filename, job_id):
    # Exact conjunction also proves the original ready-PR condition is retained.
    assert_draft_guard(filename, job_id, load_workflow(filename)["jobs"][job_id])


@pytest.mark.parametrize("filename", PR_WORKFLOWS)
def test_other_job_conditions_are_untouched(filename):
    for job_id, job in load_workflow(filename)["jobs"].items():
        if job_id not in guarded_jobs(filename):
            assert job.get("if") == SNAPSHOT[filename]["jobs"][job_id]["if"]


@pytest.mark.parametrize("job_id", sorted(AGGREGATES["ci.yml"]))
def test_required_aggregates_run_after_skipped_dependencies(job_id):
    job = load_workflow("ci.yml")["jobs"][job_id]
    original = SNAPSHOT["ci.yml"]["jobs"][job_id]["if"]
    assert condition(job["if"]) == condition(original)
    assert "!cancelled()" in condition(job["if"])
    assert "draft" not in job["if"]
    assert not job.get("continue-on-error", False)


@pytest.mark.parametrize("job_id", sorted(AGGREGATES["ci.yml"]))
@pytest.mark.parametrize(
    "result,expected",
    [("success", 0), ("skipped", 1), ("failure", 1), ("cancelled", 1)],
)
def test_required_aggregate_rejects_incomplete_full_result(job_id, result, expected):
    job = load_workflow("ci.yml")["jobs"][job_id]
    step = next(s for s in job["steps"] if s.get("name") == "Gate on full result")
    upstream = next(need for need in job["needs"] if need != "mode")
    assert step["env"] == {"FULL_RESULT": "${{ needs." + upstream + ".result }}"}
    assert condition(step["if"]) == (
        "needs.mode.result != 'success' || needs.mode.outputs.replay != 'true'"
    )
    assert not step.get("continue-on-error", False)
    completed = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", step["run"]],
        env={**os.environ, "FULL_RESULT": result},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == expected, completed.stdout + completed.stderr


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("missing guard", "draft guard"),
        ("disjoined guard", "draft guard"),
        ("dropped original condition", "draft guard"),
        ("renamed required check", "job names"),
        ("missing ready event", "triggers"),
    ],
)
def test_policy_mutations_are_rejected(mutation, error):
    workflow = load_workflow("ci.yml")
    job = workflow["jobs"]["lint"]
    if mutation == "missing guard":
        job["if"] = SNAPSHOT["ci.yml"]["jobs"]["lint"]["if"]
    elif mutation == "disjoined guard":
        original = condition(SNAPSHOT["ci.yml"]["jobs"]["lint"]["if"])
        job["if"] = f"({DRAFT_GUARD}) || ({original})"
    elif mutation == "dropped original condition":
        job["if"] = DRAFT_GUARD
    elif mutation == "renamed required check":
        workflow["jobs"]["lint-gate"]["name"] = "Renamed required check"
    else:
        workflow["on"]["pull_request"]["types"].remove("ready_for_review")
    with pytest.raises(AssertionError, match=error):
        if error == "draft guard":
            assert_draft_guard("ci.yml", "lint", job)
        elif error == "job names":
            assert_workflow_and_job_names("ci.yml", workflow)
        else:
            assert_triggers("ci.yml", workflow)


def test_draft_policy_is_in_the_default_pr_test_selection():
    # The domain selector already runs tests/workflows on every relevant PR.
    import importlib.util

    path = ROOT / "scripts" / "ci" / "select_test_targets.py"
    spec = importlib.util.spec_from_file_location("draft_policy_targets", path)
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    assert "tests/workflows" in selector.ALWAYS_XDIST
