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
# Required aggregates must run and reject skipped dependencies on drafts.
AGGREGATES = {
    "ci.yml": {
        "lint-gate",
        "type-check-gate",
        "security-gate",
        "docs-gate",
        "pr-gate",
    },
}
PR_EVENTS = ["opened", "synchronize", "reopened", "ready_for_review"]
PR_WORKFLOWS = {"brand-guard.yml", "ci.yml", "docs.yml", "pr-validation.yml"}


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


def assert_draft_guard(filename, job_id, job):
    original = condition(SNAPSHOT[filename]["jobs"][job_id]["if"])
    expected = f"({DRAFT_GUARD}) && ({original})" if original else DRAFT_GUARD
    assert condition(job.get("if")) == expected, f"{filename}:{job_id}: draft guard"


def assert_workflow_names(filename, workflow):
    baseline = SNAPSHOT[filename]
    assert workflow["name"] == baseline["name"], f"{filename}: workflow name"
    assert {job_id: job.get("name") for job_id, job in workflow["jobs"].items()} == {
        job_id: job["name"] for job_id, job in baseline["jobs"].items()
    }, f"{filename}: job names"


def assert_pr_triggers(filename, workflow):
    expected = json.loads(json.dumps(SNAPSHOT[filename]["on"]))
    if filename in HEAVY_JOBS:
        pull_request = expected["pull_request"] or {}
        # Restart guarded work on ready transitions; preserve metadata replay.
        old_types = pull_request.get("types", PR_EVENTS[:3])
        pull_request["types"] = PR_EVENTS + [
            event for event in old_types if event not in PR_EVENTS
        ]
        expected["pull_request"] = pull_request
    assert workflow["on"] == expected, f"{filename}: triggers"


def test_workflow_inventory():
    paths = {*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")}
    assert {path.name for path in paths} == set(SNAPSHOT)


@pytest.mark.parametrize("filename", sorted(SNAPSHOT))
def test_workflow_and_job_names_are_preserved(filename):
    assert_workflow_names(filename, load_workflow(filename))


@pytest.mark.parametrize("filename", sorted(PR_WORKFLOWS))
def test_triggers_preserve_existing_events_and_filters(filename):
    assert_pr_triggers(filename, load_workflow(filename))


@pytest.mark.parametrize("filename", sorted(set(SNAPSHOT) - PR_WORKFLOWS))
def test_non_pr_snapshots_pin_only_names(filename):
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
        for filename in sorted(HEAVY_JOBS)
        for job_id in sorted(HEAVY_JOBS[filename])
    ],
)
def test_heavy_jobs_skip_drafts(filename, job_id):
    # Exact conjunction also proves the original ready-PR condition is retained.
    assert_draft_guard(filename, job_id, load_workflow(filename)["jobs"][job_id])


@pytest.mark.parametrize("filename", sorted(PR_WORKFLOWS))
def test_other_job_conditions_are_untouched(filename):
    for job_id, job in load_workflow(filename)["jobs"].items():
        if job_id not in HEAVY_JOBS.get(filename, set()):
            assert job.get("if") == SNAPSHOT[filename]["jobs"][job_id]["if"]


@pytest.mark.parametrize("job_id", sorted(AGGREGATES["ci.yml"]))
def test_required_aggregates_run_on_drafts(job_id):
    job = load_workflow("ci.yml")["jobs"][job_id]
    assert condition(job.get("if")) == condition(
        SNAPSHOT["ci.yml"]["jobs"][job_id]["if"]
    )
    assert not job.get("continue-on-error", False)


@pytest.mark.parametrize("job_id", sorted(AGGREGATES["ci.yml"]))
@pytest.mark.parametrize("full_result", ["success", "skipped", "failure", "cancelled"])
def test_required_aggregate_checks_full_result(job_id, full_result, tmp_path):
    job = load_workflow("ci.yml")["jobs"][job_id]
    step = next(step for step in job["steps"] if step["name"] == "Gate on full result")
    upstream = [dependency for dependency in job["needs"] if dependency != "mode"]
    assert len(upstream) == 1
    assert step["env"]["FULL_RESULT"] == "${{ needs." + upstream[0] + ".result }}"
    assert condition(step.get("if")) == (
        "needs.mode.result != 'success' || needs.mode.outputs.replay != 'true'"
    )
    assert not step.get("continue-on-error", False)
    result = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        cwd=tmp_path,
        env={**os.environ, "FULL_RESULT": full_result},
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == (0 if full_result == "success" else 1), result.stdout


def test_missing_draft_guard_is_rejected():
    job = load_workflow("docs.yml")["jobs"]["docs"]
    job.pop("if", None)
    with pytest.raises(AssertionError, match="draft guard"):
        assert_draft_guard("docs.yml", "docs", job)


@pytest.mark.parametrize("mutation", ["or_guard", "dropped_original"])
def test_incorrect_draft_conjunction_is_rejected(mutation):
    job = load_workflow("ci.yml")["jobs"]["lint"]
    if mutation == "or_guard":
        original = condition(SNAPSHOT["ci.yml"]["jobs"]["lint"]["if"])
        job["if"] = f"({DRAFT_GUARD}) || ({original})"
    else:
        job["if"] = DRAFT_GUARD
    with pytest.raises(AssertionError, match="draft guard"):
        assert_draft_guard("ci.yml", "lint", job)


@pytest.mark.parametrize("mutation", ["renamed_required_check", "removed_ready_event"])
def test_required_check_policy_mutations_are_rejected(mutation):
    workflow = load_workflow("ci.yml")
    if mutation == "renamed_required_check":
        workflow["jobs"]["lint-gate"]["name"] = "Renamed lint"
        with pytest.raises(AssertionError, match="job names"):
            assert_workflow_names("ci.yml", workflow)
    else:
        workflow["on"]["pull_request"]["types"].remove("ready_for_review")
        with pytest.raises(AssertionError, match="triggers"):
            assert_pr_triggers("ci.yml", workflow)


@pytest.mark.parametrize("filename", sorted(PR_WORKFLOWS - HEAVY_JOBS.keys()))
def test_quick_workflows_reject_redundant_ready_events(filename):
    workflow = load_workflow(filename)
    pull_request = workflow["on"]["pull_request"]
    pull_request.setdefault("types", PR_EVENTS[:3]).append("ready_for_review")
    with pytest.raises(AssertionError, match="triggers"):
        assert_pr_triggers(filename, workflow)


def test_draft_policy_is_in_the_default_pr_test_selection():
    # The domain selector already runs tests/workflows on every relevant PR.
    import importlib.util

    path = ROOT / "scripts" / "ci" / "select_test_targets.py"
    spec = importlib.util.spec_from_file_location("draft_policy_targets", path)
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    assert "tests/workflows" in selector.ALWAYS_XDIST
