"""Execute the edit subscribers' job guards and check names for real event shapes."""

import re
from pathlib import Path

import pytest
import yaml

from tests.workflows.test_ci_triggers import _evaluate_expression, _render

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github/workflows"
# Code-event check names at the introduction of metadata-only skips.
CHECKS = {
    "ci.yml": {
        "mode": "Gate mode",
        "domain-tests": "domain-tests",
        "lint": "Lint (full)",
        "security": "Security Scan (full)",
        "lint-gate": "Lint",
        "security-gate": "Security Scan",
        "pr-gate": "Test (PR gate)",
    },
    "pr-validation.yml": {
        "pr-title": "Validate PR Title",
        "file-size": "Check File Sizes",
        "sensitive-files": "Check Sensitive Files",
        "pack-lint": "Lint Changed Knowledge Packs",
    },
}
# Subscribed pull-request activity types. Only CI skips drafts, so only CI hears ready_for_review.
TYPES = {
    "ci.yml": ["opened", "synchronize", "reopened", "edited", "ready_for_review"],
    "pr-validation.yml": ["opened", "synchronize", "reopened", "edited"],
}
MARKER = {"from": ""}
CODE_EVENTS = [
    ("opened", {}, "1"),
    ("synchronize", {}, "1"),
    ("reopened", {}, "1"),
    ("ready_for_review", {}, "1"),
    ("edited", {"base": {"ref": {"from": "main"}}}, "1"),
    ("edited", {"base": MARKER, "title": MARKER, "body": MARKER}, "1"),
    ("edited", {}, "1"),  # Unrecognized edit: run the full gate.
    ("edited", {"title": MARKER}, None),  # Missing attempt: run checks.
    ("edited", {"title": MARKER}, "2"),
    ("edited", {"body": MARKER}, "2"),
    ("push", {}, "1"),
]


def workflow(filename):
    return yaml.safe_load((WORKFLOWS / filename).read_text(encoding="utf-8"))


def event_context(filename, action, changes, attempt="1", run_id=101):
    return {
        "github.workflow": workflow(filename)["name"],
        "github.event_name": "push" if action == "push" else "pull_request",
        "github.event.action": None if action == "push" else action,
        "github.event.pull_request.number": None if action == "push" else 17,
        "github.ref": "refs/heads/main" if action == "push" else "refs/pull/17/merge",
        "github.run_id": run_id,
        "github.run_attempt": attempt,
        **{f"github.event.changes.{key}": value for key, value in changes.items()},
    }


def evaluate(condition, context):
    return _evaluate_expression(
        condition.removeprefix("${{").removesuffix("}}"), context
    )


def code_job_runs(job):
    """Evaluate a PR validation job for an ordinary update."""
    context = event_context("pr-validation.yml", "synchronize", {})
    return bool(evaluate(job.get("if", "True"), context))


def job_states(filename, context):
    """Follow needs in dependency order, assuming a successful, uncancelled code run."""
    jobs = workflow(filename)["jobs"]
    states = {}
    context = context.copy()
    for job_id in CHECKS[filename]:
        job = jobs[job_id]
        condition = job.get("if", "True")
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        dependencies_pass = all(states[dep][1] for dep in needs)
        explicit_status = "cancelled()" in condition or "always()" in condition
        runs = (explicit_status or dependencies_pass) and bool(
            evaluate(condition, context)
        )
        states[job_id] = (_render(job.get("name", job_id), context), runs)
        context[f"needs.{job_id}.result"] = "success" if runs else "skipped"
        if job_id == "mode" and runs:
            replay = job["steps"][0]["env"]["REPLAY"]
            assert not evaluate(replay, context), "code run must execute current checks"
            context["needs.mode.outputs.replay"] = "false"
    assert set(states) == set(jobs)
    return states


