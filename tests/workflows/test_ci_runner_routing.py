"""Guard runner routing and release isolation on persistent workers."""

import ast
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github/workflows"


def load_workflow(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def runner_labels(expression: str, context: dict) -> object:
    """Interpret the selectors' Boolean subset; this is no Actions engine."""
    expression = expression.removeprefix("${{").removesuffix("}}")
    expression = re.sub(
        r"fromJSON\('([^']*)'\)", lambda match: repr(json.loads(match[1])), expression
    )
    expression = re.sub(
        r"github\.[\w.]+", lambda match: repr(context.get(match[0])), expression
    )
    expression = expression.replace("&&", " and ").replace("||", " or ")

    def interpret(node):
        if isinstance(node, (ast.Constant, ast.List)):
            return ast.literal_eval(node)
        if isinstance(node, ast.Compare):
            assert len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))
            left, right = interpret(node.left), interpret(node.comparators[0])
            return (
                left != right if isinstance(node.ops[0], ast.NotEq) else left == right
            )
        assert isinstance(node, ast.BoolOp)
        result = interpret(node.values[0])
        for operand in node.values[1:]:
            if (isinstance(node.op, ast.And) and not result) or (
                isinstance(node.op, ast.Or) and result
            ):
                return result
            result = interpret(operand)
        return result

    return interpret(ast.parse(f"({expression.strip()})", mode="eval").body)


@pytest.mark.parametrize(
    "event,fork,head,expected",
    [
        ("pull_request", True, "different", "ubuntu-latest"),
        ("pull_request", None, None, "ubuntu-latest"),
        ("pull_request", False, None, "ubuntu-latest"),
        ("pull_request", False, "different", "ubuntu-latest"),
        ("pull_request", False, "same", ["self-hosted", "x64", "linux"]),
        ("push", None, None, ["self-hosted", "x64", "linux"]),
        ("schedule", None, None, ["self-hosted", "x64", "linux"]),
        ("workflow_dispatch", None, None, ["self-hosted", "x64", "linux"]),
    ],
)
def test_every_job_routes_trusted_events_and_isolates_forks(
    event: str, fork: bool | None, head: str | None, expected: object
) -> None:
    """Cover every declared job, including discovery, domain tests and aggregation."""
    context = {
        "github.event_name": event,
        "github.event.pull_request.head.repo.fork": fork,
        "github.event.pull_request.head.repo.full_name": head,
        "github.repository": "same",
    }
    for path in sorted(WORKFLOWS.glob("*.yml")):
        workflow = load_workflow(path.name)
        events = workflow.get("on", workflow.get(True))
        assert events and set(events) <= {
            "push",
            "pull_request",
            "schedule",
            "workflow_dispatch",
            "workflow_call",
        }, "Unsupported workflow trigger requires a routing policy review"
        for job_id, job in workflow["jobs"].items():
            if "uses" in job:
                assert job["uses"] == "./.github/workflows/domain-matrix.yml"
                assert (WORKFLOWS / "domain-matrix.yml").is_file()
                continue
            if path.name == "release.yml" and job_id in {
                "publish-testpypi",
                "publish-pypi",
            }:
                assert job["runs-on"] == "ubuntu-latest"
                assert set(events) <= {"push", "workflow_dispatch"}
                continue
            if isinstance(job["runs-on"], list):
                assert events and set(events) <= {
                    "push",
                    "schedule",
                    "workflow_dispatch",
                }, "Literal runners require trusted triggers"
                assert {"self-hosted", "x64", "linux"} <= set(
                    job["runs-on"]
                ), "Trusted runners require Linux x64"
                continue
            assert runner_labels(job["runs-on"], context) == expected, (
                path.name,
                job_id,
                event,
            )


@pytest.mark.parametrize("event", ["push", "schedule", "workflow_dispatch"])
def test_routing_accepts_literal_labels_for_trusted_workflows(
    tmp_path: Path, monkeypatch, event: str
) -> None:
    """A workflow without PR entry points may use a literal runner list."""
    workflow = {
        "on": {event: None},
        "jobs": {"full-suite": {"runs-on": ["self-hosted", "x64", "linux"]}},
    }
    (tmp_path / "trusted.yml").write_text(yaml.safe_dump(workflow), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "WORKFLOWS", tmp_path)
    test_every_job_routes_trusted_events_and_isolates_forks(
        event, None, None, ["self-hosted", "x64", "linux"]
    )


