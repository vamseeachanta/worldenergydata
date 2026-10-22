"""Execute the sensitive-filename workflow against synthetic PR merge trees.

The filename policy comes from the sensitive-files patterns in the pre-change
PR Validation workflow. Expected results below are hand classifications: .env
(and its dotted variants), private-key extensions, exact SSH key basenames,
and paths containing secret or credential fail; other names pass. No file
contains credential material. Only the synthetic PR changes should be checked.
"""

import json
import os
import runpy
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github/workflows/pr-validation.yml"
SCRIPT = ROOT / "scripts/ci/check_sensitive_files.py"


def workflow_job():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["sensitive-files"]


def workflow_shell():
    return next(
        step["run"]
        for step in workflow_job()["steps"]
        if step.get("name") == "Check for sensitive files"
    )


def run(cwd, env, *args, check=True, input=None):
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input,
        text=True,
        capture_output=True,
        check=check,
    )


@pytest.fixture
def history(tmp_path):
    """Import fixture objects only; do not alter the caller's Git configuration.

    Git fast-import's documented raw dates, marks and inline file commands
    describe this hand-built graph: initial -> base, initial -> feature, then
    merge(base, feature). The base alone adds a legacy sensitive name.
    Source: https://git-scm.com/docs/git-fast-import (Input Format, 2026).
    """
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(TMPDIR=str(tmp_path), LC_ALL="C")
    origin = tmp_path / "origin.git"
    run(tmp_path, env, "git", "init", "--bare", str(origin))

    def checkout(changes, depth=2, branch="merged"):
        # Depth 2 includes the merge's parents; actions/checkout README,
        # "Checkout HEAD^" example (2026), uses this depth for parent access.
        def files(entries):
            commands = ""
            for name, content in entries.items():
                quoted = json.dumps(name)
                if content is None:
                    commands += f"D {quoted}\n"
                else:
                    commands += (
                        f"M 100644 inline {quoted}\n"
                        f"data {len(content.encode())}\n{content}\n"
                    )
            return commands

        def commit(ref, mark, parents, entries):
            return (
                f"commit refs/heads/{ref}\nmark :{mark}\n"
                "committer Fixture <fixture> 0 +0000\ndata 7\nfixture\n"
                + parents
                + files(entries)
                + "\n"
            )

        stream = commit(
            "initial",
            1,
            "",
            {"existing.key": "fixture", "plain.txt": "fixture"},
        )
        stream += commit("feature", 2, "from :1\n", changes)
        stream += commit("base", 3, "from :1\n", {"legacy-secret.txt": "fixture"})
        stream += commit("merged", 4, "from :3\nmerge :2\n", changes)
        run(origin, env, "git", "fast-import", "--quiet", input=stream + "done\n")
        repo = tmp_path / "checkout"
        run(
            tmp_path,
            env,
            "git",
            "clone",
            f"--depth={depth}",
            f"--branch={branch}",
            origin.as_uri(),
            str(repo),
        )
        assert (
            run(repo, env, "git", "rev-parse", "--is-shallow-repository").stdout.strip()
            == "true"
        )
        # Install the production entry point without adding it to the PR diff.
        if SCRIPT.exists():
            target = repo / SCRIPT.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SCRIPT, target)
        return repo, env

    return checkout


def check_step(repo, env):
    # Run the real shell with the same error propagation as Actions' bash shell.
    return run(
        repo,
        env,
        "bash",
        "--noprofile",
        "--norc",
        "-e",
        "-o",
        "pipefail",
        "-c",
        workflow_shell().replace("python3 ", shlex.quote(sys.executable) + " "),
        check=False,
    )


def test_sensitive_job_is_unconditional_and_fetches_parents():
    """Checkout's documented parent-access depth is 2; no skip is allowed."""
    job = workflow_job()
    assert job["name"] == "Check Sensitive Files"
    assert "if" not in job and not job.get("continue-on-error", False)
    checkout = next(s for s in job["steps"] if "checkout@" in s.get("uses", ""))
    assert checkout["with"]["fetch-depth"] == 2
    assert "ref" not in checkout["with"]
    for step in job["steps"]:
        assert "if" not in step and not step.get("continue-on-error", False)


@pytest.mark.parametrize(
    "filename",
    [
        ".env",
        "config/.env",
        "config/.env.local",
        "nested/test.pem",
        "nested/test.key",
        "nested/test.p12",
        "id_rsa",
        "nested/id_dsa",
        "docs/secret-notes.txt",
        "credential-store/config.txt",
        "space dir/test.key",
        "line\nbreak.pem",
    ],
)
def test_planted_sensitive_filename_fails(history, filename):
    """Each planted name belongs to an explicit policy category listed above."""
    repo, env = history({filename: "fixture"})
    result = check_step(repo, env)
    assert result.returncode != 0, result.stdout + result.stderr
    assert "::error::Potentially sensitive" in result.stdout
    assert "No potentially sensitive" not in result.stdout


