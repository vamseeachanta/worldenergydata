"""Keep regenerable coverage out of Git without hiding ordinary reports.

Expected paths come from the pytest addopts in pyproject.toml. The hygiene
criterion comes from issue 422, option A; no engineering constants are used.
"""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def git(root, *args, check=True, **kwargs):
    """Ignore caller Git bindings and user configuration in subprocesses."""
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
    return subprocess.run(
        ["git", "-C", str(root), *args],
        env=env,
        text=True,
        capture_output=True,
        check=check,
        **kwargs,
    )


@pytest.fixture
def ignore_repo(tmp_path):
    """Exercise the shipped rules in a disposable repository, without data files."""
    git(tmp_path, "init", "--quiet")
    (tmp_path / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
    return tmp_path


@pytest.mark.parametrize(
    "path",
    [
        "reports/coverage/htmlcov/index.html",
        "reports/coverage/htmlcov/nested/source.html",
        "reports/coverage/htmlcov/style.css",
        "reports/coverage/htmlcov/status.json",
        "reports/coverage/coverage.xml",
        "reports/coverage/coverage.json",
    ],
)
def test_generated_coverage_is_ignored(ignore_repo, path):
    assert git(ignore_repo, "check-ignore", "--no-index", path).stdout.strip() == path


@pytest.mark.parametrize(
    "path",
    [
        "reports/analysis.html",
        "reports/coverage-analysis/index.html",
        "reports/field-atlas/results/summary.json",
    ],
)
def test_ordinary_reports_remain_trackable(ignore_repo, path):
    result = git(ignore_repo, "check-ignore", "--no-index", path, check=False)
    # git-check-ignore(1), EXIT STATUS: 1 means none of the paths are ignored.
    assert result.returncode == 1, result.stderr
    assert result.stdout == ""


def test_no_coverage_output_is_tracked():
    # Ignore rules cannot remove files already in the index (issue 422, option A).
    assert git(ROOT, "ls-files", "-z", "--", "reports/coverage/").stdout == ""
