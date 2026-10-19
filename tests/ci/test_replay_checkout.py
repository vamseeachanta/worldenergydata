"""Exercise metadata wrappers with PR heads on either side of helper adoption."""

import importlib.util
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
HELPER = "scripts/ci/replay_gate.py"
REQUIRED = {
    "lint-gate": "Lint",
    "type-check-gate": "Type Check",
    "security-gate": "Security Scan",
    "docs-gate": "Documentation",
    "pr-gate": "Test (PR gate)",
}


def _git(root, *args):
    """Keep fixture Git commands independent of inherited repository bindings."""
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)
    return subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-C", str(root), *args],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()


def _snapshot(root):
    """Record synthetic history without relying on configured Git identity."""
    _git(root, "add", ".")
    tree = _git(root, "write-tree")
    commit = (
        f"tree {tree}\n"
        "author Fixture <fixture> 0 +0000\n"
        "committer Fixture <fixture> 0 +0000\n\n"
        "test: replay checkout fixture\n"
    )
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)
    return (
        subprocess.run(
            ["git", "-C", str(root), "hash-object", "-t", "commit", "-w", "--stdin"],
            input=commit.encode(),
            env=env,
            check=True,
            capture_output=True,
            timeout=30,
        )
        .stdout.decode("ascii")
        .strip()
    )


def test_snapshot_survives_windows_stdin_translation(tmp_path, monkeypatch):
    """Text-mode CRLF translation must not corrupt raw Git commit headers."""
    _git(tmp_path, "init", "-q")
    (tmp_path / "README.md").write_bytes(b"fixture\n")
    run = subprocess.run

    def windows_run(args, **kwargs):
        if "hash-object" in args and kwargs.get("text"):
            kwargs["input"] = kwargs["input"].replace("\n", "\r\n")
        return run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", windows_run)
    revision = _snapshot(tmp_path)
    assert _git(tmp_path, "cat-file", "-t", revision) == "commit"


