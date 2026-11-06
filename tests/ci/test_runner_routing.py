"""Keep Linux routing open to both architectures without changing fork routing."""

import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FORK_PREFIX = (
    "${{ github.event.pull_request.head.repo.fork && 'ubuntu-latest' || fromJSON('"
)
FORK_ROUTING = FORK_PREFIX + '["self-hosted","Linux"]\') }}'
WORKFLOWS = [
    ("ci.yml", 6),
    ("main-full-run.yml", 10),
    ("docs.yml", 1),
    ("brand-guard.yml", 1),
]
X64_ONLY = {
    "full-suite",
    "f821-inventory",
    "type-check",
    "dependency-audit",
    "performance-benchmark",
}


def _local_jobs(filename):
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
    )
    return {name: job for name, job in workflow["jobs"].items() if "uses" not in job}


def _required_labels(selector):
    if isinstance(selector, str):
        assert selector.startswith(FORK_PREFIX)
        assert selector.endswith("') }}")
        selector = json.loads(selector.removeprefix(FORK_PREFIX).removesuffix("') }}"))
    return {label.casefold() for label in selector}


@pytest.mark.parametrize("filename, job_count", WORKFLOWS)
def test_linux_runner_routing(filename, job_count):
    """Hand count: 6 + 10 + 1 + 1 = 18 local jobs; one CI job is reusable.

    Compatible jobs request Linux; frozen all-extras jobs retain x64.
    The unchanged fork predicate selects ubuntu-latest.
    Reusable workflows own their runner selection outside this repository.
    """
    jobs = _local_jobs(filename)
    assert len(jobs) == job_count
    for name, job in jobs.items():
        expected = FORK_ROUTING
        if filename == "main-full-run.yml":
            expected = ["self-hosted", "x64" if name in X64_ONLY else "Linux"]
        assert job["runs-on"] == expected, name


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
        assert _required_labels(jobs[name]["runs-on"]) == {"self-hosted", "x64"}, name


@pytest.mark.parametrize("filename, job_count", WORKFLOWS)
@pytest.mark.parametrize("architecture", ["X64", "ARM64"])
def test_linux_runner_label_matching(filename, job_count, architecture):
    """Both Linux architectures match compatible jobs; ARM64 cannot take CAD jobs."""
    runner_labels = {"self-hosted", "linux", architecture.casefold()}
    jobs = _local_jobs(filename)
    assert len(jobs) == job_count
    for name, job in jobs.items():
        x64_only = filename == "main-full-run.yml" and name in X64_ONLY
        matches = _required_labels(job["runs-on"]) <= runner_labels
        assert matches == (not x64_only or architecture == "X64"), name
