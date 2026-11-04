"""Keep Linux routing open to both architectures without changing fork routing."""

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
FORK_ROUTING = (
    "${{ github.event.pull_request.head.repo.fork && 'ubuntu-latest' "
    "|| fromJSON('[\"self-hosted\",\"ARM64\"]') }}"
)


@pytest.mark.parametrize(
    "filename, job_count, expected",
    [
        ("ci.yml", 6, FORK_ROUTING),
        ("main-full-run.yml", 10, ["self-hosted", "ARM64"]),
        ("docs.yml", 1, FORK_ROUTING),
        ("brand-guard.yml", 1, FORK_ROUTING),
    ],
)
def test_linux_runner_routing(filename, job_count, expected):
    """Hand count: 6 + 10 + 1 + 1 = 18 local jobs; one CI job is reusable.

    Both {self-hosted, Linux, X64} and {self-hosted, Linux, ARM64} contain
    the two requested labels. The unchanged fork predicate selects ubuntu-latest.
    Reusable workflows own their runner selection outside this repository.
    """
    workflow = yaml.safe_load(
        (ROOT / ".github" / "workflows" / filename).read_text(encoding="utf-8")
    )
    jobs = [job for job in workflow["jobs"].values() if "uses" not in job]
    assert len(jobs) == job_count
    for job in jobs:
        assert job["runs-on"] == expected
