"""Keep Linux routing open to both architectures; fork PRs stay on hosted runners."""

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FORK_PREFIX = (
    "${{ (github.event_name != 'pull_request' || "
    "github.event.pull_request.head.repo.full_name == github.repository) && fromJSON('"
)
FORK_SUFFIX = "') || 'ubuntu-latest' }}"
FORK_ROUTING = FORK_PREFIX + '["self-hosted","Linux"]' + FORK_SUFFIX
WORKFLOWS = [
    ("ci.yml", 6),
    ("main-full-run.yml", 10),
    ("docs.yml", 1),
    ("brand-guard.yml", 1),
    ("wheel-ownership.yml", 1),
    ("pr-validation.yml", 4),
    ("domain-matrix.yml", 3),
]
X64_ONLY = {
    "full-suite",
    "f821-inventory",
    "type-check",
    "dependency-audit",
    "performance-benchmark",
}
DOMAIN_X64_ONLY = {"test-domain", "aggregate"}
LIGHTWEIGHT_PR_JOBS = [
    ("pr-validation.yml", "pr-title"),
    ("pr-validation.yml", "file-size"),
    ("pr-validation.yml", "sensitive-files"),
    ("pr-validation.yml", "pack-lint"),
    ("domain-matrix.yml", "discover"),
]


def _local_jobs(filename):
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
    )
    return {name: job for name, job in workflow["jobs"].items() if "uses" not in job}


def _required_labels(selector):
    if isinstance(selector, str):
        selector = " ".join(selector.split())
        assert selector.startswith(FORK_PREFIX)
        assert selector.endswith(FORK_SUFFIX)
        selector = json.loads(
            selector.removeprefix(FORK_PREFIX).removesuffix(FORK_SUFFIX)
        )
    return {label.casefold() for label in selector}


@pytest.mark.parametrize("filename, job_count", WORKFLOWS)
def test_linux_runner_routing(filename, job_count):
    """Hand count: 6 + 10 + 1 + 1 + 1 + 4 + 3 = 26 local jobs.

    Compatible jobs request Linux; frozen all-extras jobs retain Linux x64.
    The same-repository predicate sends fork PRs to ubuntu-latest.
    The local reusable domain workflow owns three of these selectors.
    """
    jobs = _local_jobs(filename)
    assert len(jobs) == job_count
    for name, job in jobs.items():
        if filename == "main-full-run.yml":
            expected = (
                ["self-hosted", "x64", "Linux"]
                if name in X64_ONLY
                else ["self-hosted", "Linux"]
            )
            assert job["runs-on"] == expected, name
        elif filename == "domain-matrix.yml" and name in DOMAIN_X64_ONLY:
            assert " ".join(job["runs-on"].split()) == (
                FORK_PREFIX + '["self-hosted","x64","linux"]' + FORK_SUFFIX
            ), name
        else:
            assert " ".join(job["runs-on"].split()) == FORK_ROUTING, name


@pytest.mark.parametrize("filename, job_id", LIGHTWEIGHT_PR_JOBS)
def test_lightweight_pr_jobs_allow_both_architectures(filename, job_id):
    """Pin each moved job and preserve the exact fork-isolation expression."""
    selector = _local_jobs(filename)[job_id]["runs-on"]
    assert " ".join(selector.split()) == FORK_ROUTING


@pytest.mark.parametrize("job_id", sorted(DOMAIN_X64_ONLY))
def test_domain_tests_and_summary_stay_x64(job_id):
    """CAD-dependent tests and their summary retain the existing x64 policy."""
    selector = _local_jobs("domain-matrix.yml")[job_id]["runs-on"]
    assert " ".join(selector.split()) == (
        FORK_PREFIX + '["self-hosted","x64","linux"]' + FORK_SUFFIX
    )


def test_frozen_all_extras_jobs_stay_x64():
    """Frozen CAD dependencies cannot install on Linux ARM64 with this lockfile."""
    jobs = _local_jobs("main-full-run.yml")
    frozen_jobs = {
        name
        for name, job in jobs.items()
        if any(
            "uv sync --frozen --all-extras" in step.get("run", "")
            for step in job["steps"]
        )
    }
    assert frozen_jobs == X64_ONLY
    for name in frozen_jobs:
        assert _required_labels(jobs[name]["runs-on"]) == {
            "self-hosted",
            "x64",
            "linux",
        }, name


@pytest.mark.parametrize("filename, job_count", WORKFLOWS)
@pytest.mark.parametrize("architecture", ["X64", "ARM64"])
def test_linux_runner_label_matching(filename, job_count, architecture):
    """Both Linux architectures match compatible jobs; ARM64 cannot take CAD jobs."""
    runner_labels = {"self-hosted", "linux", architecture.casefold()}
    jobs = _local_jobs(filename)
    assert len(jobs) == job_count
    for name, job in jobs.items():
        x64_only = (filename == "main-full-run.yml" and name in X64_ONLY) or (
            filename == "domain-matrix.yml" and name in DOMAIN_X64_ONLY
        )
        matches = _required_labels(job["runs-on"]) <= runner_labels
        assert matches == (not x64_only or architecture == "X64"), name
