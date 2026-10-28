"""Guard runner routing and release isolation on persistent workers."""

import ast
import json
import os
import re
import subprocess
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
            assert len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)
            return interpret(node.left) == interpret(node.comparators[0])
        assert isinstance(node, ast.BoolOp)
        result = interpret(node.values[0])
        for operand in node.values[1:]:
            if (isinstance(node.op, ast.And) and not result) or (
                isinstance(node.op, ast.Or) and result
            ):
                return result
            result = interpret(operand)
        return result

    return interpret(ast.parse(expression.strip(), mode="eval").body)


@pytest.mark.parametrize(
    "event,fork,head,expected",
    [
        ("pull_request", True, "different", "ubuntu-latest"),
        ("pull_request", False, "same", ["self-hosted", "x64"]),
        ("push", None, None, ["self-hosted", "x64"]),
        ("schedule", None, None, ["self-hosted", "x64"]),
        ("workflow_dispatch", None, None, ["self-hosted", "x64"]),
    ],
)
def test_every_job_routes_trusted_events_and_isolates_forks(
    event: str, fork: bool, head: str, expected: object
) -> None:
    """Cover every declared job, including discovery, domain tests and aggregation."""
    context = {
        "github.event_name": event,
        "github.event.pull_request.head.repo.fork": fork,
        "github.event.pull_request.head.repo.full_name": head,
        "github.repository": "same",
    }
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for job_id, job in load_workflow(path.name)["jobs"].items():
            if "uses" in job:
                assert job["uses"] == "./.github/workflows/domain-matrix.yml"
                assert (WORKFLOWS / "domain-matrix.yml").is_file()
                continue
            assert runner_labels(job["runs-on"], context) == expected, (
                path.name,
                job_id,
                event,
            )


def test_domain_gate_keeps_all_three_jobs_and_read_only_permissions() -> None:
    """Changing the runner route must retain the matrix and aggregate gate."""
    assert load_workflow("ci.yml")["jobs"]["domain-tests"]["uses"] == (
        "./.github/workflows/domain-matrix.yml"
    )
    workflow = load_workflow("domain-matrix.yml")
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
        '#!/usr/bin/env bash\nif [ "$1 $2 $3" = "run twine upload" ]; then\n'
        '  printf "%s\\0" "$@" > "$UPLOAD_ARGS"\nfi\n',
        encoding="utf-8",
        newline="\n",
    )
    recorder.chmod(0o755)
    env = dict(os.environ, PATH=f"{tools}{os.pathsep}{os.environ['PATH']}")
    env.update(RUNNER_TEMP=str(runner), UPLOAD_ARGS=str(tmp_path / "upload-args"))
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
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
            encoding="utf-8",
        )
        arguments = Path(env["UPLOAD_ARGS"]).read_bytes().split(b"\0")[:-1]
        wheels = [os.fsdecode(arg) for arg in arguments if arg.endswith(b".whl")]
        assert wheels == [str(current)]
        assert stale.exists()
    assert destinations[0] != destinations[1]
