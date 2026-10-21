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
from datetime import date
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path

from worldenergydata.bsee.analysis import ratified_day_basis_comparison as comparison

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lower_tertiary.build_wo_per_well_dc import DEV_OF_LEASE
from lower_tertiary.dc_surface_audit import audit_surfaces
from lower_tertiary.war_methodology import WAR_METHODOLOGY

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
NPV_REASON = (
    "Financial reruns on confirmed day inputs and a common cost deck are required; "
    "a day-count delta alone does not establish the discounted capital delta."
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
        "npv_impact": {"status": PENDING, "delta_usd": None, "reason": NPV_REASON},
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
            "reason": NPV_REASON,
        },
        "surface_agreement": audit_surfaces(root, bores),
        "bores": bores,
        "developments": [
            _development(name, [b for b in bores if b["development"] == name])
            for name in sorted({b["development"] for b in bores})
        ],
    }


def render_markdown(result: dict, *, revision_date: str) -> str:
    """Render the audit, keeping full totals separate from paired subtotals.

    Issue #1079 (2026), "Mandatory: show the change": after minus before.
    Only differences already calculated on identical contributors are shown.
    No financial conversion, discount rate, or tolerance is assumed here.
    """
    date.fromisoformat(revision_date)

    def cell(value):
        if value is None:
            return PENDING
        return (
            escape(str(value))
            .replace("|", "&#124;")
            .replace("\n", " ")
            .replace("\r", " ")
        )

    def row(values):
        return "| " + " | ".join(cell(v) for v in values) + " |"

    lines = [
        "# D&C republication review",
        "",
        (
            "Publication remains NOT_EVALUATED. Retained source figures are compared "
            "with available weekly records and local snapshots; published figures are not replaced."
        ),
        "",
        "## Revision history",
        "",
        "| Revision | Date | What changed and why |",
        "|---|---|---|",
        row(
            (
                "initial",
                revision_date,
                "Expose basis differences and missing evidence before replacement.",
            )
        ),
        "",
        "## Publication",
        "",
        cell(result["publication"]["reason"]),
        "",
        "Milestone is the comparison default; activity-code and interim methods remain available.",
        "",
        "## Retained development totals",
        "",
        (
            "All counts below are displayed source values, including legacy zero placeholders. "
            "Confirmed replacement totals and their changes remain unavailable."
        ),
        "",
        "| Development | Bores | Before drilling | Before completion | Before D&C | Replacement status | Before basis |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for dev in result["developments"]:
        lines.append(
            row(
                (
                    dev["development"],
                    dev["bores"],
                    *[dev["before"][m] for m in METRICS],
                    dev["status"],
                    dev["before_basis"],
                )
            )
        )
    lines.extend(
        [
            "",
            "## Before and after on identical contributors",
            "",
            (
                "Paired subtotals are not replacement development totals. Each metric has its own "
                "paired count; sparse samples and per-well histories are kept separate. "
                "Missing records and undated legacy zero placeholders do not become measured zeros."
            ),
            "",
            "| Development | Method | Coverage | Metric | Paired bores | Before | After | Change |",
            "|---|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for dev in result["developments"]:
        for method, values in dev["methods"].items():
            for coverage, metrics in values["paired_by_coverage"].items():
                for metric, pair in metrics.items():
                    delta = pair["delta"]
                    lines.append(
                        row(
                            (
                                dev["development"],
                                method,
                                coverage,
                                metric,
                                pair["bores"],
                                pair["before"],
                                pair["after"],
                                None if delta is None else f"{delta:+d}",
                            )
                        )
                    )
    lines.extend(["", "### Method and cause", ""])
    lines.extend(
        f"- **{cell(method)}:** {cell(basis)}." for method, basis in BASES.items()
    )
    lines.extend(
        [
            "",
            (
                "Milestone excludes unreported gaps; activity codes allocate whole reported intervals; "
                "interim counts calendar gaps and includes TD in both phases. "
                "These are method differences, not proof that incomplete histories are complete."
            ),
            "",
            "## NPV impact by development",
            "",
            cell(NPV_REASON),
            "",
            "| Development | Status | NPV change (USD) |",
            "|---|---|---:|",
        ]
    )
    lines.extend(
        row((d["development"], d["npv_impact"]["status"], d["npv_impact"]["delta_usd"]))
        for d in result["developments"]
    )
    lines.extend(
        [
            "",
            "## Snapshot consistency",
            "",
            cell(result["surface_agreement"]["reason"]),
            "",
            "| Surface | Status | Findings |",
            "|---|---|---:|",
        ]
    )
    for snapshot in result["surface_agreement"]["surfaces"]:
        lines.append(
            row(
                (
                    snapshot["surface"],
                    snapshot["status"],
                    len(snapshot.get("findings", [])),
                )
            )
        )
    lines.extend(["", "## Weekly records still needed", ""])
    for bore in result["bores"]:
        if bore["coverage"] == "absent":
            lines.append(f"- {cell(bore['api12'])}: {cell(bore['reason'])}")
    lines.extend(["", "## Input digests", "", "| Input | SHA-256 |", "|---|---|"])
    inputs = result["inputs"] + [
        s for s in result["surface_agreement"]["surfaces"] if s.get("sha256")
    ]
    lines.extend(row((item["path"], item["sha256"])) for item in inputs)
    lines.extend(
        [
            "",
            "## Sources and limits",
            "",
            (
                "Basis: issue #1064, milestone-default decision (2026-10-12); "
                "docs/data-sources/bsee/analysis/rig_days/day_basis_comparison.md, Rule and conventions. "
                "Interim: rig_days_summary.md (2025-06-02), preferred method 3. "
                "Change and surface scope: issue #1079 (2026)."
            ),
            "",
            *[f"- {cell(limit)}" for limit in result["limits"]],
            "- Vintage checks cover current-side day counts and membership; historical categories are not certified.",
            "- Dataset and website publication were not inspected. Fidelity pins remain unchanged.",
            "",
            WAR_METHODOLOGY.strip(),
            "",
        ]
    )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--report-date", type=date.fromisoformat)
    args = parser.parse_args(argv)
    root, output = args.root.resolve(), args.output.resolve()
    review = args.markdown_output.resolve() if args.markdown_output else None
    if any(p.is_relative_to(root) for p in (output, review) if p):
        parser.error("audit output must be outside the repository")
    if review and (review == output or not args.report_date):
        parser.error("review requires a distinct output and an explicit report date")
    result = build_audit(root)
    markdown = (
        render_markdown(result, revision_date=args.report_date.isoformat())
        if review
        else None
    )
    output.write_text(
        json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    if review:
        review.write_text(markdown, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
