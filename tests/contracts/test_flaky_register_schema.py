"""Validate the informational flaky-test register without changing test selection."""

import re
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest
import yaml

REGISTER = Path(__file__).resolve().parents[2] / ".github/ci/flaky-register.yml"
KEYS = {
    "id",
    "kind",
    "first_seen",
    "last_seen",
    "evidence",
    "cause",
    "fix_issue",
    "status",
    "seen_on",
    "main_run",
    "main_job",
    "unrelated_because",
}


def validate_register(entries: object) -> None:
    """Require complete, uniquely identified entries with dated run evidence."""
    assert isinstance(entries, list), "register must be a list"
    seen = set()
    for entry in entries:
        assert isinstance(entry, dict) and set(entry) == KEYS, "entry keys"
        for key in ("id", "cause"):
            assert isinstance(entry[key], str) and entry[key].strip(), key
        assert entry["id"] not in seen, "duplicate id"
        seen.add(entry["id"])
        assert entry["kind"] in {
            "retry-pass",
            "same-tree-mismatch",
            "signal-exit",
        }, "kind"
        assert entry["status"] in {"open", "fixed"}, "status"
        for key in ("first_seen", "last_seen"):
            assert isinstance(entry[key], str), key
            assert date.fromisoformat(entry[key]).isoformat() == entry[key], key
        assert entry["first_seen"] <= entry["last_seen"], "date order"
        fix_issue = entry["fix_issue"]
        is_pr_number = type(fix_issue) is int and fix_issue > 0
        assert fix_issue == "pending" or is_pr_number, "fix_issue"
        assert entry["status"] != "fixed" or is_pr_number, "fixed reference"
        evidence = entry["evidence"]
        assert isinstance(evidence, list) and evidence, "evidence"
        job_urls = set()
        for url in evidence:
            assert isinstance(url, str), "evidence URL"
            match = re.fullmatch(
                r"https://github\.com/vamseeachanta/worldenergydata/"
                r"actions/runs/[0-9]+(?:/job/[0-9]+)?",
                url,
            )
            assert match, "evidence URL"
            if "/job/" in url:
                job_urls.add(url)
        assert job_urls, "job evidence required"
        validate_observation(entry, job_urls)


def validate_observation(entry: dict, job_urls: set[str]) -> None:
    """Require main failure identifiers or a documented unrelated PR failure."""
    assert entry["seen_on"] in {"main", "pull_request"}, "seen_on"
    if entry["seen_on"] == "main":
        for key in ("main_run", "main_job"):
            assert type(entry[key]) is int and entry[key] > 0, key
        expected = (
            "https://github.com/vamseeachanta/worldenergydata/actions/runs/"
            f"{entry['main_run']}/job/{entry['main_job']}"
        )
        assert expected in job_urls, "main job evidence"
        assert entry["unrelated_because"] is None, "unrelated_because"
    else:
        assert entry["main_run"] is None, "main_run"
        assert entry["main_job"] is None, "main_job"
        reason = entry["unrelated_because"]
        assert isinstance(reason, str) and re.search(
            r"[A-Za-z]", reason
        ), "unrelated_because"


def test_flaky_register_schema() -> None:
    """Validate every committed entry against the register contract."""
    validate_register(yaml.safe_load(REGISTER.read_text(encoding="utf-8")))


@pytest.fixture
def valid_entry() -> dict:
    """Return an independent copy of a committed entry for negative probes."""
    return deepcopy(yaml.safe_load(REGISTER.read_text(encoding="utf-8"))[0])


def test_duplicate_ids_are_rejected(valid_entry: dict) -> None:
    """Two records for the same test must fail the contract."""
    with pytest.raises(AssertionError, match="duplicate id"):
        validate_register([valid_entry, deepcopy(valid_entry)])


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("evidence", []),
        ("evidence", "not a list"),
        ("evidence", ["https://github.com/actions/runs/1"]),
        ("evidence", [123]),
        ("kind", "unknown"),
        ("status", "unknown"),
        ("id", ""),
        ("cause", ""),
        ("first_seen", "invalid"),
        ("last_seen", "2000-01-01"),
        ("fix_issue", True),
        ("fix_issue", 0),
    ],
)
def test_invalid_fields_are_rejected(
    valid_entry: dict, key: str, value: object
) -> None:
    """Invalid field values must fail rather than silently enter the register."""
    valid_entry[key] = value
    with pytest.raises((AssertionError, ValueError)):
        validate_register([valid_entry])