@pytest.mark.parametrize(
    "event", ["pull_request", "workflow_call", "pull_request_target"]
)
def test_literal_labels_cannot_bypass_untrusted_event_routing(
    tmp_path: Path, monkeypatch, event: str
) -> None:
    """Reusable workflows must retain the caller's PR isolation policy."""
    workflow = {
        "on": {"workflow_dispatch": None, event: None},
        "jobs": {"unsafe": {"runs-on": ["self-hosted", "x64"]}},
    }
    (tmp_path / "unsafe.yml").write_text(yaml.safe_dump(workflow), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "WORKFLOWS", tmp_path)
    with pytest.raises(
        AssertionError,
        match=(
            "Unsupported workflow trigger"
            if event == "pull_request_target"
            else "Literal runners require trusted triggers"
        ),
    ):
        test_every_job_routes_trusted_events_and_isolates_forks(
            "pull_request", None, None, "ubuntu-latest"
        )


@pytest.mark.parametrize(
    "event", ["pull_request_target", "issue_comment", "workflow_run"]
)
def test_expression_routing_rejects_unsupported_triggers(tmp_path, monkeypatch, event):
    """A new event cannot silently inherit access to persistent workers."""
    workflow = {
        "on": {event: None},
        "jobs": {"unsafe": {"runs-on": "${{ 'ubuntu-latest' }}"}},
    }
    (tmp_path / "unsafe.yml").write_text(yaml.safe_dump(workflow), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "WORKFLOWS", tmp_path)
    with pytest.raises(AssertionError, match="Unsupported workflow trigger"):
        test_every_job_routes_trusted_events_and_isolates_forks(
            event, None, None, "ubuntu-latest"
        )


def test_literal_runners_require_linux(tmp_path, monkeypatch):
    workflow = {
        "on": {"workflow_dispatch": None},
        "jobs": {"full-suite": {"runs-on": ["self-hosted", "x64"]}},
    }
    (tmp_path / "trusted.yml").write_text(yaml.safe_dump(workflow), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "WORKFLOWS", tmp_path)
    with pytest.raises(AssertionError, match="Trusted runners require Linux x64"):
        test_every_job_routes_trusted_events_and_isolates_forks(
            "workflow_dispatch", None, None, ["self-hosted", "x64", "linux"]
        )


@pytest.mark.parametrize("job_id", ["publish-testpypi", "publish-pypi"])
def test_publish_jobs_use_ephemeral_workers(job_id):
    """Index tokens must not share a persistent worker with PR code."""
    job = load_workflow("release.yml")["jobs"][job_id]
    assert job["runs-on"] == "ubuntu-latest"
    assert not any("checkout@" in step.get("uses", "") for step in job["steps"])


@pytest.mark.parametrize(
    "name", ["brand-guard.yml", "ci.yml", "docs.yml", "release.yml"]
)
def test_workflow_tokens_default_to_read_only(name):
    assert load_workflow(name)["permissions"] == {"contents": "read"}
    if name == "release.yml":
        assert load_workflow(name)["jobs"]["github-release"]["permissions"] == {
            "contents": "write"
        }


def test_pr_title_has_only_read_access_to_pull_requests():
    workflow = load_workflow("pr-validation.yml")
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["pr-title"]["permissions"] == {"pull-requests": "read"}
    assert all(
        job.get("permissions", {}).get("pull-requests") != "write"
        for job in workflow["jobs"].values()
    )


@pytest.mark.parametrize("name", ["pr-validation.yml", "brand-guard.yml", "docs.yml"])
def test_superseded_pr_runs_cancel_within_the_same_workflow_and_ref(name):
    concurrency = load_workflow(name)["concurrency"]
    assert concurrency["group"] == (
        "${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}"
    )
    cancel = concurrency["cancel-in-progress"]
    for event in ("pull_request", "push", "workflow_dispatch"):
        assert runner_labels(cancel, {"github.event_name": event}) is (
            event == "pull_request"
        )


def test_releases_serialize_across_tags_without_cancelling():
    assert load_workflow("release.yml")["concurrency"] == {
        "group": "release-publishing",
        "cancel-in-progress": False,
    }


def test_package_verification_uses_an_isolated_tool_environment():
    steps = load_workflow("release.yml")["jobs"]["build"]["steps"]
    verify = next(step for step in steps if step["name"] == "Verify package")
    assert shlex.split(verify["run"]) == [
        "uv",
        "run",
        "--no-project",
        "--with",
        "twine",
        "twine",
        "check",
        "dist/*",
    ]


