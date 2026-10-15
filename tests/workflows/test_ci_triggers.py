"""Keep pull request CI available for every target branch."""

import json
import os
import subprocess
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
def test_checkout_resolves_and_guards_current_base(job_id: str, index: int) -> None:
    """Every checkout verifies both parents against the current base and head."""
    steps = _load_workflow()["jobs"][job_id]["steps"]
    assert index > 0, job_id
    resolve, checkout, guard = steps[index - 1 : index + 2]
    condition = "github.event_name == 'pull_request'"
    assert resolve["if"] == guard["if"] == condition
    assert resolve["id"] == "resolve_merge"
    assert checkout["with"]["ref"] == (
        "${{ steps.resolve_merge.outputs.sha || github.sha }}"
    )
    assert resolve["env"]["BASE_REF"] == ("${{ github.event.pull_request.base.ref }}")
    assert resolve["env"]["HEAD_SHA"] == ("${{ github.event.pull_request.head.sha }}")
    assert "github.event.pull_request.base.sha" not in str(resolve)
    script = resolve["run"]
    for required in (
        "git/ref/heads/$BASE_REF",
        ".object.sha",
        "pulls/$PR_NUMBER",
        "commits/$sha",
        '"$first_parent" = "$tip"',
        '"$second_parent" = "$HEAD_SHA"',
        '"${#parents[@]}" -eq 2',
        "${MERGE_RETRIES:-10}",
        "${MERGE_RETRY_SECONDS:-6}",
        'echo "sha=$sha"',
        'echo "tip=$tip"',
        'echo "head=$HEAD_SHA"',
        "exit 1",
    ):
        assert required in script, (job_id, required)
    assert guard["env"] == {
        "RESOLVED_SHA": "${{ steps.resolve_merge.outputs.sha }}",
        "BASE_TIP": "${{ steps.resolve_merge.outputs.tip }}",
        "HEAD_SHA": "${{ steps.resolve_merge.outputs.head }}",
        "EVENT_BASE": "${{ github.event.pull_request.base.sha }}",
    }
    for required in (
        "git cat-file -p HEAD",
        '"$tested" != "$RESOLVED_SHA"',
        '"$first_parent" != "$BASE_TIP"',
        '"$second_parent" != "$HEAD_SHA"',
        '"${#parents[@]}" -ne 2',
        "git rev-parse 'HEAD^{tree}'",
        "tested=$tested first_parent=$first_parent second_parent=$second_parent",
        "tip=$BASE_TIP event_base=$EVENT_BASE tree=$tree",
        "exit 1",
    ):
        assert required in guard["run"], (job_id, required)


@pytest.mark.parametrize("job_id,index", _checkout_steps())
@pytest.mark.parametrize(
    "case,expected_calls",
    [
        ("moved_base", 1),
        ("old_base", 3),
        ("wrong_head", 3),
        ("conflict", 1),
        ("no_merge", 1),
        ("extra_parent", 3),
        ("refresh", 2),
    ],
)
def test_resolve_merge_behavior(
    tmp_path: Path, job_id: str, index: int, case: str, expected_calls: int
) -> None:
    """Run the actual resolver against API fixtures, including stale events."""
    steps = _load_workflow()["jobs"][job_id]["steps"]
    resolve = steps[index - 1]
    stub = tmp_path / "gh"
    stub.write_text(
        "#!/usr/bin/env python3\n"
        + r"""import json
import os
import pathlib
import sys

root = pathlib.Path(os.environ["FIXTURE_ROOT"])
route = sys.argv[2]
with (root / "calls").open("a") as stream:
    stream.write(route + "\n")
fixture = json.loads((root / "fixture.json").read_text())
if "/git/ref/heads/" in route:
    print(fixture["tip"])
elif "/pulls/" in route:
    print(fixture["pr"])
elif "/commits/" in route:
    calls = (root / "calls").read_text().count("/commits/")
    parents = fixture["parents"]
    if fixture["refresh"] and calls > 1:
        parents = [fixture["tip"], "event-head"]
    print("\n".join(parents))
else:
    sys.exit(2)
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    fixture = {
        "tip": "current-base",
        "pr": "false merge" if case == "conflict" else "true merge",
        "parents": ["current-base", "event-head"],
        "refresh": case == "refresh",
    }
    if case in {"old_base", "refresh"}:
        fixture["parents"][0] = "old-base"
    if case == "wrong_head":
        fixture["parents"][1] = "other-head"
    if case == "extra_parent":
        fixture["parents"].append("third-parent")
    if case == "no_merge":
        fixture["pr"] = "null"
    (tmp_path / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")
    output = tmp_path / "output"
    env = dict(
        os.environ,
        PATH=f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        FIXTURE_ROOT=str(tmp_path),
        REPOSITORY="example/repository",
        PR_NUMBER="1",
        BASE_REF="main",
        HEAD_SHA="event-head",
        EVENT_BASE="old-event-base",
        GITHUB_OUTPUT=str(output),
        MERGE_RETRIES="3",
        MERGE_RETRY_SECONDS="0",
    )
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", resolve["run"]],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    calls = (tmp_path / "calls").read_text(encoding="utf-8")
    assert calls.count("/git/ref/heads/main") == expected_calls, result.stdout
    assert calls.count("/pulls/1") == expected_calls
    if case in {"moved_base", "refresh"}:
        assert result.returncode == 0, result.stdout + result.stderr
        assert output.read_text().splitlines() == [
            "sha=merge",
            "tip=current-base",
            "head=event-head",
        ]
    else:
        assert result.returncode != 0
        assert not output.exists()
        if case in {"conflict", "no_merge"}:
            assert "not mergeable" in result.stdout
        else:
            assert "current-base" in result.stdout
            assert "event-head" in result.stdout
            assert "parents" in result.stdout


# Exercise merge selection again after a base change.
