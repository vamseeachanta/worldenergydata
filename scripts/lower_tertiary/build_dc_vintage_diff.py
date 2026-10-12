#!/usr/bin/env python3
"""Diff the frozen V30 D&C workbook against the wed candidate extract, per bore.

Answers the drilling-days resolution question in the WO April 2026 QA/QC:
does any bore's DRILLING day count change between data vintages, or is all
movement new data arriving? Output is a committed CSV consumed by
``build_wo_per_well_dc.py`` (which stays stdlib-only) to render the
"Drilling-days resolution" section.

Requires pandas + openpyxl (reads the frozen ``.xlsx``); run manually when
either input changes, then re-run ``build_wo_per_well_dc.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lower_tertiary.dc_provenance import nullable_days, provenance, validate_day_schema

REPO = Path(__file__).resolve().parents[2]
V30_DIR = REPO / "docs/modules/bsee/analysis/production/FDAS_V30"
FROZEN_XLSX = V30_DIR / "drilling_and_completion_days.xlsx"
CANDIDATE_CSV = V30_DIR / "drilling_and_completion_days_v21_kc.csv"
OUT_CSV = REPO / "reports/lower_tertiary/data/dc_vintage_diff.csv"

DEV_OF_LEASE = {
    "Cascade": "Cascade Chinook",
    "Chinook": "Cascade Chinook",
    "Jack": "Jack St Malo",
    "St Malo": "Jack St Malo",
}


def _indexed(frame: pd.DataFrame) -> dict[str, dict]:
    rows = frame.dropna(subset=["API_WELL_NUMBER"]).to_dict("records")
    result = {}
    for row in rows:
        api = str(row["API_WELL_NUMBER"]).strip().removesuffix(".0")
        if api in result:
            raise ValueError("duplicate bore in vintage input")
        result[api] = row
    return result


def _comparison(old: dict, new: dict, old_basis: str, new_basis: str) -> tuple:
    if "unavailable" in (old_basis, new_basis):
        return "basis_unavailable", None, None
    if old_basis != new_basis:
        return "basis_changed", None, None
    counts = [
        nullable_days(row.get(col))
        for row in (old, new)
        for col in ("DRILLING_DAYS", "COMPLETION_DAYS")
    ]
    if any(value is None for value in counts):
        return "days_unavailable", None, None
    d_old, c_old, d_new, c_new = counts
    d, c = d_new - d_old, c_new - c_old
    category = "drilling_changed" if d else ("completion_changed" if c else "unchanged")
    return category, d, c


def build_diff(frozen: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    """Retain both bases; differences require identical, known rules and days."""
    old, new = _indexed(frozen), _indexed(candidate)
    rows = []
    for api in sorted(old.keys() | new.keys()):
        before, after = old.get(api, {}), new.get(api, {})
        meta = (
            provenance(after)
            if after
            else {
                "basis": "unavailable",
                "pnd_days": None,
                "days_status": None,
            }
        )
        basis_old = before.get("BASIS")
        basis_old = "unavailable" if pd.isna(basis_old) or not basis_old else basis_old
        category, d_drill, d_compl = _comparison(
            before, after, basis_old, meta["basis"]
        )
        if not before or not after:
            category = "wed_only" if after else "v30_only"
            d_drill = d_compl = None
        source = after or before
        lease = str(source["LEASE_NAME"]).strip()
        rows.append(
            {
                "api12": api,
                "dev": DEV_OF_LEASE.get(lease, lease),
                "category": category,
                "drill_v30": nullable_days(before.get("DRILLING_DAYS")),
                "compl_v30": nullable_days(before.get("COMPLETION_DAYS")),
                "drill_wed": nullable_days(after.get("DRILLING_DAYS")),
                "compl_wed": nullable_days(after.get("COMPLETION_DAYS")),
                "d_drill": d_drill,
                "d_compl": d_compl,
                "spud_wed": str(after.get("WELL_SPUD_DATE", "") or ""),
                "basis": basis_old if basis_old == meta["basis"] else "mixed",
                "basis_v30": basis_old,
                "basis_wed": meta["basis"],
                "pnd_days": meta["pnd_days"],
                "days_status": meta["days_status"],
            }
        )
    return _typed_diff(rows)


def _typed_diff(rows: list[dict]) -> pd.DataFrame:
    out = pd.DataFrame(rows)
    for column in (
        "drill_v30",
        "compl_v30",
        "drill_wed",
        "compl_wed",
        "d_drill",
        "d_compl",
        "pnd_days",
    ):
        out[column] = out[column].astype("Int64")
    for column in ("basis", "basis_v30", "basis_wed", "days_status"):
        out[column] = out[column].astype("string")
    validate_day_schema(out.columns)
    return out


def main() -> None:
    frozen = pd.read_excel(FROZEN_XLSX, sheet_name="Sheet1", keep_default_na=False)
    candidate = pd.read_csv(
        CANDIDATE_CSV, dtype={"API_WELL_NUMBER": str}, keep_default_na=False
    )
    out = build_diff(frozen, candidate)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(
        f"wrote {OUT_CSV} — {len(out)} bores; comparable differences require matching bases"
    )


if __name__ == "__main__":
    main()
