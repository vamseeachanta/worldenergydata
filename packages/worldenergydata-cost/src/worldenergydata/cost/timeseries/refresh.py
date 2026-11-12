"""
ABOUTME: Monthly refresh and offline check of the public reference series (CPI, PPI, oil price).
ABOUTME: Replaces only the rows fetched from FRED; hand-cited research rows are never rewritten.

Run from the repository root::

    python -m worldenergydata.cost.timeseries.refresh            # fetch and rewrite
    python -m worldenergydata.cost.timeseries.refresh --check    # offline check

The refresh owns exactly the rows whose ``SOURCE_URL`` is the FRED page of a
series pinned in ``reference_series.REFERENCE_SERIES``. Every other row is
written back unchanged. A manifest beside the CSV records, per series, the
retrieval date, the first and last monthly observation and a digest of the
fetched observations, so freshness can be checked without network access.

Validation runs before anything is written. A failed validation leaves the
curated file and the manifest untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from worldenergydata.cost.timeseries.dataset import (
    TIMESERIES_CSV,
    read_timeseries_csv,
    write_timeseries_csv,
)
from worldenergydata.cost.timeseries.reference_series import (
    FRED_PAGE,
    REFERENCE_SERIES,
    ReferenceSeriesSpec,
    build_reference_observations,
    fetch_fred_series,
)
from worldenergydata.cost.timeseries.schema import CostObservation

__all__ = [
    "MANIFEST_NAME",
    "RefreshError",
    "RefreshResult",
    "check_freshness",
    "merge_reference_rows",
    "refresh",
    "validate_reference_rows",
]

MANIFEST_NAME = "reference_series.manifest.json"
START_YEAR = 1998
#: BLS and EIA publish each month about one month in arrears; allow two missed
#: releases before the newest observation counts as stale.
MAX_OBSERVATION_LAG_DAYS = 120
#: A complete calendar year that moves by more than this is treated as a
#: rebased or redefined series, not a routine statistical revision.
MAX_COMPLETE_YEAR_REVISION = 0.05
_CURATED = Path("data/modules/cost/curated")

Fetch = Callable[[str], list[tuple[date, float]]]


class RefreshError(ValueError):
    """The fetched series failed validation; nothing was written."""


@dataclass(frozen=True)
class RefreshResult:
    rows_written: int
    reference_rows: int
    revisions: tuple[str, ...]
    manifest: dict


def _owned_urls(specs: Sequence[ReferenceSeriesSpec]) -> dict[str, ReferenceSeriesSpec]:
    return {FRED_PAGE.format(series_id=spec.series_id): spec for spec in specs}


def _is_owned(row: CostObservation, owned: dict[str, ReferenceSeriesSpec]) -> bool:
    spec = owned.get(row.source_url or "")
    return spec is not None and row.component == spec.component


def merge_reference_rows(
    existing: Sequence[CostObservation],
    fetched: Sequence[CostObservation],
    specs: Sequence[ReferenceSeriesSpec] = REFERENCE_SERIES,
) -> list[CostObservation]:
    """Return ``existing`` with every refresh-owned row replaced by ``fetched``."""
    owned = _owned_urls(specs)
    stray = [row for row in fetched if not _is_owned(row, owned)]
    if stray:
        raise RefreshError("fetched rows include a series the refresh does not own")
    return [row for row in existing if not _is_owned(row, owned)] + list(fetched)


def _complete_year(row: CostObservation) -> bool:
    return "PARTIAL YEAR" not in (row.notes or "")


def validate_reference_rows(
    existing: Sequence[CostObservation],
    fetched: Sequence[CostObservation],
    monthly: dict[str, list[tuple[date, float]]],
    accessed_date: date,
    specs: Sequence[ReferenceSeriesSpec] = REFERENCE_SERIES,
) -> tuple[str, ...]:
    """Validate a fetch against the held rows; return routine revisions found.

    Raises ``RefreshError`` when a series is missing, has a gap in its years,
    holds a non-finite or non-positive value, has lost a year that was held,
    is stale, or has a complete year that moved by more than
    ``MAX_COMPLETE_YEAR_REVISION``.
    """
    owned = _owned_urls(specs)
    problems: list[str] = []
    revisions: list[str] = []
    for url, spec in owned.items():
        name = spec.series_id
        new = {row.year: row for row in fetched if row.source_url == url}
        old = {
            row.year: row
            for row in existing
            if row.source_url == url and row.component == spec.component
        }
        if not new:
            problems.append(f"{name}: no rows fetched")
            continue
        years = sorted(new)
        if years != list(range(years[0], years[-1] + 1)):
            problems.append(f"{name}: gap in fetched years")
        if any(
            row.value is None or not math.isfinite(row.value) or row.value <= 0
            for row in new.values()
        ):
            problems.append(f"{name}: non-finite or non-positive value")
            continue
        lost = sorted(set(old) - set(new))
        if lost:
            problems.append(f"{name}: held years missing from fetch: {lost}")
        observations = monthly.get(name) or []
        if not observations:
            problems.append(f"{name}: no monthly observations recorded")
        else:
            lag = (accessed_date - max(day for day, _ in observations)).days
            if lag > MAX_OBSERVATION_LAG_DAYS:
                problems.append(
                    f"{name}: newest observation is {lag} days old "
                    f"(limit {MAX_OBSERVATION_LAG_DAYS})"
                )
        for year in sorted(set(old) & set(new)):
            before, after = old[year], new[year]
            if before.value is None or not _complete_year(before):
                continue
            change = after.value / before.value - 1.0
            if abs(change) > MAX_COMPLETE_YEAR_REVISION:
                problems.append(
                    f"{name} {year}: complete-year value moved {change:+.1%} "
                    f"({before.value} to {after.value})"
                )
            elif before.value != after.value:
                revisions.append(
                    f"{name} {year}: {before.value} to {after.value} ({change:+.2%})"
                )
    if problems:
        shown = "; ".join(problems[:5])
        more = f"; and {len(problems) - 5} more" if len(problems) > 5 else ""
        raise RefreshError(shown + more)
    return tuple(revisions)


def _manifest(
    fetched: Sequence[CostObservation],
    monthly: dict[str, list[tuple[date, float]]],
    accessed_date: date,
    specs: Sequence[ReferenceSeriesSpec],
) -> dict:
    series = []
    for spec in specs:
        observations = sorted(monthly[spec.series_id])
        payload = "".join(
            f"{day.isoformat()},{value!r}\n" for day, value in observations
        )
        url = FRED_PAGE.format(series_id=spec.series_id)
        series.append(
            {
                "series_id": spec.series_id,
                "component": spec.component.value,
                "title": spec.title,
                "publisher": spec.publisher,
                "source_url": url,
                "unit": spec.unit,
                "first_observation": observations[0][0].isoformat(),
                "last_observation": observations[-1][0].isoformat(),
                "monthly_observations": len(observations),
                "annual_rows": sum(row.source_url == url for row in fetched),
                "observations_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            }
        )
    return {
        "schema": "cost_reference_series_manifest.v1",
        "retrieved_date": accessed_date.isoformat(),
        "start_year": START_YEAR,
        "reduction": "calendar-year arithmetic mean of monthly observations",
        "series": series,
    }


def _write_json(payload: dict, path: Path) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def refresh(
    timeseries_path: Path,
    accessed_date: date,
    fetch: Fetch = fetch_fred_series,
    specs: Sequence[ReferenceSeriesSpec] = REFERENCE_SERIES,
    manifest_path: Path | None = None,
) -> RefreshResult:
    """Fetch every pinned series, validate, then rewrite the CSV and manifest."""
    monthly: dict[str, list[tuple[date, float]]] = {}

    def recording_fetch(series_id: str) -> list[tuple[date, float]]:
        monthly[series_id] = list(fetch(series_id))
        return monthly[series_id]

    existing = read_timeseries_csv(timeseries_path)
    fetched = build_reference_observations(
        accessed_date=accessed_date,
        start_year=START_YEAR,
        specs=tuple(specs),
        fetch=recording_fetch,
    )
    revisions = validate_reference_rows(
        existing, fetched, monthly, accessed_date, specs
    )
    merged = merge_reference_rows(existing, fetched, specs)
    manifest = _manifest(fetched, monthly, accessed_date, specs)

    staged = timeseries_path.with_name(f".{timeseries_path.name}.tmp")
    try:
        written = write_timeseries_csv(merged, staged)
        read_timeseries_csv(staged)  # the staged file must pass the row contract
        os.replace(staged, timeseries_path)
    finally:
        staged.unlink(missing_ok=True)
    _write_json(manifest, manifest_path or timeseries_path.with_name(MANIFEST_NAME))
    return RefreshResult(written, len(fetched), revisions, manifest)


def check_freshness(
    timeseries_path: Path,
    today: date,
    max_age_days: int = 45,
    manifest_path: Path | None = None,
    specs: Sequence[ReferenceSeriesSpec] = REFERENCE_SERIES,
) -> list[str]:
    """Offline check of the held file against its manifest; return problems."""
    path = manifest_path or timeseries_path.with_name(MANIFEST_NAME)
    if not path.exists():
        return [f"manifest not found: {path.name}; run the refresh"]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []
    retrieved = date.fromisoformat(manifest["retrieved_date"])
    age = (today - retrieved).days
    if age > max_age_days:
        problems.append(
            f"reference series retrieved {retrieved.isoformat()}, {age} days ago "
            f"(limit {max_age_days})"
        )
    rows = read_timeseries_csv(timeseries_path)
    recorded = {entry["series_id"]: entry for entry in manifest["series"]}
    for spec in specs:
        entry = recorded.get(spec.series_id)
        if entry is None:
            problems.append(f"{spec.series_id}: pinned series absent from manifest")
            continue
        url = FRED_PAGE.format(series_id=spec.series_id)
        held = [
            row
            for row in rows
            if row.source_url == url and row.component == spec.component
        ]
        if len(held) != entry["annual_rows"]:
            problems.append(
                f"{spec.series_id}: {len(held)} rows held, manifest records "
                f"{entry['annual_rows']}"
            )
        if any(row.accessed_date != retrieved for row in held):
            problems.append(f"{spec.series_id}: row access date differs from manifest")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--timeseries", type=Path, default=_CURATED / TIMESERIES_CSV)
    parser.add_argument("--check", action="store_true", help="offline check only")
    parser.add_argument("--max-age-days", type=int, default=45)
    args = parser.parse_args(argv)
    today = date.today()
    if args.check:
        problems = check_freshness(args.timeseries, today, args.max_age_days)
        for problem in problems:
            print(f"STALE: {problem}", file=sys.stderr)
        if not problems:
            print("reference series: current")
        return 1 if problems else 0
    try:
        result = refresh(args.timeseries, today)
    except (RefreshError, RuntimeError, OSError) as exc:
        print(f"refresh failed, nothing written: {exc}", file=sys.stderr)
        return 2
    for revision in result.revisions:
        print(f"revised: {revision}")
    print(
        f"reference rows: {result.reference_rows}; rows written: {result.rows_written}; "
        f"retrieved {result.manifest['retrieved_date']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