def test_missing_keys_are_rejected(valid_entry: dict) -> None:
    """Every schema field is required."""
    for key in KEYS:
        incomplete = {name: value for name, value in valid_entry.items() if name != key}
        with pytest.raises(AssertionError, match="entry keys"):
            validate_register([incomplete])


@pytest.mark.parametrize("entries", [None, {}, "invalid", [None]])
def test_invalid_register_shapes_are_rejected(entries: object) -> None:
    """The top level must be a list of mappings."""
    with pytest.raises(AssertionError):
        validate_register(entries)


@pytest.mark.parametrize(
    "change",
    [
        {
            "evidence": [
                "https://github.com/vamseeachanta/worldenergydata/actions/runs/38726236486"
            ]
        },
        {"evidence": ["https://github.com/other/repository/actions/runs/1/job/2"]},
        {
            "evidence": [
                "https://github.com/vamseeachanta/worldenergydata/actions/runs/38726236486/job/116392677940",
                "https://github.com/other/repository/actions/runs/1",
            ]
        },
        {"status": "fixed", "fix_issue": "pending"},
    ],
)
def test_insufficient_evidence_is_rejected(valid_entry: dict, change: dict) -> None:
    """Run context, foreign evidence and unreferenced fixes cannot suffice."""
    valid_entry.update(change)
    with pytest.raises(AssertionError):
        validate_register([valid_entry])


@pytest.mark.parametrize(
    "change",
    [
        {"seen_on": "unknown"},
        {"main_run": None},
        {"main_job": None},
        {"main_run": True},
        {"main_job": 0},
        {"main_job": 1},
        {"main_run": 1},
        {"unrelated_because": "Not applicable"},
        {"seen_on": "pull_request", "main_run": None, "main_job": None},
        {
            "seen_on": "pull_request",
            "main_run": None,
            "main_job": None,
            "unrelated_because": "   ",
        },
        {"seen_on": "pull_request", "unrelated_because": "Independent failure"},
        {
            "evidence": [
                "https://github.com/vamseeachanta/worldenergydata/actions/runs/1/job/2?extra=1"
            ]
        },
    ],
)
def test_invalid_observation_basis_is_rejected(valid_entry: dict, change: dict) -> None:
    """Observation location requires matching ids or an unrelated-failure reason."""
    valid_entry.update(change)
    with pytest.raises(AssertionError):
        validate_register([valid_entry])


def test_pull_request_basis_is_valid(valid_entry: dict) -> None:
    """A documented unrelated failure uses explicit nulls for main identifiers."""
    valid_entry.update(
        seen_on="pull_request",
        main_run=None,
        main_job=None,
        unrelated_because="The failing component is unchanged by the pull request.",
    )
    validate_register([valid_entry])


def test_register_has_no_test_selection_consumers() -> None:
    """Workflows, CI scripts and conftests cannot consume the register."""
    root = REGISTER.parents[2]
    candidates = set(root.glob(".github/workflows/**/*"))
    candidates.update(root.glob("scripts/ci/**/*"))
    candidates.update(root.rglob("conftest.py"))
    consumers = [
        str(path.relative_to(root))
        for path in sorted(candidates)
        if path.is_file() and b"flaky-register" in path.read_bytes()
    ]
    assert not consumers, f"register consumers: {consumers}"


def test_fixed_entry_with_run_context_is_valid(valid_entry: dict) -> None:
    """A fixed entry may retain additional run context beside its job evidence."""
    valid_entry.update(status="fixed", fix_issue=1243)
    valid_entry["evidence"].append(
        "https://github.com/vamseeachanta/worldenergydata/actions/runs/38726236486"
    )
    validate_register([valid_entry])
