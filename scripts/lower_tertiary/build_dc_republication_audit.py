"""Audit D&C basis changes locally without replacing a published figure.

Run with the namespace package paths and scripts on PYTHONPATH, supplying
--output outside the repository. The JSON keeps every published bore, all three
methods, the input digests, and paired before/after subtotals by development
and coverage. A paired subtotal is never a replacement development total.

Example: python scripts/lower_tertiary/build_dc_republication_audit.py
--output "$TMPDIR/dc-republication-audit.json"

Basis source: issue #1064, milestone-default decision of 2026-10-12;
docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.md,
"Rule and conventions".
Day arithmetic is delegated to the existing comparison module. No rates,
financial assumptions, acceptance tolerances or new interval rules are added.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from worldenergydata.bsee.analysis import ratified_day_basis_comparison as comparison

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lower_tertiary.build_wo_per_well_dc import DEV_OF_LEASE

REPO = Path(__file__).resolve().parents[2]
SOURCE = comparison.EXPORT
WEEKLY = comparison.WEEKLY
SAMPLE = comparison.SAMPLE
METRICS = ("drilling_days", "completion_days", "dc_days")
BASES = {
    "milestone": "calendar TD minus spud; union of reported days from TD onward",
    "activity_code": "DRL and COM unions separately; other activity codes excluded",
    "interim": "inclusive spud to TD; inclusive TD to last reported end",
}
PENDING = "NOT_EVALUATED"
CONFIRMATION = (
    "Wider-population confirmation is required before replacing published figures; "
    "held records and numeric agreement do not certify complete weekly histories."
)


def _days(raw):
    """Preserve blank published cells; reject invalid counts rather than coerce."""
    if raw is None or not str(raw).strip():
        return None
    try:
        value = Decimal(str(raw))
    except InvalidOperation as error:
        raise ValueError("invalid published day count") from error
    if not value.is_finite() or value < 0 or value != value.to_integral_value():
        raise ValueError("invalid published day count")
    return int(value)


def _sum_known(values):
    items = list(values)
    return None if not items or any(v is None for v in items) else sum(items)


def _metrics(drill=None, complete=None):
    return {
        "drilling_days": drill,
        "completion_days": complete,
        "dc_days": _sum_known((drill, complete)),
    }


def _delta(before, after):
    # Issue #1079, "Mandatory: show the change": new minus old, on identical bores.
    return {
        key: (
            None
            if before[key] is None or after[key] is None
            else after[key] - before[key]
        )
        for key in METRICS
    }


def _published_rows(root):
    with (root / SOURCE).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {
            "API_WELL_NUMBER",
            "LEASE_NAME",
            "DRILLING_DAYS",
            "COMPLETION_DAYS",
            "WELL_SPUD_DATE",
            "TOTAL_DEPTH_DATE",
        }
        if not required.issubset(reader.fieldnames or ()):
            raise ValueError("published population is missing required columns")
        rows = list(reader)
    apis = [row["API_WELL_NUMBER"].strip() for row in rows]
    if (
        not rows
        or not all(apis)
        or len(set(apis)) != len(apis)
        or any(not row["LEASE_NAME"].strip() for row in rows)
    ):
        raise ValueError("published population requires unique identifiers and leases")
    return rows


def _bore(row, records, scope):
    api = row["API_WELL_NUMBER"].strip()
    lease = row["LEASE_NAME"].strip()
    before = _metrics(_days(row["DRILLING_DAYS"]), _days(row["COMPLETION_DAYS"]))
    comparable = dict(before)
    # Preserve the comparison module's rule: zero without either valid milestone
    # is not published. Retain the displayed snapshot but exclude it from pairs.
    no_dates = all(
        comparison._date(row[key]) is None
        for key in ("WELL_SPUD_DATE", "TOTAL_DEPTH_DATE")
    )
    for metric in ("drilling_days", "completion_days"):
        if no_dates and comparable[metric] == 0:
            comparable[metric] = None
    comparable["dc_days"] = _sum_known(
        comparable[key] for key in ("drilling_days", "completion_days")
    )
    after = {name: _metrics() for name in BASES}
    activity = None
    coverage, source = scope.get(api, ("absent", None))
    reason = "Weekly records are not available for this published bore."
    if api in records:
        group = records[api]
        try:
            activity = comparison.count_ratified_days(group)
        except ValueError:
            # An empty/reversed history must not yield measured zero days.
            reason = "No usable weekly intervals; source records require correction."
        else:
            milestone = comparison.count_milestone_days(
                group, row["WELL_SPUD_DATE"], row["TOTAL_DEPTH_DATE"]
            )
            after["milestone"] = _metrics(
                milestone["milestone_drilling_days"],
                milestone["milestone_completion_days"],
            )
            after["activity_code"] = _metrics(
                activity["drilling_days"], activity["completion_days"]
            )
            after["interim"] = _metrics(
                *comparison.count_interim_days(
                    row["WELL_SPUD_DATE"],
                    row["TOTAL_DEPTH_DATE"],
                    activity["last_record_date"],
                )
            )
            reason = CONFIRMATION
    return {
        "api12": api,
        "development": DEV_OF_LEASE.get(lease, lease),
        "before_basis": row.get("BASIS") or "unlabelled legacy output",
        "before": before,
        "comparable_before": comparable,
        "spud_date": row["WELL_SPUD_DATE"] or None,
        "total_depth_date": row["TOTAL_DEPTH_DATE"] or None,
        "coverage": coverage,
        "weekly_source": source,
        "status": PENDING,
        "reason": reason,
        "activity_breakdown": activity,
        "methods": {
            method: {
                "basis": BASES[method],
                "after": values,
                "delta": _delta(comparable, values),
            }
            for method, values in after.items()
        },
    }


def _paired(bores, method):
    """Compare identical bore/metric pairs, separating sparse samples from histories."""
    result = {}
    for coverage in sorted({b["coverage"] for b in bores} - {"absent"}):
        metrics = {}
        for metric in METRICS:
            pairs = [
                (b["comparable_before"][metric], b["methods"][method]["after"][metric])
                for b in bores
                if b["coverage"] == coverage
                and b["comparable_before"][metric] is not None
                and b["methods"][method]["after"][metric] is not None
            ]
            # Issue #1079 comparison matrix: sum only the same paired contributors.
            before = _sum_known(p[0] for p in pairs)
            after = _sum_known(p[1] for p in pairs)
            metrics[metric] = {
                "bores": len(pairs),
                "before": before,
                "after": after,
                "delta": None if not pairs else after - before,
            }
        result[coverage] = metrics
    return result


def _development(name, bores):
    bases = sorted({b["before_basis"] for b in bores})
    return {
        "development": name,
        "bores": len(bores),
        "before_basis": bases[0] if len(bases) == 1 else "mixed",
        "before_bases": bases,
        # Legacy zero placeholders are retained as displayed, not validated as zeros.
        "before": {key: _sum_known(b["before"][key] for b in bores) for key in METRICS},
        "coverage": dict(sorted(Counter(b["coverage"] for b in bores).items())),
        "status": PENDING,
        "reason": CONFIRMATION,
        "methods": {
            method: {
                "basis": basis,
                "after": None,
                "delta": None,
                "paired_by_coverage": _paired(bores, method),
            }
            for method, basis in BASES.items()
        },
    }


def build_audit(root: Path) -> dict:
    """Read committed-format inputs; never infer readiness from available subsets."""
    rows = _published_rows(root)
    weekly, scope = comparison.load_weekly_records(root)
    records = dict(tuple(weekly.groupby("API_WELL_NUMBER")))
    bores = sorted((_bore(r, records, scope) for r in rows), key=lambda b: b["api12"])
    inputs = [
        SOURCE,
        SAMPLE,
        *sorted(
            path.relative_to(root) for path in (root / WEEKLY).glob("war_data_*.csv")
        ),
    ]
    return {
        "default_basis": "milestone",
        "units": "days",
        "limits": [
            "Paired subtotals cover only the indicated bore/metric pairs and coverage class.",
            "Displayed legacy zero placeholders remain in before totals but not in numeric pairs.",
            "Different activity-code unions can overlap; their sum need not equal the total union.",
            "All methods are retained; the default does not imply publication readiness.",
        ],
        "inputs": [
            {
                "path": p.as_posix(),
                "sha256": hashlib.sha256((root / p).read_bytes()).hexdigest(),
            }
            for p in inputs
        ],
        "publication": {"status": PENDING, "reason": CONFIRMATION},
        "npv_impact": {
            "status": PENDING,
            "reason": "Financial reruns on confirmed day inputs and a common cost deck are required.",
        },
        "surface_agreement": {
            "status": PENDING,
            "reason": "The published reports, tables and downstream consumers have not been regenerated.",
        },
        "bores": bores,
        "developments": [
            _development(name, [b for b in bores if b["development"] == name])
            for name in sorted({b["development"] for b in bores})
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root, output = args.root.resolve(), args.output.resolve()
    if output.is_relative_to(root):
        parser.error("audit output must be outside the repository")
    result = build_audit(root)
    output.write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
