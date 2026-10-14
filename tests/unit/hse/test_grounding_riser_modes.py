"""Fixture and live-corpus checks for riser and pressure grounding candidates."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import runpy
from pathlib import Path

import pytest

from worldenergydata.hse.grounding import (
    FAILURE_MODES,
    corpus_vintage,
    default_bsee_path,
    ground,
    load_bsee,
)

FIXTURE = Path(__file__).parent / "fixtures" / "bsee_riser_pressure_sample.txt"
CORPUS_SHA256 = "a174d467b39f74f3ceeab4c4d3e0dd01c903de253b21feec03359e818b9dd2fd"
EXPECTED = {"riser_viv_fatigue": 7, "structural_overpressure": 45}


@pytest.mark.parametrize(
    "mode,dates",
    [
        ("riser_viv_fatigue", {"2006-03-20", "2005-03-15", "2005-03-11"}),
        ("structural_overpressure", {"2007-02-28", "2017-11-03", "2011-09-17"}),
    ],
)
def test_corpus_fixture_positive_records(mode, dates):
    matches = load_bsee(FAILURE_MODES[mode], FIXTURE)
    assert len(matches) == EXPECTED[mode]
    assert dates <= {record.date for record in matches}
    assert "cause unconfirmed" in ground(mode, bsee_path=FIXTURE).failure_mode


@pytest.mark.parametrize(
    "mode,near_misses",
    [
        (
            "riser_viv_fatigue",
            {"2004-04-11", "2007-12-02", "2017-10-16", "2016-01-30"},
        ),
        (
            "structural_overpressure",
            {"2008-04-08", "2014-10-27", "2011-03-31", "2017-10-16"},
        ),
    ],
)
def test_corpus_fixture_near_misses(mode, near_misses):
    with FIXTURE.open() as source:
        fixture_dates = {
            dt.datetime.strptime(row["DATE_OCCURRED"], "%m/%d/%Y").date().isoformat()
            for row in csv.DictReader(source)
        }
    assert near_misses <= fixture_dates
    matches = load_bsee(FAILURE_MODES[mode], FIXTURE)
    assert near_misses.isdisjoint(record.date for record in matches)


@pytest.mark.parametrize("mode", EXPECTED)
def test_candidate_modes_route_bsee_only(mode):
    result = ground(mode, bsee_path=FIXTURE)
    assert result.source_counts["BSEE"] > 0
    assert "not routed" in result.source_counts["OSHA"]
    assert "not routed" in result.source_counts["EPA_TRI"]
    # The public representation contains no additional raw-corpus columns.
    assert set(result.latest[0].public()) == {
        "source",
        "date",
        "location",
        "description",
        "severity",
        "severity_rank",
        "vintage_note",
    }


@pytest.mark.parametrize("mode,count", EXPECTED.items())
def test_live_corpus_candidate_counts(mode, count):
    """2026-10-14: 1,987 records, vintage 2026-01-08; riser 7, pressure 45.

    These are candidate counts, with no confirmed VIV/fatigue or overpressure
    cause inferred from accident types. The SHA pins the observed source bytes.
    """
    path = default_bsee_path()
    if path is None:
        pytest.skip("Live BSEE incident corpus is not present")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == CORPUS_SHA256
    with path.open(encoding="latin-1") as source:
        assert len(list(csv.DictReader(source))) == 1987
    assert corpus_vintage(path) == "2026-01-08"
    matches = load_bsee(FAILURE_MODES[mode], path)
    assert len(matches) == count
    assert len(matches) / 1987 <= 0.30


def test_identifier_note_is_repeatable_and_revision_matches():
    root = Path(__file__).resolve().parents[3]
    builder = runpy.run_path(str(root / "scripts/build_hse_grounding_matches.py"))
    revisions = root / "docs/hse/grounding-riser-revisions.json"
    first = builder["build_note"](FIXTURE, revisions)
    assert first == builder["build_note"](FIXTURE, revisions)
    history = json.loads(revisions.read_text())
    newest = history["history"][-1]
    assert newest["revision"] == history["revision"]
    assert f"Revision {history['revision']}." in first
    assert f"| {newest['revision']} | {newest['date']} | {newest['change']} |" in first
    headings = [line for line in first.splitlines() if line.startswith("## ")]
    assert headings[:2] == ["## Summary", "## Revision history"]
    assert "2006-03-20|8:22|G17003|WR 544" in first
    assert "2007-02-28|20:14|G15610|GC 782" in first


def test_fixture_records_are_source_exact():
    path = default_bsee_path()
    if path is None:
        pytest.skip("Live BSEE incident corpus is not present")
    with path.open(encoding="latin-1") as source:
        rows = list(csv.DictReader(source))
    with FIXTURE.open() as source:
        fixture = list(csv.DictReader(source))
    assert all(row in rows for row in fixture)


def test_identifier_note_rejects_revision_mismatch(tmp_path):
    root = Path(__file__).resolve().parents[3]
    builder = runpy.run_path(str(root / "scripts/build_hse_grounding_matches.py"))
    data = json.loads((root / "docs/hse/grounding-riser-revisions.json").read_text())
    data["revision"] += 1
    revisions = tmp_path / "revisions.json"
    revisions.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Newest revision record"):
        builder["build_note"](FIXTURE, revisions)


def test_identifier_note_accepts_the_classifiers_iso_dates(tmp_path):
    root = Path(__file__).resolve().parents[3]
    builder = runpy.run_path(str(root / "scripts/build_hse_grounding_matches.py"))
    with FIXTURE.open() as source:
        reader = csv.DictReader(source)
        fields, rows = reader.fieldnames, list(reader)
    for row in rows:
        row["DATE_OCCURRED"] = (
            dt.datetime.strptime(row["DATE_OCCURRED"], "%m/%d/%Y").date().isoformat()
        )
    corpus = tmp_path / "iso_dates.txt"
    with corpus.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    revisions = root / "docs/hse/grounding-riser-revisions.json"
    note = builder["build_note"](corpus, revisions)
    assert "2006-03-20|8:22|G17003|WR 544" in note
    assert "7 candidates" in note and "45 candidates" in note