def test_git_preserves_lf_with_autocrlf_enabled(tmp_path):
    """Inherited autocrlf settings must not alter checked-out helper bytes."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "core.autocrlf", "true")
    script = tmp_path / "helper.py"
    contents = b"print('fixture')\n"
    script.write_bytes(contents)
    revision = _snapshot(tmp_path)
    script.unlink()
    _git(tmp_path, "checkout", revision, "--", script.name)
    assert script.read_bytes() == contents


@pytest.fixture(scope="module")
def history(tmp_path_factory):
    """Create a live base and older event/head snapshots around helper adoption."""
    source = tmp_path_factory.mktemp("replay-history")
    _git(source, "init", "-q")
    (source / "README.md").write_text("fixture\n", encoding="utf-8")
    without_helper = _snapshot(source)
    helper = source / HELPER
    helper.parent.mkdir(parents=True)
    helper.write_text(
        "raise RuntimeError('PR helper must not execute')\n", encoding="utf-8"
    )
    with_helper = _snapshot(source)
    # Use the maintained helper bytes as the live-base fixture.
    helper.write_bytes((ROOT / HELPER).read_bytes())
    base = _snapshot(source)
    _git(source, "update-ref", "refs/heads/main", base)
    return source, base, {False: without_helper, True: with_helper}


def _wrapper(job_id):
    """Read the actual checkout and command for each required wrapper."""
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    job = workflow["jobs"][job_id]
    assert job["name"] == REQUIRED[job_id]
    assert job["permissions"] == {"contents": "read", "actions": "read"}
    mode = workflow["jobs"]["mode"]
    checkout, replay = mode["steps"][1:3]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["if"] == replay["if"]
    assert replay["run"].splitlines() == [
        'echo "Replay helper revision: $(git rev-parse HEAD)"',
        "python scripts/ci/replay_gate.py --mode",
    ]
    assert not replay.get("continue-on-error", False)
    return checkout["with"], job["name"]


@pytest.mark.parametrize("job_id", REQUIRED)
@pytest.mark.skipif(os.name == "nt", reason="Workflow shell runs on Linux")
def test_mode_command_logs_revision_and_selects_fallback(tmp_path, history, job_id):
    """Missing context selects full CI without turning the mode job red."""
    config, _name = _wrapper(job_id)
    runner = _checkout(tmp_path, history, False, False, config)
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    command = workflow["jobs"]["mode"]["steps"][2]["run"]
    env = os.environ.copy()
    # Invalid context exercises the real CLI's failure without any API request.
    env["GITHUB_EVENT_PATH"] = str(tmp_path / "absent-event.json")
    env["GITHUB_OUTPUT"] = str(tmp_path / "output")
    result = subprocess.run(
        [
            "bash",
            "-e",
            "-c",
            f'python() {{ {shlex.quote(sys.executable)} "$@"; }}\n{command}',
        ],
        cwd=runner,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    revision, audit = result.stdout.splitlines()
    assert revision == f"Replay helper revision: {history[1]}"
    assert json.loads(audit) == {
        "replay": False,
        "evidence": {},
        "reason": "invalid replay context",
    }
    assert (tmp_path / "output").read_text().splitlines() == [
        "replay=false",
        "evidence={}",
    ]


def _checkout(tmp_path, history, has_helper, event_base_has_helper, config):
    """Resolve workflow inputs and sparse-check out their selected snapshot."""
    source, base, heads = history
    values = {
        "${{ github.event.pull_request.base.sha }}": (
            base if event_base_has_helper else heads[False]
        ),
        "${{ github.event.pull_request.base.ref }}": "refs/heads/main",
        "${{ github.event.pull_request.head.sha }}": heads[has_helper],
        "${{ github.event.pull_request.base.repo.full_name }}": "example/base",
        "${{ github.event.pull_request.head.repo.full_name }}": "example/fork",
    }
    assert config["persist-credentials"] is False
    assert config["sparse-checkout"] == HELPER
    assert config["sparse-checkout-cone-mode"] is False
    runner = tmp_path / "checkout"
    runner.mkdir()
    _git(runner, "init", "-q")
    _git(runner, "fetch", "--depth=1", source.as_uri(), values[config["ref"]])
    _git(runner, "sparse-checkout", "set", "--no-cone", config["sparse-checkout"])
    _git(runner, "checkout", "--detach", "FETCH_HEAD")
    return runner


def _evidence(base, head, name, condition):
    """Supply synthetic REST evidence while preserving the real decision engine."""
    run = {
        "id": 90,
        "run_attempt": 2,
        "head_sha": head if condition != "wrong_head" else "d" * 40,
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "pull_requests": [{"number": 7, "base": {"ref": "main", "repo": {"id": 1}}}],
    }
    artifact = {"name": f"gate-tip-{base}-attempt-2", "expired": condition == "expired"}
    job = {"id": 3, "name": name, "conclusion": "success"}

    def request(path):
        if "/branches/" in path:
            return {"commit": {"sha": "c" * 40 if condition == "stale" else base}}
        if "/workflows/ci.yml/runs?" in path:
            return {"workflow_runs": [] if condition == "missing_run" else [run]}
        if "/artifacts?" in path:
            return {"artifacts": [] if condition == "missing_marker" else [artifact]}
        if "/attempts/2/jobs?" in path:
            return {"jobs": [] if condition == "missing_job" else [job]}
        raise AssertionError(path)

    return request


@pytest.mark.parametrize("job_id", REQUIRED)
@pytest.mark.parametrize("has_helper", [False, True], ids=["old-head", "helper-head"])
@pytest.mark.parametrize(
    "event_base_has_helper", [False, True], ids=["old-event-base", "helper-event-base"]
)
@pytest.mark.parametrize(
    "condition",
    [
        "valid",
        "missing_run",
        "missing_marker",
        "missing_job",
        "expired",
        "stale",
        "wrong_head",
    ],
)
def test_metadata_replay_checkout(
    tmp_path,
    monkeypatch,
    capsys,
    history,
    job_id,
    has_helper,
    event_base_has_helper,
    condition,
):
    """Only exact, current evidence passes, regardless of the PR helper's presence."""
    config, name = _wrapper(job_id)
    runner = _checkout(tmp_path, history, has_helper, event_base_has_helper, config)
    _, base, heads = history
    assert _git(runner, "rev-parse", "HEAD") == base
    script = runner / HELPER
    assert script.read_bytes() == (ROOT / HELPER).read_bytes()
    # Distinct identities catch accidental checkout of a fork's base revision.
    assert (
        config["repository"] == "${{ github.event.pull_request.base.repo.full_name }}"
    )
    spec = importlib.util.spec_from_file_location("checked_out_replay", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    head = heads[has_helper]
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "action": "edited",
                "pull_request": {
                    "number": 7,
                    "head": {"sha": head},
                    "base": {
                        "ref": "main",
                        "sha": base if event_base_has_helper else heads[False],
                        "repo": {"id": 1},
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/base")
    monkeypatch.setenv("GITHUB_RUN_ID", "100")
    monkeypatch.setattr(sys, "argv", [str(script), name])
    monkeypatch.setattr(module, "request_json", _evidence(base, head, name, condition))
    result = module.main()
    audit = json.loads(capsys.readouterr().out)
    assert result == (0 if condition == "valid" else 1), audit
    assert audit["decision"] == ("PASS" if condition == "valid" else "FAIL")
    assert audit["head"] == head  # Evidence stays bound to the PR, not the helper SHA.
    if condition == "missing_marker":
        assert audit["reason"] == "full run without base-tip evidence"
    if condition == "valid":
        assert audit["run_id"] == 90
        assert audit["attempt"] == 2
        assert audit["job_id"] == 3
        assert audit["recorded_tip"] == audit["live_tip"] == base
