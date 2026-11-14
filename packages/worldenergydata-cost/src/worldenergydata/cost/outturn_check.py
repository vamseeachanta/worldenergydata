"""Compare sanction estimates, escalated by public indices, with stated outturns.

Run ``python -m worldenergydata.cost.outturn_check --help`` from the repository
root. Method and limits: ``docs/modules/cost/OUTTURN_CHECK.md``.

For each project in the held revision trails with a USD sanction estimate and a
later USD final statement, the sanction amount is carried from its statement
year to the final statement year with the public-series factor
(``CostEscalator.factor(..., public_only=True)``) and set beside the stated
final amount.

A comparison is evaluated only when both statements have been reviewed against
their source wording and each states an amount, exactly or approximately. A
statement that gives a bound ("more than", "under", "within"), or whose source
does not support the recorded date and kind, is listed as ``NOT_EVALUATED``
with the reason. The reviewed wording is held in
``cost_revision_trail_qualifiers.csv``.

The result is arithmetic on held figures. It identifies no cause for any
difference. No network access and no currency conversion occur.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from worldenergydata.cost.escalation import CostEscalator, _json
from worldenergydata.cost.timeseries.dataset import read_timeseries_csv

__all__ = [
    "COLUMNS",
    "COMPARABLE_QUALIFIERS",
    "FINAL_KINDS",
    "QUALIFIERS",
    "build_outturn_checks",
    "main",
    "read_qualifiers",
]

FINAL_KINDS = ("final_outturn", "final_forecast")
#: How the source words the amount. Only the first two support a comparison.
QUALIFIERS = ("exact", "approximate", "lower_bound", "upper_bound", "unsupported")
COMPARABLE_QUALIFIERS = ("exact", "approximate")
_SANCTION = "sanction_estimate"
_CURATED = Path("data/modules/cost/curated")
_QUALIFIER_COLUMNS = (
    "TRAIL_PROJECT",
    "STATEMENT_DATE",
    "KIND",
    "QUALIFIER",
    "EVIDENCE",
    "REVIEWED_DATE",
)
COLUMNS = (
    "PROJECT",
    "STATUS",
    "REASON",
    "SANCTION_YEAR",
    "SANCTION_USD_MM",
    "SANCTION_QUALIFIER",
    "SANCTION_CONFIDENCE",
    "FINAL_YEAR",
    "FINAL_KIND",
    "FINAL_USD_MM",
    "FINAL_QUALIFIER",
    "FINAL_CONFIDENCE",
    "INDEX_FACTOR",
    "INDEX_USED",
    "ESCALATED_SANCTION_USD_MM",
    "STATED_CHANGE",
    "INDEX_CHANGE",
    "FINAL_OVER_ESCALATED_SANCTION",
    "SANCTION_SOURCE_URL",
    "SANCTION_ACCESSED_DATE",
    "FINAL_SOURCE_URL",
    "FINAL_ACCESSED_DATE",
    "ESCALATION_NOTE",
    "INDEX_TRACE",
)

Key = tuple[str, str, str]


def _year(statement_date: str) -> int:
    year = int(statement_date[:4])
    if not 1970 <= year <= 2040:
        raise ValueError(f"statement year out of range: {statement_date}")
    return year


def _date_parts(statement_date: str) -> tuple[int, ...]:
    """``YYYY``, ``YYYY-MM`` or ``YYYY-MM-DD`` as integers, for ordering."""
    parts = tuple(int(part) for part in statement_date.strip().split("-"))
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"unsupported statement date: {statement_date}")
    return parts


def _precedes(later: str, earlier: str) -> bool:
    """True when ``later`` is before ``earlier`` at their shared precision."""
    a, b = _date_parts(later), _date_parts(earlier)
    shared = min(len(a), len(b))
    return a[:shared] < b[:shared]


def _amount(row: dict[str, str]) -> float:
    value = float(row["VALUE_MM"])
    if not value > 0:
        raise ValueError(f"{row['PROJECT']}: non-positive statement amount")
    return value


def _key(row: dict[str, str]) -> Key:
    return (row["PROJECT"], row["STATEMENT_DATE"], row["KIND"])


def _skip(project: str, reason: str) -> dict[str, str]:
    row = dict.fromkeys(COLUMNS, "")
    row.update(PROJECT=project, STATUS="NOT_EVALUATED", REASON=reason)
    return row


def read_qualifiers(path: Path, trail_keys: set[Key]) -> dict[Key, dict[str, str]]:
    """Read the reviewed statement wording; every row must match a trail row."""
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != _QUALIFIER_COLUMNS:
            raise ValueError("qualifier table has unexpected columns")
        records = list(reader)
    out: dict[Key, dict[str, str]] = {}
    for record in records:
        key = (record["TRAIL_PROJECT"], record["STATEMENT_DATE"], record["KIND"])
        if key not in trail_keys:
            raise ValueError(f"qualifier row matches no trail statement: {key}")
        if key in out:
            raise ValueError(f"duplicate qualifier row: {key}")
        if record["QUALIFIER"] not in QUALIFIERS:
            raise ValueError(f"unknown qualifier for {key}: {record['QUALIFIER']}")
        if not record["EVIDENCE"].strip() or not record["REVIEWED_DATE"].strip():
            raise ValueError(f"qualifier row lacks evidence or review date: {key}")
        out[key] = record
    return out


def _wording_reason(label: str, qualifier: dict[str, str] | None) -> str | None:
    """Reason a statement cannot enter an exact comparison, or ``None``."""
    if qualifier is None:
        return f"{label} statement wording not reviewed"
    kind = qualifier["QUALIFIER"]
    if kind in COMPARABLE_QUALIFIERS:
        return None
    described = {
        "lower_bound": "a lower bound",
        "upper_bound": "an upper bound",
        "unsupported": "not supported by its cited source",
    }[kind]
    return f"{label} statement is {described}: {qualifier['EVIDENCE']}"


def build_outturn_checks(
    trails: Path, indices: Path, qualifiers: Path
) -> list[dict[str, str]]:
    """Return one row per trail project: an evaluated comparison or a reason."""
    escalator = CostEscalator(read_timeseries_csv(indices))
    with trails.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
    reviewed = read_qualifiers(qualifiers, {_key(record) for record in records})
    projects: dict[str, list[dict[str, str]]] = {}
    for record in records:
        projects.setdefault(record["PROJECT"], []).append(record)

    out: list[dict[str, str]] = []
    for project in sorted(projects):
        rows = projects[project]
        sanctions = [row for row in rows if row["KIND"] == _SANCTION]
        finals = [row for row in rows if row["KIND"] in FINAL_KINDS]
        if len(sanctions) != 1:
            out.append(
                _skip(
                    project, f"{len(sanctions)} sanction estimates held; one required"
                )
            )
            continue
        if not finals:
            out.append(_skip(project, "no final outturn or final forecast held"))
            continue
        sanction = sanctions[0]
        final = max(finals, key=lambda row: _date_parts(row["STATEMENT_DATE"]))
        if sanction["CURRENCY"] != "USD" or final["CURRENCY"] != "USD":
            out.append(
                _skip(
                    project, "statements not in USD; no currency conversion is applied"
                )
            )
            continue
        if _precedes(final["STATEMENT_DATE"], sanction["STATEMENT_DATE"]):
            out.append(
                _skip(project, "final statement precedes the sanction statement")
            )
            continue
        sanction_wording = reviewed.get(_key(sanction))
        final_wording = reviewed.get(_key(final))
        reasons = [
            reason
            for reason in (
                _wording_reason("sanction", sanction_wording),
                _wording_reason("final", final_wording),
            )
            if reason
        ]
        if reasons:
            out.append(_skip(project, "; ".join(reasons)))
            continue
        base = _year(sanction["STATEMENT_DATE"])
        target = _year(final["STATEMENT_DATE"])
        try:
            factor = escalator.factor(base, target, public_only=True)
        except ValueError as exc:
            out.append(_skip(project, str(exc)))
            continue
        sanctioned, stated = _amount(sanction), _amount(final)
        escalated = sanctioned * factor.factor
        out.append(
            {
                "PROJECT": project,
                "STATUS": "EVALUATED",
                "REASON": "",
                "SANCTION_YEAR": str(base),
                "SANCTION_USD_MM": repr(sanctioned),
                "SANCTION_QUALIFIER": sanction_wording["QUALIFIER"],
                "SANCTION_CONFIDENCE": sanction["CONFIDENCE"],
                "FINAL_YEAR": str(target),
                "FINAL_KIND": final["KIND"],
                "FINAL_USD_MM": repr(stated),
                "FINAL_QUALIFIER": final_wording["QUALIFIER"],
                "FINAL_CONFIDENCE": final["CONFIDENCE"],
                "INDEX_FACTOR": repr(factor.factor),
                "INDEX_USED": factor.index_used,
                "ESCALATED_SANCTION_USD_MM": repr(escalated),
                "STATED_CHANGE": repr(stated / sanctioned - 1.0),
                "INDEX_CHANGE": repr(factor.factor - 1.0),
                "FINAL_OVER_ESCALATED_SANCTION": repr(stated / escalated - 1.0),
                "SANCTION_SOURCE_URL": sanction["SOURCE_URL"],
                "SANCTION_ACCESSED_DATE": sanction["ACCESSED_DATE"],
                "FINAL_SOURCE_URL": final["SOURCE_URL"],
                "FINAL_ACCESSED_DATE": final["ACCESSED_DATE"],
                "ESCALATION_NOTE": factor.note,
                "INDEX_TRACE": _json(list(factor.trace)),
            }
        )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--trails", type=Path, default=_CURATED / "cost_revision_trails.csv"
    )
    parser.add_argument(
        "--indices", type=Path, default=_CURATED / "cost_component_timeseries.csv"
    )
    parser.add_argument(
        "--qualifiers",
        type=Path,
        default=_CURATED / "cost_revision_trail_qualifiers.csv",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for source in (args.trails, args.indices, args.qualifiers):
        if args.output.resolve() == source.resolve() or (
            args.output.exists() and args.output.samefile(source)
        ):
            print("outturn_check: output must not overwrite an input", file=sys.stderr)
            return 2
    try:
        rows = build_outturn_checks(args.trails, args.indices, args.qualifiers)
    except ValueError as exc:
        print(f"outturn_check: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COLUMNS), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    evaluated = sum(row["STATUS"] == "EVALUATED" for row in rows)
    print(
        f"projects: {len(rows)}; evaluated: {evaluated}; "
        f"not evaluated: {len(rows) - evaluated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