@pytest.mark.parametrize(
    "workflow_name,job_id,maximum",
    [
        ("domain-matrix.yml", "discover", 10),
        ("domain-matrix.yml", "test-domain", 60),
        ("domain-matrix.yml", "aggregate", 10),
        ("ci.yml", "lint", 30),
        ("ci.yml", "security", 30),
        ("release.yml", "publish-testpypi", 15),
        ("release.yml", "publish-pypi", 15),
    ],
)
def test_expensive_and_publishing_jobs_have_bounded_timeouts(
    workflow_name: str, job_id: str, maximum: int
) -> None:
    assert (
        0 < load_workflow(workflow_name)["jobs"][job_id]["timeout-minutes"] <= maximum
    )


@pytest.mark.parametrize(
    "job_id,step_name,tool",
    [
        ("publish-testpypi", "Publish to Test PyPI", "twine"),
        ("publish-pypi", "Publish to PyPI", "twine"),
        ("publish-testpypi", "Test installation from Test PyPI", "python"),
    ],
)
def test_release_tools_ignore_reused_workspace(
    job_id: str, step_name: str, tool: str
) -> None:
    """Never discover a project or mutate its environment during publication."""
    job = load_workflow("release.yml")["jobs"][job_id]
    step = next(step for step in job["steps"] if step["name"] == step_name)
    assert step.get("working-directory") == "${{ runner.temp }}"
    commands = [
        shlex.split(line)
        for line in step["run"].replace("\\\n", " ").splitlines()
        if line.strip() and not line.lstrip().startswith("sleep ")
    ]
    assert len(commands) == 1
    command = commands[0]
    assert command[:3] == ["uv", "run", "--no-project"]
    assert command[3] == "--with"
    if tool == "twine":
        assert command[4:7] == ["twine", "twine", "upload"]
    else:
        assert "validate" in job["needs"]
        assert command[4] == "worldenergydata==${{ needs.validate.outputs.version }}"
        assert command[-3:] == ["python", "-c", "import worldenergydata"]


def test_domain_gate_keeps_all_three_jobs_and_read_only_permissions() -> None:
    """Changing the runner route must retain the matrix and aggregate gate."""
    assert load_workflow("ci.yml")["jobs"]["domain-tests"]["uses"] == (
        "./.github/workflows/domain-matrix.yml"
    )
    caller = load_workflow("ci.yml")["jobs"]["domain-tests"]
    assert caller["with"]["test-runner"] == (
        "env WED_FAST_GATE=1 uv run --with pytest-xdist pytest"
    )
    workflow = load_workflow("domain-matrix.yml")
    assert "test-runner" in workflow[True]["workflow_call"]["inputs"]
    assert any(
        step.get("env", {}).get("TEST_RUNNER") == "${{ inputs.test-runner }}"
        and "$TEST_RUNNER $TARGETS" in step.get("run", "")
        for step in workflow["jobs"]["test-domain"]["steps"]
    )
    assert workflow["permissions"] == {"contents": "read"}
    jobs = workflow["jobs"]
    assert set(jobs) == {"discover", "test-domain", "aggregate"}
    assert jobs["test-domain"]["strategy"]["fail-fast"] is False
    assert jobs["test-domain"]["strategy"]["matrix"] == (
        "${{ fromJSON(needs.discover.outputs.matrix) }}"
    )
    assert jobs["aggregate"]["if"] == "always()"
    assert jobs["aggregate"]["needs"] == ["discover", "test-domain"]
    for job in jobs.values():
        for step in job.get("steps", []):
            if "checkout@" in step.get("uses", ""):
                assert step["with"]["persist-credentials"] is False


