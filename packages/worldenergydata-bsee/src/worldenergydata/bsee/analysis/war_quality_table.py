"""Standalone WAR input diagnostics (issue #1681), without validation decisions.

``summarize_quality`` accepts the same input columns as ``war_rig_days``:
``API_WELL_NUMBER``, ``WAR_START_DT``, ``WAR_END_DT``, ``WELL_ACTIVITY_CD``.
The calendar year comes only from the parsed start date; a missing or
unparseable start has a nullable, unknown year, with no fallback to the end.
Dates are parsed independently as calendar values, with timezone offsets
normalized to UTC. Numeric calendar dates are not treated as epoch offsets.

Each observed (year, defect_type) emits one row; absent defects emit no row.
``missing_well_key`` means a null or whitespace-only key. ``reversed_dates``
requires two valid dates and an end before the start. ``unknown_activity_code``
means a code outside the caller's vocabulary, including null/blank activity.
Codes and vocabulary are stripped and uppercased for comparison only. No
activity meaning or production status is inferred and no input is repaired.

``count`` counts distinct input row positions within each defect, including
identical records and repeated index labels. ``affected_share`` divides that
count by ALL input rows in the same year, including defect-free rows. Defects
can overlap: counts and shares across defects must not be added as a total.
Every finding is ``flagged``; keep/drop decisions remain with the validator.

Rows sort by year (unknown last), then defect name. ``example_id`` is a
synthetic ordinal over sorted unique diagnostic signatures (parsed dates,
key-missing flag and normalized activity). The lowest affected signature is
selected. Equal signatures share a label, so it is an illustrative reference,
not a unique source-record identifier. It is stable under row permutation,
but may change when records are added. No well key, source index or unrelated
column contributes to it or appears in the output.

``quality_to_csv`` and ``quality_to_json`` serialize the summary in schema
order. Unknown years are empty CSV fields and JSON nulls; numeric counts and
shares retain their values. Empty summaries retain CSV headers and emit a
JSON empty array. All functions preserve their input frames.
"""

from __future__ import annotations

import json
from collections.abc import Iterable

import pandas as pd

__all__ = ["summarize_quality", "quality_to_csv", "quality_to_json"]

_INPUT_COLUMNS = (
    "API_WELL_NUMBER",
    "WAR_START_DT",
    "WAR_END_DT",
    "WELL_ACTIVITY_CD",
)
_SCHEMA = {
    "year": "Int64",
    "defect_type": "string",
    "count": "int64",
    "example_id": "string",
    "applied_rule": "string",
    "affected_share": "float64",
}
_DEFECTS = ("missing_well_key", "reversed_dates", "unknown_activity_code")


def _parse_dates(values: pd.Series) -> pd.Series:
    # Integer calendar dates can widen to floats beside nulls. String parsing
    # prevents pandas from interpreting these calendar values as epoch offsets.
    text = values.astype("string").str.strip()
    text = text.str.replace(r"^(\d+)\.0+$", r"\1", regex=True)
    return pd.to_datetime(text, errors="coerce", format="mixed", utc=True)


def summarize_quality(
    frame: pd.DataFrame, known_activity_codes: Iterable[str]
) -> pd.DataFrame:
    """Return per-year flagged defect counts and independent affected shares.

    The module docstring defines grouping, missing values, example references
    and overlap semantics. Missing input columns raise ``ValueError`` even
    for empty input; callers must supply the WAR schema. The vocabulary is
    supplied explicitly and is never inferred from the input records.
    """
    missing = [column for column in _INPUT_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"WAR frame is missing required column(s): {', '.join(missing)}"
        )

    source = frame.reset_index(drop=True)
    start = _parse_dates(source["WAR_START_DT"])
    end = _parse_dates(source["WAR_END_DT"])
    keys = source["API_WELL_NUMBER"].astype("string").str.strip()
    activity = source["WELL_ACTIVITY_CD"].astype("string").str.strip().str.upper()
    vocabulary = pd.Series(list(known_activity_codes), dtype="string")
    vocabulary = vocabulary.str.strip().str.upper().dropna()
    vocabulary = set(vocabulary[vocabulary.ne("")])
    diagnostics = pd.DataFrame(
        {
            "year": start.dt.year.astype("Int64"),
            "missing_well_key": keys.isna() | keys.eq("").fillna(False),
            "reversed_dates": start.notna() & end.notna() & end.lt(start),
            "unknown_activity_code": ~activity.isin(vocabulary),
        }
    )

    signatures = [
        json.dumps(
            [
                None if pd.isna(first) else first.isoformat(),
                None if pd.isna(last) else last.isoformat(),
                bool(missing_key),
                None if pd.isna(code) else code,
            ],
            separators=(",", ":"),
        )
        for first, last, missing_key, code in zip(
            start, end, diagnostics["missing_well_key"], activity
        )
    ]
    # Issue #1681: illustrative ordinals start at one; no source IDs are used.
    examples = {
        signature: f"record-{ordinal}"
        for ordinal, signature in enumerate(sorted(set(signatures)), start=1)
    }
    diagnostics["signature"] = signatures
    rows = []
    for year, group in diagnostics.groupby("year", dropna=False, sort=True):
        for defect in _DEFECTS:
            affected = group.loc[group[defect]]
            if affected.empty:
                continue
            rows.append(
                {
                    "year": year,
                    "defect_type": defect,
                    "count": len(affected),
                    "example_id": examples[min(affected["signature"])],
                    "applied_rule": "flagged",
                    "affected_share": len(affected) / len(group),
                }
            )
    return pd.DataFrame(rows, columns=list(_SCHEMA)).astype(_SCHEMA)


def quality_to_csv(table: pd.DataFrame) -> str:
    """Serialize a summary as CSV, with an empty field for an unknown year."""
    return table.loc[:, list(_SCHEMA)].to_csv(index=False, lineterminator="\n")


def quality_to_json(table: pd.DataFrame) -> str:
    """Serialize a summary as strict JSON records, with nullable integer years."""
    records = [
        {
            "year": None if pd.isna(row.year) else int(row.year),
            "defect_type": row.defect_type,
            "count": int(row.count),
            "example_id": row.example_id,
            "applied_rule": row.applied_rule,
            "affected_share": float(row.affected_share),
        }
        for row in table.loc[:, list(_SCHEMA)].itertuples(index=False)
    ]
    return json.dumps(records, allow_nan=False, separators=(",", ":"))
