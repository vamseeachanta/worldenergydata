"""Preserve ready-PR checks while keeping expensive jobs off draft PRs."""

import json
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
# Aggregates must skip along with their dependencies to avoid false failures.
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
    return HEAVY_JOBS.get(filename, set()) | AGGREGATES.get(filename, set())


def assert_draft_guard(filename, job_id, job):
    original = condition(SNAPSHOT[filename]["jobs"][job_id]["if"])
    expected = f"({DRAFT_GUARD}) && ({original})" if original else DRAFT_GUARD
    assert condition(job.get("if")) == expected, f"{filename}:{job_id}: draft guard"


def test_workflow_inventory():
    paths = {*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")}
    assert {path.name for path in paths} == set(SNAPSHOT)


@pytest.mark.parametrize("filename", sorted(SNAPSHOT))
def test_workflow_and_job_names_are_preserved(filename):
    workflow = load_workflow(filename)
    baseline = SNAPSHOT[filename]
    assert workflow["name"] == baseline["name"]
    assert {job_id: job.get("name") for job_id, job in workflow["jobs"].items()} == {
        job_id: job["name"] for job_id, job in baseline["jobs"].items()
    }


@pytest.mark.parametrize("filename", sorted(SNAPSHOT))
def test_triggers_preserve_existing_events_and_filters(filename):
    workflow = load_workflow(filename)
    expected = json.loads(json.dumps(SNAPSHOT[filename]["on"]))
    if "pull_request" in expected:
        pull_request = expected["pull_request"] or {}
        # Keep edited events for title validation and metadata-result replay.
        old_types = pull_request.get("types", PR_EVENTS[:3])
        pull_request["types"] = PR_EVENTS + [
            event for event in old_types if event not in PR_EVENTS
        ]
        expected["pull_request"] = pull_request
    assert workflow["on"] == expected


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
def test_heavy_jobs_and_their_aggregates_skip_drafts(filename, job_id):
    # Exact conjunction also proves the original ready-PR condition is retained.
    assert_draft_guard(filename, job_id, load_workflow(filename)["jobs"][job_id])


@pytest.mark.parametrize("filename", sorted(SNAPSHOT))
def test_other_job_conditions_are_untouched(filename):
    for job_id, job in load_workflow(filename)["jobs"].items():
        if job_id not in guarded_jobs(filename):
            assert job.get("if") == SNAPSHOT[filename]["jobs"][job_id]["if"]


def test_missing_draft_guard_is_rejected():
    job = load_workflow("docs.yml")["jobs"]["docs"]
    job.pop("if", None)
    with pytest.raises(AssertionError, match="draft guard"):
        assert_draft_guard("docs.yml", "docs", job)


def test_draft_policy_is_in_the_default_pr_test_selection():
    # The domain selector already runs tests/workflows on every relevant PR.
    import importlib.util

    path = ROOT / "scripts" / "ci" / "select_test_targets.py"
    spec = importlib.util.spec_from_file_location("draft_policy_targets", path)
    selector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(selector)
    assert "tests/workflows" in selector.ALWAYS_XDIST
