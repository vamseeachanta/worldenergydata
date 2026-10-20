"""Compare committed day tables and weekly records; no data fetching.
Milestone drilling is published TD minus spud; completion unions all records
on or after TD with union_days inclusive endpoints, excluding unreported gaps.
Missing published dates leave both milestone figures unavailable.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import re
from pathlib import Path
from statistics import mean, median

import pandas as pd

from worldenergydata.bsee.analysis.war_rig_days import (
    BASIS_DRL_COM,
    rig_days_by_bore,
    union_days,
)

NOTES = Path("docs/data-sources/bsee/analysis/rig_days")
WEEKLY = Path("docs/modules/bsee/analysis/rig_days")
TABLES = Path("docs/modules/bsee/analysis/production/FDAS_V30")
EXPORT = TABLES / "drilling_and_completion_days_v21_kc.csv"
WORKBOOK = TABLES / "drilling_and_completion_days.xlsx"
QA = Path("reports/lower_tertiary/data/roy_rig_days_qa.csv")
BENCHMARK = Path(
    "reports/lower_tertiary/lt_well_benchmark_lower_tertiary_2010_latest.csv"
)
SAMPLE = Path("data/modules/bsee/current/operations/well_activity_summary.csv")
MISSING = "not computed: records not in the repository"
RULES = ("ratified", "interim", "milestone")


def _nullable(value):
    return (
        None if pd.isna(value) else (value.item() if hasattr(value, "item") else value)
    )


def _date(value):
    parsed = pd.to_datetime(value, format="mixed", errors="coerce")
    return None if pd.isna(parsed) else parsed.normalize()


def _span_diagnostics(records):
    bounds = []
    for start, end in zip(records.WAR_START_DT, records.WAR_END_DT):
        start, end = _date(start), _date(end)
        if start is not None and end is not None and end >= start:
            bounds.append((start, end))
    gaps = []
    current_end = None
    for start, end in sorted(bounds):
        if current_end is not None and start > current_end + pd.Timedelta(days=1):
            gaps.append((current_end.date().isoformat(), start.date().isoformat()))
        current_end = end if current_end is None else max(end, current_end)
    identity = "API_WELL_NUMBER WAR_START_DT WAR_END_DT WELL_ACTIVITY_CD".split()
    return {
        "first_record_date": min(s for s, _ in bounds).date().isoformat(),
        "last_record_date": max(e for _, e in bounds).date().isoformat(),
        "gap_count": len(gaps),
        "gap_boundaries": gaps,
        "duplicate_count": int(records.duplicated(subset=identity).sum()),
    }


def count_ratified_days(records: pd.DataFrame) -> dict:
    """One wellbore; code unions may overlap, overall total is a union."""
    if records.API_WELL_NUMBER.astype(str).str.strip().nunique() != 1:
        raise ValueError("Exactly one wellbore is required")
    frame = rig_days_by_bore(records, basis=BASIS_DRL_COM)
    if len(frame) != 1:
        raise ValueError("No usable weekly intervals")
    bore = frame.iloc[0]
    codes = bore.days_by_code
    normalized = records.WELL_ACTIVITY_CD.astype(str).str.strip().str.upper()
    coded = records[~normalized.isin({"", "NAN", "NONE"})]
    coded_total = union_days(
        zip(map(_date, coded.WAR_START_DT), map(_date, coded.WAR_END_DT))
    )
    other = {
        k: int(v) for k, v in codes.items() if k not in {"DRL", "COM", "DSI", "TA"}
    }
    result = {
        "drilling_days": _nullable(bore.drilling_days),
        "completion_days": _nullable(bore.completion_days),
        "suspended_days": int(codes.get("DSI", 0)),
        "temporarily_abandoned_days": int(codes.get("TA", 0)),
        "other_days_by_code": other,
        "other_coded_days": sum(other.values()),
        "pnd_days": int(codes.get("PND", 0)),
        "total_days": int(bore.war_days_total),
        "weekly_records": len(records),
        **{
            f"{k}_records": int(bore[f"war_weeks_{k}"])
            for k in ("unattributed", "rejected", "implausible")
        },
        "unattributed_days": int(bore.war_days_total) - coded_total,
        "cross_code_excess_days": sum(codes.values()) - coded_total,
        **{
            f"activity_code_{k}_days": int(codes.get(k, 0))
            for k in set(codes) | {"DRL", "COM", "DSI", "TA", "PND", "PA"}
        },
    }
    return {**result, **_span_diagnostics(records)}


def count_interim_days(spud, total_depth, last_record) -> tuple:
    """Summary lines 25 and 33: inclusive spud-to-TD and preferred method 3."""
    spud, total_depth, last_record = map(_date, (spud, total_depth, last_record))

    def span(start, end):
        if start is None or end is None or end < start:
            return None
        return (end - start).days + 1

    return span(spud, total_depth), span(total_depth, last_record)


def count_milestone_days(records, spud, total_depth) -> dict:
    """Published date difference and inclusive reported-day union after TD."""
    spud, td = map(_date, (spud, total_depth))
    result = dict(
        milestone_drilling_days=None,
        milestone_completion_days=None,
        milestone_completion_days_by_code=None,
        milestone_status="not computed: dates not published",
    )
    if spud is None or td is None:
        return result
    if td < spud:
        result["milestone_status"] = "not computed: reversed published dates"
        return result
    spans = []
    for start, end, code in zip(
        records.WAR_START_DT, records.WAR_END_DT, records.WELL_ACTIVITY_CD
    ):
        start, end = map(_date, (start, end))
        if start is not None and end is not None and end >= start and end >= td:
            spans.append((max(start, td), end, str(code).strip().upper()))
    result.update(
        milestone_drilling_days=(td - spud).days,
        milestone_completion_days=union_days((s, e) for s, e, _ in spans),
        milestone_completion_days_by_code={
            c: union_days((s, e) for s, e, k in spans if k == c)
            for c in sorted({k for _, _, k in spans})
        },
        milestone_status="computed from published dates and repository records",
    )
    return result


def _read_csv(root, path):
    frame = pd.read_csv(root / path, dtype=str, encoding="utf-8")
    return frame.where(frame.notna(), None)


def load_weekly_records(root: Path) -> tuple:
    """Read the two committed histories and the small operational sample."""
    frames, scope = [], {}
    for path in sorted((root / WEEKLY).glob("war_data_*.csv")):
        frame = pd.read_csv(path, dtype=str, encoding="utf-8")
        frames.append(frame)
        for api in frame.API_WELL_NUMBER:
            scope[api] = ("per-well history", path.relative_to(root).as_posix())
    sample = _read_csv(root, SAMPLE)
    sample = sample[~sample.API_WELL_NUMBER.isin(scope)]
    frames.append(sample)
    for api in sample.API_WELL_NUMBER:
        scope[api] = ("sparse operational sample", SAMPLE.as_posix())
    return pd.concat(frames, ignore_index=True), scope


def _publication_rows(frame, source, api_col, drilling_col, completion_col):
    rows = []
    for index, record in frame.iterrows():
        api = record[api_col]
        if api is None or pd.isna(api):
            continue
        row = {
            "api12": str(api),
            "published_table": source,
            "published_row": int(index) + 2,
            "published_drilling_days": _number(record[drilling_col]),
            "published_completion_days": _number(record[completion_col]),
            "spud_date": record.get("WELL_SPUD_DATE", record.get("spud")),
            "total_depth_date": record.get("TOTAL_DEPTH_DATE"),
            "milestone_source": source,
        }
        rows.append(row)
        no_dates = all(_date(row[k]) is None for k in ("spud_date", "total_depth_date"))
        for metric in ("drilling", "completion"):
            key = f"published_{metric}_days"
            if row[key] == 0 and no_dates:
                row[key] = None
                row[f"published_{metric}_status"] = "not published"
    return rows


def _number(value):
    return None if value is None or pd.isna(value) or value == "" else float(value)


def load_publications(root: Path) -> list:
    export = _read_csv(root, EXPORT)
    book = pd.read_excel(root / WORKBOOK, sheet_name="Sheet1", dtype=str)
    qa = _read_csv(root, QA)
    qa = qa[qa.grain.eq("bore")]
    benchmark = _read_csv(root, BENCHMARK)
    rows = []
    for frame, source, workbook_columns in [
        (book, WORKBOOK.as_posix() + ":Sheet1", True),
        (export, EXPORT.as_posix(), True),
        (qa, QA.as_posix(), False),
        (benchmark, BENCHMARK.as_posix(), False),
    ]:
        columns = ["api12", "drilling_days", "completion_days"]
        if source == BENCHMARK.as_posix():
            # Issue #1077 (2026): read the explicit calendar name. This audit
            # retains historical diagnostic output keys, not a rig-time claim.
            columns[1] = "spud_to_completion_calendar_days"
        if workbook_columns:
            columns = ["API_WELL_NUMBER", "DRILLING_DAYS", "COMPLETION_DAYS"]
        rows.extend(_publication_rows(frame, source, *columns))
    milestones = export.set_index("API_WELL_NUMBER").to_dict("index")
    for row in rows:
        if row["published_table"] in {QA.as_posix(), BENCHMARK.as_posix()}:
            dates = milestones.get(row["api12"], {})
            row["total_depth_date"] = dates.get("TOTAL_DEPTH_DATE")
            if row["published_table"] == QA.as_posix():
                row["spud_date"] = dates.get("WELL_SPUD_DATE")
            row["milestone_source"] = (
                EXPORT.as_posix() + ":API_WELL_NUMBER=" + row["api12"]
            )
    return rows + _note_rows(root)


def _note_rows(root):
    milestone = (root / NOTES / "rig_days_by_milestone.md").read_text(encoding="utf-8")
    fields = re.search(r"\| -\d+\s*\| (\d+)\s*\| ([^|]+)\| ([^|]+)\| (\d+)", milestone)
    api, spud, td, drilling = (s.strip() for s in fields.groups())
    completion = re.search(r"completion days for this well = (\d+)", milestone).group(1)
    summary = (root / NOTES / "rig_days_summary.md").read_text(encoding="utf-8")
    codes = ast.literal_eval(re.search(r'\{"COM":[^\n]+\}', summary).group())
    return [
        dict(
            api12=api,
            published_table=(NOTES / name).as_posix(),
            published_row=line,
            published_drilling_days=drill,
            published_completion_days=complete,
            spud_date=spud,
            total_depth_date=td,
            milestone_source=(NOTES / "rig_days_by_milestone.md").as_posix() + ":16",
        )
        for name, line, drill, complete in [
            ("rig_days_summary.md", 18, codes["DRL"], codes["COM"]),
            ("rig_days_by_milestone.md", 16, int(drilling), int(completion)),
        ]
    ]


def _differences(row, rule):
    for metric in ("drilling", "completion"):
        value = row.get(f"{rule}_{metric}_days")
        published = row[f"published_{metric}_days"]
        delta = None if value is None or published is None else value - published
        row[f"{rule}_{metric}_difference_days"] = delta
        row[f"{rule}_{metric}_difference_pct"] = (
            None if delta is None or published == 0 else 100 * delta / published
        )


def build_comparison(root: Path) -> list:
    weekly, scope = load_weekly_records(root)
    groups = dict(tuple(weekly.groupby("API_WELL_NUMBER")))
    counted = {api: count_ratified_days(group) for api, group in groups.items()}
    rows = []
    for publication in load_publications(root):
        row = dict(publication, milestone_status="not computed: dates not published")
        api = row["api12"]
        if api not in counted:
            row.update(status=MISSING, coverage="absent")
            if all(
                _date(row[k]) is not None for k in ("spud_date", "total_depth_date")
            ):
                row["milestone_status"] = MISSING
        else:
            categories = (
                "drilling_days completion_days suspended_days "
                "temporarily_abandoned_days other_coded_days total_days pnd_days"
            ).split()
            row.update(
                {
                    f"ratified_{k}" if k in categories else k: v
                    for k, v in counted[api].items()
                }
            )
            row["coverage"], row["weekly_source"] = scope[api]
            row["status"] = (
                "computed from repository records; complete history not established"
            )
            row["interim_drilling_days"], row["interim_completion_days"] = (
                count_interim_days(
                    row["spud_date"], row["total_depth_date"], row["last_record_date"]
                )
            )
            row.update(
                count_milestone_days(
                    groups[api], row["spud_date"], row["total_depth_date"]
                )
            )
        for rule in RULES:
            _differences(row, rule)
        rows.append(row)
    return sorted(rows, key=lambda r: (r["published_table"], r["api12"]))


def csv_rows(rows):
    keys = sorted(set().union(*(row.keys() for row in rows)))
    added = [
        k
        for k in keys
        if k.startswith("activity_code_")
        or (k.startswith("milestone_") and k != "milestone_source")
        or k.endswith("_status")
    ]
    keys = [k for k in keys if k not in added] + added

    def cell(value):
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        return "" if value is None or pd.isna(value) else str(value)

    return [{key: cell(row.get(key)) for key in keys} for row in rows]


def comparison_csv(rows):
    stream = io.StringIO(newline="")
    normalized = csv_rows(rows)
    writer = csv.DictWriter(stream, fieldnames=list(normalized[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(normalized)
    return stream.getvalue()


def summary_statistics(rows):
    """Paired numeric comparisons, by source and coverage, without pooling tables."""
    summaries = []
    groups = {}
    for row in rows:
        if row["coverage"] != "absent":
            groups.setdefault((row["published_table"], row["coverage"]), []).append(row)
    for (source, coverage), group in sorted(groups.items()):
        for metric in ("drilling", "completion"):
            paired = [
                r
                for r in group
                if None
                not in [r.get(f"{rule}_{metric}_difference_days") for rule in RULES]
            ]
            for rule in RULES:
                diffs = [r[f"{rule}_{metric}_difference_days"] for r in paired]
                if not diffs:
                    continue
                percentages = [r[f"{rule}_{metric}_difference_pct"] for r in paired]
                summaries.append(
                    dict(
                        published_table=source,
                        coverage=coverage,
                        metric=metric,
                        rule=rule,
                        wells=len(paired),
                        median_absolute_days=median(map(abs, diffs)),
                        maximum_absolute_days=max(map(abs, diffs)),
                        within_five_days=sum(abs(d) <= 5 for d in diffs),
                        within_five_pct=sum(
                            abs(p) <= 5 for p in percentages if p is not None
                        ),
                        mean_signed_days=mean(diffs),
                    )
                )
    return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = build_comparison(args.root)
    target = args.output or args.root / NOTES / "day_basis_comparison.csv"
    target.write_text(comparison_csv(rows), encoding="utf-8", newline="")
    print(json.dumps(summary_statistics(rows), indent=2))


if __name__ == "__main__":
    main()
