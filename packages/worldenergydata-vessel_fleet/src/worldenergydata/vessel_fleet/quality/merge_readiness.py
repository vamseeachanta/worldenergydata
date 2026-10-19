"""Read-only coverage assessment before replacing a curated drilling fleet.

Basis: issue #407 and the coverage-loss disclosure in merged PR #409 (2026).
This checks normalized-name retention, not physical identity or engineering
suitability. No engineering acceptance limit or dimension estimate is supplied.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path
from typing import Any

from worldenergydata.vessel_fleet.dedup.deduplicator import deduplicate_fleet
from worldenergydata.vessel_fleet.dedup.normalizer import normalize_vessel_name


def _name_counts(records: Sequence[Mapping[str, Any]]) -> Counter[str]:
    return Counter(
        normalize_vessel_name(value) if isinstance(value, str) else ""
        for record in records
        for value in [record.get("VESSEL_NAME")]
    )


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Real):
        return math.isfinite(value)
    return True


def assess_merge_readiness(
    baseline: Sequence[Mapping[str, Any]] | None,
    candidate: Sequence[Mapping[str, Any]],
    *,
    required_fields: Sequence[str] = (),
) -> dict[str, Any]:
    """Compare a candidate with the existing curated snapshot without mutation.

    Set equations: Discrete Mathematics: An Open Introduction, third
    edition (2019), section 0.3, Sets:
    https://discrete.openmathbooks.org/dmoi3/sec_intro-sets.html
    Replacement criterion: issue #407 / PR #409 coverage disclosure (2026).
    retained = B intersect C; added = C minus B; removed = B minus C,
    where B and C are distinct nonempty normalized names. Any removed name
    blocks replacement. No percentage tolerance is assumed. Missing/empty input,
    unnamed rows or duplicate names make coverage NOT_EVALUATED unless known
    loss already blocks it. Duplicate counts count names, not excess rows.

    Field presence is separate and requires explicit caller-selected fields.
    None, blank strings and nonfinite numbers are missing; zero is present.
    Presence does not establish valid units, values, provenance or freshness.
    """
    base_counts = _name_counts(baseline or [])
    candidate_counts = _name_counts(candidate)
    base_names = set(base_counts) - {""}
    candidate_names = set(candidate_counts) - {""}
    removed = base_names - candidate_names
    # A duplicate is a name occurring more than once, by definition.
    base_duplicates = sum(count > 1 for name, count in base_counts.items() if name)
    candidate_duplicates = sum(
        count > 1 for name, count in candidate_counts.items() if name
    )
    uncertain = (
        not baseline
        or not candidate
        or base_counts[""]
        or candidate_counts[""]
        or base_duplicates
        or candidate_duplicates
    )
    coverage_status = "PASS"
    if removed and candidate:
        coverage_status = "BLOCKED"
    elif uncertain:
        coverage_status = "NOT_EVALUATED"

    missing = {
        field: sum(not _present(record.get(field)) for record in candidate)
        for field in sorted(set(required_fields))
    }
    field_status = "NOT_EVALUATED"
    if candidate and missing:
        field_status = "BLOCKED" if any(missing.values()) else "PASS"

    return {
        "baseline_rows": len(baseline) if baseline is not None else None,
        "candidate_rows": len(candidate),
        "name_coverage": {
            "status": coverage_status,
            "baseline_unique_names": len(base_names),
            "candidate_unique_names": len(candidate_names),
            "retained_names": len(base_names & candidate_names),
            "added_names": len(candidate_names - base_names),
            "removed_names": len(removed),
            "baseline_unnamed_rows": base_counts[""],
            "candidate_unnamed_rows": candidate_counts[""],
            "baseline_duplicate_names": base_duplicates,
            "candidate_duplicate_names": candidate_duplicates,
        },
        "field_presence": {"status": field_status, "missing_by_field": missing},
        "engineering_validity": "NOT_EVALUATED",
    }


def assess_data_directory(
    data_dir: Path, *, required_fields: Sequence[str] = ()
) -> dict[str, Any]:
    """Read raw parquets and curated CSV; never create a store or write data.

    Uses the same recursive raw-source discovery and deduplication as
    scripts/vessel_fleet/fuse_and_deduplicate.py. Stops before hull estimation,
    schema validation or persistence. CSV is the human-readable baseline;
    CSV/parquet agreement is not established by this assessment.
    """
    import pandas as pd

    def records(frame: pd.DataFrame) -> list[dict[str, Any]]:
        # Object dtype permits None in numeric columns before deduplication.
        return frame.astype(object).where(frame.notna(), None).to_dict("records")

    raw_records = []
    source_rows = {}
    raw_dir = data_dir / "raw"
    source_dirs = sorted(raw_dir.iterdir()) if raw_dir.is_dir() else []
    for source_dir in source_dirs:
        if not source_dir.is_dir():
            continue
        for path in sorted(source_dir.rglob("*.parquet")):
            loaded = records(pd.read_parquet(path, engine="pyarrow"))
            source_rows[path.relative_to(raw_dir).as_posix()] = len(loaded)
            raw_records.extend(loaded)

    candidate = [
        record
        for record in deduplicate_fleet(raw_records)
        if record.get("VESSEL_CATEGORY") == "drilling_rig"
    ]
    baseline_path = data_dir / "curated" / "drilling_rigs.csv"
    baseline = (
        records(pd.read_csv(baseline_path, dtype=object))
        if baseline_path.is_file()
        else None
    )
    return {
        "raw_records": len(raw_records),
        "source_rows": source_rows,
        **assess_merge_readiness(baseline, candidate, required_fields=required_fields),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Print JSON: success only for the explicit coverage and presence checks.

    Exit codes are command-interface choices: 0 = explicit checks pass,
    2 = blocked/input error, 3 = not evaluated. Engineering validity always
    remains NOT_EVALUATED; this command never authorizes a curated write.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--required-field", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        report = assess_data_directory(
            args.data_dir, required_fields=args.required_field
        )
    except (OSError, ValueError, ImportError) as error:
        # Avoid echoing source payloads or absolute input paths in diagnostics.
        print(
            f"Unable to read assessment inputs ({type(error).__name__})",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    statuses = {report["name_coverage"]["status"], report["field_presence"]["status"]}
    if "BLOCKED" in statuses:
        return 2
    return 3 if "NOT_EVALUATED" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
