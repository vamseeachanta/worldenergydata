"""Readiness cases specified by issue 451; all records are synthetic.

Freshness hand calculation: Oct 19 - Oct 17 = 2 days. A caller-selected
3-day maximum therefore passes; Oct 19 - Oct 15 = 4 days therefore fails.
These are test inputs, not regulatory limits or production defaults.
"""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from worldenergydata.common.catalog import DatasetEntry
from worldenergydata.common.source_readiness import probe_source

AS_OF = datetime(2026, 10, 19, tzinfo=timezone.utc)
CSV = "API_WELL_NUMBER,LEASE_NUMBER,OIL\nsynthetic-well,synthetic-lease,1\n"


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "production.csv"
    path.write_text(CSV, encoding="utf-8")
    return DatasetEntry(
        "production", path.name, "csv", "production", path.stat().st_size
    )


def probe(entry, tmp_path, **overrides):
    options = {
        "source": "bsee",
        "as_of": AS_OF,
        "data_as_of": AS_OF - timedelta(days=2),
        "max_age": timedelta(days=3),
        "required_columns": ("API_WELL_NUMBER", "OIL"),
        "entity_columns": {"well": ("API_WELL_NUMBER",), "lease": ("LEASE_NUMBER",)},
        "sampled": False,
        "local_only": False,
    }
    options.update(overrides)
    return probe_source(entry, tmp_path, **options)


def test_available_data_and_serializable_evidence(source, tmp_path):
    result = probe(source, tmp_path)
    assert result["usable"] is True
    assert result["availability"] == "available"
    assert result["freshness"] == "current"
    assert result["entities"] == {
        "well": ["API_WELL_NUMBER"],
        "lease": ["LEASE_NUMBER"],
    }
    assert result["row_count"] == 1
    assert result["data_as_of"] == "2026-10-17T00:00:00+00:00"
    assert json.loads(json.dumps(result)) == result
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize(
    "content,availability",
    [
        (None, "missing"),
        ("", "empty"),
        ("API_WELL_NUMBER,OIL\n", "empty"),
        ("API_WELL_NUMBER,OIL\n,\n", "empty"),
        # Git LFS pointer specification v1: version line identifies pointer content.
        # https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md
        (
            "version https://git-lfs.github.com/spec/v1\noid sha256:example\nsize 1\n",
            "lfs_stub",
        ),
        ('API_WELL_NUMBER,OIL\n"unterminated', "invalid"),
        ("API_WELL_NUMBER,OIL\nx,1,extra\n", "invalid"),
        ("API_WELL_NUMBER,API_WELL_NUMBER\nx,x\n", "invalid"),
    ],
)
def test_missing_empty_stub_and_invalid(source, tmp_path, content, availability):
    target = tmp_path / source.path
    if content is None:
        source = replace(source, path="absent.csv")
    else:
        target.write_text(content, encoding="utf-8")
    result = probe(source, tmp_path)
    assert result["availability"] == availability
    assert result["usable"] is False


@pytest.mark.parametrize(
    "age,freshness,usable",
    [
        (timedelta(days=3), "current", True),  # equality satisfies age <= max_age
        (timedelta(days=4), "stale", False),
        (timedelta(days=-1), "future", False),
        (None, "not_evaluated", False),
    ],
)
def test_freshness_uses_source_vintage(source, tmp_path, age, freshness, usable):
    result = probe(source, tmp_path, data_as_of=None if age is None else AS_OF - age)
    assert result["freshness"] == freshness
    assert result["usable"] is usable


@pytest.mark.parametrize(
    "options,reason",
    [
        ({"sampled": True}, "sampled"),
        ({"local_only": True}, "external_root_requires_opt_in"),
        (
            {
                "blocked_by": (
                    "https://github.com/vamseeachanta/worldenergydata/issues/365",
                )
            },
            "pending_ingest",
        ),
        ({"required_columns": ("absent",)}, "missing_columns"),
    ],
)
def test_independent_blockers(source, tmp_path, options, reason):
    result = probe(source, tmp_path, **options)
    assert result["availability"] == "available"
    assert reason in result["reasons"]
    assert result["usable"] is False


def test_local_only_requires_explicit_permission(source, tmp_path):
    result = probe(source, tmp_path, source="fdas", local_only=True, allow_local=True)
    assert result["usable"] is True
    assert result["local_only"] is True
    assert result["source"] == "fdas"
    assert result["publication_eligibility"] == "not_evaluated"


def test_entities_require_observed_values(source, tmp_path):
    (tmp_path / source.path).write_text("API_WELL_NUMBER,LEASE_NUMBER,OIL\nx,,1\n")
    result = probe(source, tmp_path)
    assert result["entities"] == {"well": ["API_WELL_NUMBER"]}


def test_catalog_cannot_override_observed_data(source, tmp_path):
    source = replace(source, columns=["absent"], row_count=99, data_status="real")
    result = probe(source, tmp_path, required_columns=("absent",))
    assert result["usable"] is False
    assert result["row_count"] == 1


@pytest.mark.parametrize(
    "options",
    [
        {"max_age": timedelta(days=-1)},
        {"as_of": AS_OF.replace(tzinfo=None)},
        {"data_as_of": AS_OF.replace(tzinfo=None)},
        {"source": "unknown"},
        {"required_columns": ()},
        {"entity_columns": {"unknown": ("OIL",)}},
    ],
)
def test_invalid_policy_is_rejected(source, tmp_path, options):
    with pytest.raises(ValueError):
        probe(source, tmp_path, **options)


@pytest.mark.parametrize("path", ["../outside.csv", "/outside.csv"])
def test_paths_stay_within_explicit_data_root(source, tmp_path, path):
    with pytest.raises(ValueError, match="root"):
        probe(replace(source, path=path), tmp_path)


def test_unsupported_binary_is_not_loaded(source, tmp_path):
    source = replace(source, path="production.bin", format="pickle")
    (tmp_path / source.path).write_bytes(b"not a CSV")
    assert probe(source, tmp_path)["availability"] == "unsupported"


def test_probe_preserves_file_bytes_and_mtime(source, tmp_path):
    path = tmp_path / source.path
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    probe(source, tmp_path)
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == [source.path]


@pytest.mark.parametrize(
    "options",
    [
        {"sampled": "false"},
        {"local_only": None},
        {"allow_local": "true"},
        {"entity_columns": {"well": "API_WELL_NUMBER"}},
        {"entity_columns": {"well": ()}},
    ],
)
def test_ambiguous_policy_cannot_enable_eligibility(source, tmp_path, options):
    with pytest.raises(ValueError):
        probe(source, tmp_path, **options)


def test_required_column_with_only_blank_values_is_blocked(source, tmp_path):
    (tmp_path / source.path).write_text("API_WELL_NUMBER,OIL\n,1\n")
    result = probe(source, tmp_path)
    assert result["usable"] is False
    assert "unpopulated_columns" in result["reasons"]


def test_symlink_cannot_escape_root(source, tmp_path):
    root = tmp_path / "selected-root"
    root.mkdir()
    (root / source.path).symlink_to(tmp_path / source.path)
    with pytest.raises(ValueError, match="root"):
        probe(source, root)


def test_directory_is_unreadable_data(source, tmp_path):
    source = replace(source, path="directory.csv")
    (tmp_path / source.path).mkdir()
    assert probe(source, tmp_path)["availability"] == "unreadable"


def test_non_utf8_input_is_invalid(source, tmp_path):
    (tmp_path / source.path).write_bytes(b"\xff\xfe")
    assert probe(source, tmp_path)["availability"] == "invalid"
