"""Keep pull request CI available across target branch changes."""

from pathlib import Path

import pytest
import yaml

CI_WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"


def _load_workflow() -> dict:
    """Read the workflow with the YAML 1.1 event-key conversion handled."""
    return yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))


def test_pull_request_has_no_branch_filters() -> None:
    """Stacked pull requests receive the same workflow as default-base PRs."""
    workflow = _load_workflow()
    events = workflow["on"] if "on" in workflow else workflow[True]
    assert "pull_request" in events
    pull_request = events["pull_request"]
    assert pull_request is None or isinstance(pull_request, dict)
    filters = pull_request or {}
    assert "branches" not in filters
    assert "branches-ignore" not in filters


def test_push_branch_filter_is_unchanged() -> None:
    """Feature pushes do not duplicate pull request runs."""
    workflow = _load_workflow()
    events = workflow["on"] if "on" in workflow else workflow[True]
    assert events["push"]["branches"] == ["main", "develop"]


def test_required_pull_request_check_name_is_unchanged() -> None:
    """The aggregate keeps the name required by branch protection."""
    assert _load_workflow()["jobs"]["pr-gate"]["name"] == "Test (PR gate)"


def _evaluate_expression(expression: str, context: dict) -> object:
    """Evaluate the equality and short-circuit subset used by concurrency."""
    expression = expression.strip()
    for operator in ("||", "&&", "=="):
        left, separator, right = expression.partition(operator)
        if separator:
            value = _evaluate_expression(left, context)
            if operator == "||":
                return value or _evaluate_expression(right, context)
            if operator == "&&":
                return value and _evaluate_expression(right, context)
            return value == _evaluate_expression(right, context)
    if expression.startswith("'") and expression.endswith("'"):
        return expression[1:-1]
    return context[expression]


def _concurrency(event: str, ref: str, run_id: int) -> tuple[str, bool]:
    """Render the configured group and cancellation expression for a run."""
    import re

    concurrency = _load_workflow()["concurrency"]
    context = {
        "github.workflow": "CI",
        "github.event_name": event,
        "github.ref": ref,
        "github.run_id": run_id,
    }
    group = re.sub(
        r"\$\{\{(.*?)\}\}",
        lambda match: str(_evaluate_expression(match[1], context)),
        concurrency["group"],
    )
    cancel = concurrency["cancel-in-progress"]
    if isinstance(cancel, str):
        cancel = _evaluate_expression(
            cancel.removeprefix("${{").removesuffix("}}"), context
        )
    assert isinstance(cancel, bool)
    return group, cancel


def test_concurrency_expression_contract() -> None:
    """Only pull request runs share a ref group and cancel earlier runs."""
    concurrency = _load_workflow()["concurrency"]
    assert concurrency["group"] == (
        "${{ github.workflow }}-"
        "${{ github.event_name == 'pull_request' && github.ref || github.run_id }}"
    )
    assert (
        concurrency["cancel-in-progress"]
        == "${{ github.event_name == 'pull_request' }}"
    )


def test_concurrency_event_behavior() -> None:
    """Distinct non-PR runs never share groups, even on the same ref."""
    first_pr = _concurrency("pull_request", "refs/pull/1/merge", 101)
    repeated_pr = _concurrency("pull_request", "refs/pull/1/merge", 102)
    other_pr = _concurrency("pull_request", "refs/pull/2/merge", 103)
    assert first_pr == repeated_pr == ("CI-refs/pull/1/merge", True)
    assert other_pr == ("CI-refs/pull/2/merge", True)
    assert first_pr[0] != other_pr[0]

    runs = [
        ("push", 104),
        ("push", 105),
        ("schedule", 106),
        ("workflow_dispatch", 107),
    ]
    groups = []
    for event, run_id in runs:
        group, cancel = _concurrency(event, "refs/heads/main", run_id)
        assert group == f"CI-{run_id}"
        assert cancel is False
        groups.append(group)
    assert len(set(groups)) == len(runs)


def test_pull_request_activity_types() -> None:
    """Retargeting starts fresh gates while preserving the default events."""
    workflow = _load_workflow()
    events = workflow["on"] if "on" in workflow else workflow[True]
    pull_request = events["pull_request"] or {}
    assert pull_request.get("types") == [
        "opened",
        "synchronize",
        "reopened",
        "edited",
    ]


def test_jobs_and_steps_do_not_filter_edit_events() -> None:
    """Every edit runs the gates so skipped checks cannot mask failures."""
    for job_id, job in _load_workflow()["jobs"].items():
        conditions = [job.get("if", "")]
        conditions.extend(step.get("if", "") for step in job.get("steps", []))
        for condition in conditions:
            for event_field in ("github.event.action", "github.event.changes"):
                assert event_field not in str(condition), (job_id, condition)


def _checkout_steps() -> list:
    """Enumerate every checkout, including the optional full test matrix."""
    return [
        (job_id, index)
        for job_id, job in _load_workflow()["jobs"].items()
        for index, step in enumerate(job.get("steps", []))
        if step.get("uses", "").startswith("actions/checkout@")
    ]


@pytest.mark.parametrize("job_id,index", _checkout_steps())
def test_checkout_resolves_and_guards_event_base(job_id: str, index: int) -> None:
    """Every checkout tests a merge verified against the event's base commit."""
    steps = _load_workflow()["jobs"][job_id]["steps"]
    assert index > 0, job_id
    resolve, checkout, guard = steps[index - 1 : index + 2]
    condition = "github.event_name == 'pull_request'"
    assert resolve["if"] == guard["if"] == condition
    assert resolve["id"] == "resolve_merge"
    assert checkout["with"]["ref"] == (
        "${{ steps.resolve_merge.outputs.sha || github.sha }}"
    )
    assert resolve["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "REPOSITORY": "${{ github.repository }}",
        "PR_NUMBER": "${{ github.event.pull_request.number }}",
        "BASE_SHA": "${{ github.event.pull_request.base.sha }}",
    }
    script = resolve["run"]
    for required in (
        'gh api "repos/$REPOSITORY/pulls/$PR_NUMBER"',
        "--jq '.merge_commit_sha // empty'",
        'gh api "repos/$REPOSITORY/commits/$sha"',
        "--jq '.parents[0].sha // empty'",
        '"$first_parent" = "$BASE_SHA"',
        'echo "sha=$sha" >> "$GITHUB_OUTPUT"',
        "seq 1 10",
        "sleep 6",
        "exit 1",
    ):
        assert required in script, (job_id, required)
    assert guard["env"] == {"BASE_SHA": "${{ github.event.pull_request.base.sha }}"}
    for required in (
        "git cat-file -p HEAD | sed -n 's/^parent //p' | head -n 1",
        '"$first_parent" != "$BASE_SHA"',
        "git rev-parse HEAD",
        "git rev-parse 'HEAD^{tree}'",
        "tested=$tested first_parent=$first_parent base=$BASE_SHA tree=$tree",
        "exit 1",
    ):
        assert required in guard["run"], (job_id, required)