@pytest.mark.parametrize("filename", CHECKS)
@pytest.mark.parametrize("action,changes,attempt", CODE_EVENTS)
def test_code_events_keep_checks(filename, action, changes, attempt):
    context = event_context(filename, action, changes, attempt)
    config = workflow(filename)
    triggers = config.get("on", config.get(True))
    if action == "push" and filename == "pr-validation.yml":
        assert "push" not in triggers
        return
    if action != "push":
        assert triggers["pull_request"] == {"types": TYPES[filename]}
    else:
        assert triggers["push"] == {"branches": ["main", "develop"]}
    assert job_states(filename, context) == {
        job: (name, action != "push" or job not in {"domain-tests", "pr-gate"})
        for job, name in CHECKS[filename].items()
    }
    concurrency = config["concurrency"]
    group = _render(concurrency["group"], context)
    cancel = evaluate(concurrency["cancel-in-progress"], context)
    pr_group = {
        "ci.yml": "CI-refs/pull/17/merge",
        "pr-validation.yml": "PR Validation-17",
    }[filename]
    if action == "push":
        assert group == "CI-101" and cancel is False
    elif changes.keys() & {"title", "body"} and "base" not in changes:
        # Rerunning an old edit must not evict a newer head's pending code checks.
        assert group != pr_group and cancel is False
    else:
        assert group == pr_group and cancel is True


@pytest.mark.parametrize("filename", CHECKS)
@pytest.mark.parametrize("fields", [("title",), ("body",), ("title", "body")])
def test_metadata_edit_only_runs_title_check(filename, fields):
    changes = {key: {"from": None} for key in fields}
    contexts = [
        event_context(filename, "edited", changes, run_id=n) for n in (101, 102)
    ]
    states = job_states(filename, contexts[0])
    for job, usual in CHECKS[filename].items():
        expected = (
            (usual, True)
            if job == "pr-title"
            else (f"Not run for a metadata edit - {usual}", False)
        )
        assert states[job] == expected, job
    concurrency = workflow(filename)["concurrency"]
    groups = {_render(concurrency["group"], ctx) for ctx in contexts}
    assert all(
        evaluate(concurrency["cancel-in-progress"], ctx) is False for ctx in contexts
    )
    assert len(groups) == 2
    code = event_context(filename, "synchronize", {})
    assert _render(concurrency["group"], code) not in groups


def test_only_audited_workflows_subscribe_to_edits():
    listeners = set()
    for path in WORKFLOWS.glob("*.y*ml"):
        config = workflow(path.name)
        triggers = config.get("on", config.get(True))
        assert "pull_request_target" not in triggers, path
        if "edited" in (triggers.get("pull_request") or {}).get("types", []):
            listeners.add(path.name)
    assert listeners == CHECKS.keys()


def workflow_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from workflow_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from workflow_strings(item)


def test_only_title_check_reads_pr_text():
    """Change-marker presence is allowed. The current and previous text are inputs."""
    title_action = "amannn/action-semantic-pull-request@"
    for path in WORKFLOWS.glob("*.y*ml"):
        config = workflow(path.name)
        if path.name == "pr-validation.yml":
            (step,) = config["jobs"]["pr-title"]["steps"]
            assert step.pop("uses").startswith(title_action)
            assert "if" not in step
        # Inspect the decoded YAML strings so quoting cannot hide a property.
        text = "\n".join(workflow_strings(config))
        assert title_action not in text, path
        # Normalize bracket-property notation as well as dot-property notation.
        text = re.sub(r"""\[\s*['"](\w+)['"]\s*\]""", r".\1", text)
        assert not re.search(r"pull_request\s*\.\s*(title|body)\b", text, re.I), path
        markers = r"changes\s*\.\s*(title|body)\b"
        text = re.sub(markers + r"\s*!=\s*null\b", "", text, flags=re.I)
        assert not re.search(markers, text, re.I), path
        assert not re.search(
            r"gh\s+pr\s+view[^\n]*--json[^\n]*(body|title)\b", text, re.I
        ), path
