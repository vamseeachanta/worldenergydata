"""Compare sanction estimates, escalated by public indices, with stated outturns.

Run ``python -m worldenergydata.cost.outturn_check --help`` from the repository
root. Method and limits: ``docs/modules/cost/OUTTURN_CHECK.md``.

For each project in the held revision trails with a USD sanction estimate and a
later USD final statement, the sanction amount is carried from its statement
year to the final statement year with the public-series factor
(``CostEscalator.factor(..., public_only=True)``) and set beside the stated
final amount. The result is arithmetic on held figures. It identifies no cause
for any difference. No network access and no currency conversion occur.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from worldenergydata.cost.escalation import CostEscalator, _json
from worldenergydata.cost.timeseries.dataset import read_timeseries_csv

__all__ = ["COLUMNS", "FINAL_KINDS", "build_outturn_checks", "main"]

FINAL_KINDS = ("final_outturn", "final_forecast")
_SANCTION = "sanction_estimate"
_CURATED = Path("data/modules/cost/curated")
COLUMNS = (
    "PROJECT",
    "STATUS",
    "REASON",
    "SANCTION_YEAR",
    "SANCTION_USD_MM",
    "FINAL_YEAR",
    "FINAL_KIND",
    "FINAL_USD_MM",
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


def _skip(project: str, reason: str) -> dict[str, str]:
    row = dict.fromkeys(COLUMNS, "")
    row.update(PROJECT=project, STATUS="NOT_EVALUATED", REASON=reason)
    return row


def build_outturn_checks(trails: Path, indices: Path) -> list[dict[str, str]]:
    """Return one row per trail project: an evaluated comparison or a reason."""
    escalator = CostEscalator(read_timeseries_csv(indices))
    with trails.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))
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
        base = _year(sanction["STATEMENT_DATE"])
        target = _year(final["STATEMENT_DATE"])
        if _precedes(final["STATEMENT_DATE"], sanction["STATEMENT_DATE"]):
            out.append(
                _skip(project, "final statement precedes the sanction statement")
            )
            continue
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
                "FINAL_YEAR": str(target),
                "FINAL_KIND": final["KIND"],
                "FINAL_USD_MM": repr(stated),
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
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    for source in (args.trails, args.indices):
        if args.output.resolve() == source.resolve() or (
            args.output.exists() and args.output.samefile(source)
        ):
            print("outturn_check: output must not overwrite an input", file=sys.stderr)
            return 2
    rows = build_outturn_checks(args.trails, args.indices)
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
