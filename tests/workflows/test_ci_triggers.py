"""Keep pull request CI available for every target branch."""

import os
import shutil
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
def test_checkout_builds_current_base_merge(job_id: str, index: int) -> None:
    """Every checkout builds and guards the merge without API polling."""
    steps = _load_workflow()["jobs"][job_id]["steps"]
    checkout, merge = steps[index : index + 2]
    assert checkout["with"]["ref"] == (
        "${{ github.event.pull_request.head.sha || github.sha }}"
    )
    assert checkout["with"]["repository"] == (
        "${{ github.event.pull_request.head.repo.full_name || github.repository }}"
    )
    assert merge["id"] == "local_merge"
    assert merge["if"] == "github.event_name == 'pull_request'"
    assert merge["env"] == {
        "BASE_REF": "${{ github.event.pull_request.base.ref }}",
        "BASE_URL": "${{ github.event.pull_request.base.repo.clone_url }}",
        "HEAD_URL": "${{ github.event.pull_request.head.repo.clone_url }}",
        "PR_HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
        "EVENT_BASE": "${{ github.event.pull_request.base.sha }}",
    }
    script = merge["run"]
    assert "${{" not in script
    assert 'echo "tip=$tip"' in script
    assert "git cat-file -p HEAD" in script
    for forbidden in ("merge_commit_sha", "gh api", "curl", "sleep"):
        assert forbidden not in CI_WORKFLOW.read_text(encoding="utf-8")
    for line in script.splitlines():
        if "EVENT_BASE" in line:
            assert "event_base=$EVENT_BASE" in line


def _git(root: Path, *args: str) -> str:
    """Run a real Git command and include its diagnostics on failure."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout.strip()


def _commit(root: Path, filename: str, contents: str) -> str:
    """Commit a fixture change using the fixture repository identity."""
    (root / filename).write_text(contents, encoding="utf-8")
    _git(root, "add", filename)
    _git(root, "commit", "-m", "fixture change")
    return _git(root, "rev-parse", "HEAD")


def _fixture_history(root: Path, case: str) -> tuple[Path, str, str, str]:
    """Create diverged base/head histories, including shallow ancestry."""
    origin = root / "origin.git"
    _git(root, "init", "--bare", str(origin))
    source = root / "source"
    _git(root, "clone", origin.as_uri(), str(source))
    _git(source, "config", "user.name", "Test")
    _git(source, "config", "user.email", "test@example.com")
    _git(source, "checkout", "-b", "main")
    event_base = _commit(source, "shared.txt", "original\n")
    if case == "shallow":
        for number in range(55):
            _commit(source, "history.txt", str(number))
    _git(source, "checkout", "-b", "feature")
    filename = "shared.txt" if case == "conflict" else "feature.txt"
    head = _commit(source, filename, "feature\n")
    _git(source, "checkout", "main")
    if case == "descendant":
        tip = _git(source, "rev-parse", "HEAD")
    else:
        filename = "shared.txt" if case == "conflict" else "base.txt"
        tip = _commit(source, filename, "new base\n")
    if case == "shallow":
        for number in range(55):
            tip = _commit(source, "base-history.txt", str(number))
    _git(source, "push", "origin", "main", "feature")
    return origin, event_base, tip, head


@pytest.mark.parametrize("job_id,index", _checkout_steps())
@pytest.mark.parametrize(
    "case", ["moved_base", "conflict", "shallow", "descendant", "no_api"]
)
def test_local_merge_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, job_id: str, index: int, case: str
) -> None:
    """Execute each inline script against real repositories, without an API."""
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(key, raising=False)
    origin, event_base, tip, head = _fixture_history(tmp_path, case)
    runner = tmp_path / "runner"
    _git(
        tmp_path, "clone", "--depth=1", "--branch=feature", origin.as_uri(), str(runner)
    )
    assert _git(runner, "rev-parse", "--is-shallow-repository") == "true"
    tools = tmp_path / "tools"
    tools.mkdir()
    # Only Git and the script's text utility are available; no API clients.
    for tool in ("git", "sed"):
        executable = shutil.which(tool)
        assert executable
        (tools / tool).symlink_to(executable)
    output = tmp_path / "output"
    env = dict(
        os.environ,
        PATH=str(tools),
        BASE_REF="main",
        BASE_URL=origin.as_uri(),
        HEAD_URL=origin.as_uri(),
        PR_HEAD_SHA=head,
        EVENT_BASE=event_base,
        GITHUB_OUTPUT=str(output),
    )
    script = _load_workflow()["jobs"][job_id]["steps"][index + 1]["run"]
    bash = shutil.which("bash")
    assert bash
    result = subprocess.run(
        [bash, "-e", "-o", "pipefail", "-c", script],
        cwd=runner,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if case == "conflict":
        assert result.returncode != 0
        assert "::error::" in result.stdout
        assert _git(runner, "rev-parse", "HEAD") == tip
        assert not (runner / ".git" / "MERGE_HEAD").exists()
        assert not output.exists()
    else:
        assert result.returncode == 0, result.stdout + result.stderr
        parents = _git(runner, "show", "-s", "--format=%P", "HEAD").split()
        assert parents == [tip, head]
        assert output.read_text().splitlines() == [f"tip={tip}"]
        tested = _git(runner, "rev-parse", "HEAD")
        tree = _git(runner, "rev-parse", "HEAD^{tree}")
        assert (
            f"tested={tested} first_parent={tip} second_parent={head} "
            f"tip={tip} event_base={event_base} tree={tree}"
        ) in result.stdout
