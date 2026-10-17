"""Run the production PR lint step against a stale-base merge topology."""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
PASS = Path(__file__).with_name("pack_lint_fixtures") / "pass.md"
WORKFLOW = ROOT / ".github/workflows/pr-validation.yml"


def run(repo, env, *args, check=True):
    return subprocess.run(
        args, cwd=repo, env=env, text=True, capture_output=True, check=check
    )


@pytest.fixture
def merge_repo(tmp_path):
    # An inherited Git binding must never redirect fixture mutations to a caller.
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.org",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.org",
        PACK_ACCOUNT="example-owner",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        TMPDIR=str(tmp_path),
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    run(repo, env, "git", "init", "-b", "main")
    run(repo, env, "git", "config", "core.hooksPath", "/dev/null")
    (repo / "scripts").mkdir()
    shutil.copy(ROOT / "scripts/pack_lint.py", repo / "scripts/pack_lint.py")
    (repo / "modified").mkdir()
    (repo / "modified/agent-pack.md").write_bytes(PASS.read_bytes())
    run(repo, env, "git", "add", ".")
    run(repo, env, "git", "commit", "-m", "initial base")
    env["BASE_SHA"] = run(repo, env, "git", "rev-parse", "HEAD").stdout.strip()
    run(repo, env, "git", "branch", "pr")
    (repo / "legacy").mkdir()
    (repo / "legacy/agent-pack.md").write_text("Legacy pack with findings\n")
    run(repo, env, "git", "add", ".")
    run(repo, env, "git", "commit", "-m", "main advances with legacy pack")
    legacy = run(
        repo,
        env,
        "python3",
        "scripts/pack_lint.py",
        "--account",
        "example-owner",
        "legacy/agent-pack.md",
        check=False,
    )
    assert legacy.returncode == 1 and "S10:" in legacy.stdout
    run(repo, env, "git", "checkout", "pr")
    return repo, env


def lint_merge(repo, env):
    run(repo, env, "git", "add", ".")
    run(repo, env, "git", "commit", "-m", "PR changes")
    run(repo, env, "git", "checkout", "main")
    run(repo, env, "git", "merge", "--no-ff", "pr", "-m", "PR merge ref")
    return lint_step(repo, env)


def lint_step(repo, env):
    # Execute the actual workflow shell, not a test copy of its selection logic.
    job = yaml.safe_load(WORKFLOW.read_text())["jobs"]["pack-lint"]
    assert "if" not in job and not job.get("continue-on-error", False)
    steps = job["steps"]
    matches = [step for step in steps if step.get("name") == "Lint changed agent packs"]
    assert len(matches) == 1
    step = matches[0]
    assert step["env"] == {"PACK_ACCOUNT": "${{ github.repository_owner }}"}
    assert "if" not in step and not step.get("continue-on-error", False)
    assert steps[0]["with"]["fetch-depth"] == 0
    shell = step["run"]
    shell = f'python() {{ {shlex.quote(sys.executable)} "$@"; }}\n' + shell
    return run(repo, env, "bash", "-c", shell, check=False)


@pytest.mark.parametrize("kind", ["added pack", "modified"])
@pytest.mark.parametrize("finding", [None, "SWEEP", "URL"])
def test_only_pr_packs_are_linted(merge_repo, kind, finding):
    repo, env = merge_repo
    pack = repo / kind / "agent-pack.md"
    pack.parent.mkdir(exist_ok=True)
    content = PASS.read_text() + "\nPR update\n"
    if finding == "SWEEP":
        assert "sweep: 2 found" in content
        content = content.replace("sweep: 2 found", "Missing sweep evidence")
    elif finding == "URL":
        content += "https://example.org/example-owner/notes\n"
    pack.write_text(content)
    result = lint_merge(repo, env)
    assert result.returncode == int(bool(finding)), result.stdout + result.stderr
    assert "legacy/agent-pack.md" not in result.stdout
    assert "in 1 file(s)" in result.stdout
    if finding:
        assert f": {finding}:" in result.stdout


@pytest.mark.parametrize("delete", [False, True])
def test_no_added_or_modified_packs(merge_repo, delete):
    repo, env = merge_repo
    if delete:
        (repo / "modified/agent-pack.md").unlink()
    else:
        (repo / "README.md").write_text("Documentation only\n")
    result = lint_merge(repo, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "No changed agent packs."


def test_non_merge_checkout_fails(merge_repo):
    repo, env = merge_repo
    result = lint_step(repo, env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert result.stdout == ""
    assert "Needed a single revision" in result.stderr


def test_exact_pack_filename(merge_repo):
    repo, env = merge_repo
    (repo / "agent-pack.md").write_bytes(PASS.read_bytes())
    (repo / "notagent-pack.md").write_text("Not a knowledge pack\n")
    (repo / "modified/my-agent-pack.md").write_text("Not a knowledge pack\n")
    result = lint_merge(repo, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "in 1 file(s)" in result.stdout
