"""Offline tests for the reference-series refresh: ownership, validation, freshness."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from worldenergydata.cost.timeseries.dataset import (
    read_timeseries_csv,
    write_timeseries_csv,
)
from worldenergydata.cost.timeseries.reference_series import (
    FRED_PAGE,
    REFERENCE_SERIES,
)
from worldenergydata.cost.timeseries.refresh import (
    MANIFEST_NAME,
    RefreshError,
    check_freshness,
    main,
    refresh,
)

CURATED = Path("data/modules/cost/curated/cost_component_timeseries.csv")
ACCESSED = date(2026, 11, 12)


def _monthly(first_year: int, last: date, level: float = 100.0):
    out = []
    year, month = first_year, 1
    while date(year, month, 1) <= last:
        out.append((date(year, month, 1), level + (year - first_year) + month / 100))
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return out


def _fetch(last: date = date(2026, 9, 1), level: float = 100.0):
    return lambda series_id: _monthly(1998, last, level)


def _owned(rows):
    urls = {FRED_PAGE.format(series_id=spec.series_id) for spec in REFERENCE_SERIES}
    return [row for row in rows if row.source_url in urls]


@pytest.fixture()
def held(tmp_path: Path) -> Path:
    """The held research rows only, so synthetic series have nothing to contradict."""
    path = tmp_path / "cost_component_timeseries.csv"
    rows = read_timeseries_csv(CURATED)
    write_timeseries_csv([row for row in rows if row not in _owned(rows)], path)
    return path


def test_refresh_replaces_only_owned_rows(held: Path) -> None:
    research_before = read_timeseries_csv(held)
    assert research_before and not _owned(research_before)
    result = refresh(held, ACCESSED, fetch=_fetch())
    after = read_timeseries_csv(held)
    research_after = [row for row in after if row not in _owned(after)]
    assert sorted(map(repr, research_after)) == sorted(map(repr, research_before))
    owned = _owned(after)
    assert len(owned) == result.reference_rows == 29 * len(REFERENCE_SERIES)
    assert {row.accessed_date for row in owned} == {ACCESSED}
    assert result.rows_written == len(after)


def test_refresh_is_idempotent_and_writes_manifest(held: Path) -> None:
    refresh(held, ACCESSED, fetch=_fetch())
    first = held.read_bytes()
    manifest_path = held.with_name(MANIFEST_NAME)
    manifest = manifest_path.read_text(encoding="utf-8")
    result = refresh(held, ACCESSED, fetch=_fetch())
    assert held.read_bytes() == first
    assert manifest_path.read_text(encoding="utf-8") == manifest
    assert result.revisions == ()
    entries = json.loads(manifest)["series"]
    assert [entry["series_id"] for entry in entries] == [
        spec.series_id for spec in REFERENCE_SERIES
    ]
    assert {entry["last_observation"] for entry in entries} == {"2026-09-01"}
    assert {entry["annual_rows"] for entry in entries} == {29}


def test_small_revision_is_reported_not_blocked(held: Path) -> None:
    refresh(held, ACCESSED, fetch=_fetch())
    result = refresh(held, ACCESSED, fetch=_fetch(level=100.5))
    assert any("2005" in line for line in result.revisions)


def test_large_complete_year_move_blocks_and_leaves_file(held: Path) -> None:
    refresh(held, ACCESSED, fetch=_fetch())
    snapshot = held.read_bytes()
    with pytest.raises(RefreshError, match="complete-year value moved"):
        refresh(held, ACCESSED, fetch=_fetch(level=200.0))
    assert held.read_bytes() == snapshot


def test_stale_source_blocks(held: Path) -> None:
    snapshot = held.read_bytes()
    with pytest.raises(RefreshError, match="newest observation"):
        refresh(held, ACCESSED, fetch=_fetch(last=date(2026, 5, 1)))
    assert held.read_bytes() == snapshot
    assert not held.with_name(MANIFEST_NAME).exists()


def test_lost_years_and_bad_values_block(held: Path) -> None:
    refresh(held, ACCESSED, fetch=_fetch())
    short = lambda series_id: _monthly(2001, date(2026, 9, 1), 103.0)
    with pytest.raises(RefreshError, match="held years missing"):
        refresh(held, ACCESSED, fetch=short)
    negative = lambda series_id: [
        (day, -value) for day, value in _monthly(1998, date(2026, 9, 1))
    ]
    with pytest.raises(RefreshError, match="non-positive"):
        refresh(held, ACCESSED, fetch=negative)


def test_check_freshness(held: Path) -> None:
    assert check_freshness(held, ACCESSED)[0].startswith("manifest not found")
    refresh(held, ACCESSED, fetch=_fetch())
    assert check_freshness(held, date(2026, 12, 1)) == []
    [problem] = check_freshness(held, date(2027, 2, 1))
    assert "retrieved 2026-11-12" in problem
    rows = read_timeseries_csv(held)
    write_timeseries_csv([row for row in rows if row is not _owned(rows)[0]], held)
    assert any("rows held" in line for line in check_freshness(held, ACCESSED))


def test_cli_check_reports_missing_manifest(held: Path, capsys) -> None:
    assert main(["--check", "--timeseries", str(held)]) == 1
    assert "STALE" in capsys.readouterr().err


def test_curated_snapshot_is_consistent_with_its_manifest() -> None:
    manifest = json.loads(CURATED.with_name(MANIFEST_NAME).read_text(encoding="utf-8"))
    retrieved = date.fromisoformat(manifest["retrieved_date"])
    assert check_freshness(CURATED, retrieved) == []
