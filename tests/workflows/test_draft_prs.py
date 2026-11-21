"""A draft pull request runs no CI or wheel job; marking it ready runs the full gate."""

import pytest

from tests.workflows.test_ci_triggers import _render
from tests.workflows.test_metadata_edits import (
    CHECKS,
    MARKER,
    evaluate,
    event_context,
    job_states,
    workflow,
)

DRAFT_EVENTS = [
    ("opened", {}),
    ("synchronize", {}),
    ("reopened", {}),
    ("edited", {"base": {"ref": {"from": "main"}}}),  # Retarget while still a draft.
]


def context(filename, action, changes, draft, **run):
    return {
        **event_context(filename, action, changes, **run),
        "github.event.pull_request.draft": draft,
    }


@pytest.mark.parametrize("action,changes", DRAFT_EVENTS)
def test_draft_runs_no_ci_job(action, changes):
    states = job_states("ci.yml", context("ci.yml", action, changes, True))
    usual = set(CHECKS["ci.yml"].values())
    for job, (name, runs) in states.items():
        assert not runs, job
        # A skipped job must never report under a required check name.
        assert name not in usual, job
        assert name == f"Not run for a draft - {CHECKS['ci.yml'][job]}", job


@pytest.mark.parametrize("action,changes", DRAFT_EVENTS)
def test_draft_keeps_cheap_pr_validation(action, changes):
    filename = "pr-validation.yml"
    states = job_states(filename, context(filename, action, changes, True))
    assert states == {job: (name, True) for job, name in CHECKS[filename].items()}


@pytest.mark.parametrize("draft", [False, None])
def test_ready_pull_request_runs_the_full_gate(draft):
    for action in ("ready_for_review", "synchronize"):
        states = job_states("ci.yml", context("ci.yml", action, {}, draft))
        assert states == {job: (name, True) for job, name in CHECKS["ci.yml"].items()}


def test_draft_rerun_cannot_cancel_active_ready_gate():
    concurrency = workflow("ci.yml")["concurrency"]

    def policy(ctx):
        return (
            _render(concurrency["group"], ctx),
            evaluate(concurrency["cancel-in-progress"], ctx),
        )

    ready = context("ci.yml", "ready_for_review", {}, False, run_id=102)
    rerun = context("ci.yml", "opened", {}, True, run_id=101, attempt="2")
    assert policy(ready) == ("CI-refs/pull/17/merge", True)
    assert policy(rerun) == ("CI-101", False)


def test_metadata_edit_on_a_draft_keeps_the_metadata_label():
    states = job_states("ci.yml", context("ci.yml", "edited", {"title": MARKER}, True))
    assert states == {
        job: (f"Not run for a metadata edit - {name}", False)
        for job, name in CHECKS["ci.yml"].items()
    }


def test_push_ignores_the_draft_guard():
    states = job_states("ci.yml", context("ci.yml", "push", {}, None))
    assert states["mode"] == ("Gate mode", True)


def test_wheel_build_skips_drafts_and_runs_when_ready():
    config = workflow("wheel-ownership.yml")
    triggers = config.get("on", config.get(True))
    assert triggers["pull_request"] == {
        "types": ["opened", "synchronize", "reopened", "ready_for_review"]
    }
    assert "workflow_dispatch" in triggers
    job = config["jobs"]["wheel-ownership"]
    filename = "wheel-ownership.yml"
    assert not evaluate(job["if"], context(filename, "synchronize", {}, True))
    assert evaluate(job["if"], context(filename, "ready_for_review", {}, False))
    assert evaluate(job["if"], context(filename, "push", {}, None))