@pytest.mark.parametrize(
    "filename",
    [
        "README.md",
        "docs/environment.md",
        "config/env",
        "docs/.env-example",
        "docs/test.pem.txt",
        "docs/id_rsa.pub",
        "docs/id_dsa.txt",
        "space dir/clean.txt",
        "line\nbreak.txt",
    ],
)
def test_clean_pr_passes_despite_legacy_base_names(history, filename):
    """These names have no policy token; unchanged base findings are excluded."""
    repo, env = history({filename: "fixture"})
    result = check_step(repo, env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No potentially sensitive filenames" in result.stdout


@pytest.mark.parametrize(
    "changes, expected_failure",
    [
        ({"existing.key": "modified fixture"}, True),
        ({"existing.key": None}, False),
        ({"plain.txt": None, "renamed.key": "fixture"}, True),
        ({"existing.key": None, "renamed.txt": "fixture"}, False),
        ({}, False),
    ],
)
def test_modified_deleted_renamed_and_empty_changes(history, changes, expected_failure):
    """Hand calculation: new/modified key names fail; removal and no change pass.

    The equal fixture contents make the paired deletion/addition pure renames.
    This also checks that a rename's destination, rather than its source, wins.
    """
    repo, env = history(changes)
    result = check_step(repo, env)
    assert bool(result.returncode) is expected_failure, result.stdout + result.stderr


@pytest.mark.parametrize("depth, branch", [(1, "merged"), (2, "feature")])
def test_unusable_merge_history_fails_loudly(history, depth, branch):
    """A depth-1 merge hides parents; the feature commit is not a merge."""
    repo, env = history({"README.md": "fixture"}, depth=depth, branch=branch)
    result = check_step(repo, env)
    assert result.returncode != 0
    assert (
        "::error::Expected the pull_request merge ref with both parents"
        in result.stdout
    )
    assert "No potentially sensitive" not in result.stdout


def test_diff_failure_is_not_a_clean_result(history, tmp_path):
    """Inject a failed git diff; no filename-policy evaluation can then pass."""
    repo, env = history({"README.md": "fixture"})
    tools = tmp_path / "tools"
    tools.mkdir()
    git = shutil.which("git")
    assert git
    wrapper = tools / "git"
    wrapper.write_text(
        '#!/bin/bash\nif [[ "$1" == diff ]]; then\n'
        '  echo "injected diff failure" >&2\n  exit 1\nfi\n'
        f'exec {shlex.quote(git)} "$@"\n'
    )
    wrapper.chmod(0o755)
    result = check_step(repo, {**env, "PATH": str(tools) + os.pathsep + env["PATH"]})
    assert result.returncode != 0
    assert "injected diff failure" in result.stderr
    assert "::error::Unable to compute PR filename diff" in result.stdout
    assert "No potentially sensitive" not in result.stdout


def test_workflow_calls_offline_script():
    """The script exercised offline must be the workflow's sole policy check."""
    assert workflow_shell().strip() == "python3 scripts/ci/check_sensitive_files.py"


@pytest.mark.parametrize(
    "pattern,positive,negative",
    [
        (
            "environment",
            [".env", "x/.env.local"],
            ["x.env", "x/.env-example", ".env\n", ".ENV"],
        ),
        (
            "private-key",
            ["x.pem", "a/x.key", "x.p12"],
            ["x.pem.txt", "monkey", "x.key\n", "x.PEM"],
        ),
        ("secret-token", ["secret.txt", "a/credential/file"], ["secure.txt", "credit"]),
        (
            "ssh-key",
            ["id_rsa", "a/id_dsa"],
            ["id_rsa.pub", "my_id_dsa", "id_rsa\n", "ID_RSA"],
        ),
    ],
)
def test_each_regex_has_positive_and_negative_boundaries(pattern, positive, negative):
    """Hand classifications from the pre-extraction workflow's filename policy.

    Environment basenames end or continue with a dot; key extensions end the
    path; secret/credential are substrings; SSH key basenames match exactly.
    Case sensitivity is retained. These are policy examples, not file contents.
    """
    patterns = runpy.run_path(str(SCRIPT))["SENSITIVE_PATTERNS"]
    regex = patterns[pattern]
    assert all(regex.search(name) for name in positive)
    assert all(regex.search(name) is None for name in negative)


def test_filename_cannot_inject_annotations(history):
    """One filename produces one annotation; newline and percent escapes are data.

    Expected escaping comes from Actions toolkit command.ts escapeData and
    Python JSON string escaping. The percent escape must itself be escaped so
    Actions cannot decode a filename into another command or line.
    """
    repo, env = history({"escape%0A::error::injected\nname.key": "fixture"})
    result = check_step(repo, env)
    assert result.returncode != 0
    assert len(result.stdout.splitlines()) == 1
    assert "%250A" in result.stdout
    assert "\\nname.key" in result.stdout