def test_domain_contract_reads_utf8_and_writes_lf_with_ascii_locale(tmp_path):
    """Execute the generated validator with UTF-8 mode explicitly disabled."""
    steps = load_workflow("domain-matrix.yml")["jobs"]["discover"]["steps"]
    shell = next(
        step["run"] for step in steps if "DOMAIN_MATRIX_SCRIPT" in step.get("run", "")
    )
    script = shell.split("<<'DOMAIN_MATRIX_SCRIPT'\n", 1)[1].split(
        "\nDOMAIN_MATRIX_SCRIPT", 1
    )[0]
    validator = tmp_path / "validator.py"
    validator.write_text(script, encoding="utf-8", newline="\n")
    source = tmp_path / "selector-output"
    matrix = {
        "include": [{"name": "core", "targets": "tests/\u03bb.py", "mode": "seq"}]
    }
    source.write_text(
        "scope=modules\nmatrix=" + json.dumps(matrix, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    output = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8=0",
            str(validator),
            str(source),
            "--github-output",
            str(output),
        ],
        env={
            **os.environ,
            "LC_ALL": "C",
            "PYTHONCOERCECLOCALE": "0",
            "PYTHONUTF8": "0",
        },
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert output.read_bytes() == b"matrix-size=1\n"


@pytest.mark.parametrize("job_id", ["publish-testpypi", "publish-pypi"])
def test_publish_excludes_stale_distributions(tmp_path: Path, job_id: str) -> None:
    """Execute both publish scripts with a stale wheel and repeated downloads."""
    job = load_workflow("release.yml")["jobs"][job_id]
    steps = job["steps"]
    preparations = [step for step in steps if step.get("id") == "release_dist"]
    assert len(preparations) == 1, "Publishing needs a fresh download directory"
    prepare = preparations[0]
    download = next(
        step for step in steps if "download-artifact@" in step.get("uses", "")
    )
    publish = next(step for step in steps if "twine upload" in step.get("run", ""))
    assert steps.index(prepare) < steps.index(download) < steps.index(publish)
    assert download["with"]["path"] == "${{ steps.release_dist.outputs.path }}"
    assert publish["env"]["DIST_DIR"] == download["with"]["path"]
    tools, runner, dist = (tmp_path / name for name in ("tools", "runner temp", "dist"))
    for directory in (tools, runner, dist):
        directory.mkdir()
    stale = dist / "stale-0.1-py3-none-any.whl"
    stale.write_bytes(b"")
    recorder = tools / "uv"
    recorder.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\0" "$@" > "$UPLOAD_ARGS"\n'
        'printf "%s" "$PWD" > "$UPLOAD_CWD"\n',
        encoding="utf-8",
        newline="\n",
    )
    recorder.chmod(0o755)
    env = dict(os.environ, PATH=f"{tools}{os.pathsep}{os.environ['PATH']}")
    env.update(
        RUNNER_TEMP=str(runner),
        UPLOAD_ARGS=str(tmp_path / "upload-args"),
        UPLOAD_CWD=str(tmp_path / "upload-cwd"),
    )
    destinations = []
    for attempt in range(2):
        output = tmp_path / f"output-{attempt}"
        env["GITHUB_OUTPUT"] = str(output)
        subprocess.run(
            ["bash", "-euo", "pipefail", "-c", prepare["run"]],
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
            encoding="utf-8",
        )
        directory = Path(
            output.read_text(encoding="utf-8").strip().removeprefix("path=")
        )
        assert directory.is_dir() and directory.parent == runner
        assert not list(directory.iterdir())
        destinations.append(directory)
        current = directory / f"current-{attempt}-py3-none-any.whl"
        current.write_bytes(b"")
        env["DIST_DIR"] = str(directory)
        subprocess.run(
            ["bash", "-euo", "pipefail", "-c", publish["run"]],
            cwd=(
                runner
                if publish.get("working-directory") == "${{ runner.temp }}"
                else tmp_path
            ),
            env=env,
            check=True,
            capture_output=True,
            encoding="utf-8",
        )
        arguments = Path(env["UPLOAD_ARGS"]).read_bytes().split(b"\0")[:-1]
        assert arguments[:6] == [
            b"run",
            b"--no-project",
            b"--with",
            b"twine",
            b"twine",
            b"upload",
        ]
        assert Path(env["UPLOAD_CWD"]).read_text(encoding="utf-8") == str(runner)
        wheels = [os.fsdecode(arg) for arg in arguments if arg.endswith(b".whl")]
        assert wheels == [str(current)]
        assert stale.exists()
    assert destinations[0] != destinations[1]


def _events(path: Path) -> dict:
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    return workflow["on"] if "on" in workflow else workflow[True]


def test_pr_gate_is_fast_only() -> None:
    """PRs run lint, the secret scan and touched-module tests (28 Oct 2026)."""
    jobs = load_workflow("ci.yml")["jobs"]
    assert set(jobs) == {
        "mode",
        "domain-tests",
        "lint",
        "security",
        "lint-gate",
        "security-gate",
        "pr-gate",
    }
    runner = jobs["domain-tests"]["with"]["test-runner"]
    assert runner.startswith("env WED_FAST_GATE=1 ")
    lint_script = "\n".join(step.get("run", "") for step in jobs["lint"]["steps"])
    assert "uv sync" not in lint_script
    assert "uv lock" not in lint_script


def test_no_workflow_uses_github_schedule() -> None:
    """The daily full run is dispatched by our own cron, not GitHub's schedule."""
    for path in sorted(WORKFLOWS.glob("*.yml")):
        assert "schedule" not in _events(path), path.name


def test_pr_validation_keeps_main_advisory_job_removals() -> None:
    workflow = yaml.safe_load((WORKFLOWS / "pr-validation.yml").read_text())
    assert "changelog-check" not in workflow["jobs"]
    assert "code-owners" not in workflow["jobs"]
