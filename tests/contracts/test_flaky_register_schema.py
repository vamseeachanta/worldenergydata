"""Validate the informational flaky-test register without changing test selection."""

from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

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
        evidence = entry["evidence"]
        assert isinstance(evidence, list) and evidence, "evidence"
        for url in evidence:
            assert isinstance(url, str), "evidence URL"
            parsed = urlparse(url)
            parts = parsed.path.strip("/").split("/")
            is_github = parsed.scheme == "https" and parsed.netloc == "github.com"
            assert is_github, "evidence URL"
            assert len(parts) in {5, 7}, "evidence URL"
            assert all(parts[:2]) and parts[2:4] == ["actions", "runs"], "evidence URL"
            assert parts[4].isdigit(), "evidence URL"
            if len(parts) == 7:
                assert parts[5] == "job" and parts[6].isdigit(), "evidence URL"


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
