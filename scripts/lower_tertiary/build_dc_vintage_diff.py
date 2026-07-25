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

from pathlib import Path

import pandas as pd

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


def _dev(series: pd.Series) -> pd.Series:
    return series.map(lambda x: DEV_OF_LEASE.get(str(x).strip(), str(x).strip()))


def main() -> None:
    frozen = pd.ExcelFile(FROZEN_XLSX).parse("Sheet1")
    frozen = frozen.dropna(subset=["API_WELL_NUMBER"]).copy()
    frozen["api12"] = frozen["API_WELL_NUMBER"].astype("int64").astype(str)
    cand = pd.read_csv(CANDIDATE_CSV, dtype={"API_WELL_NUMBER": str})
    cand["api12"] = cand["API_WELL_NUMBER"].str.strip()
    for df in (frozen, cand):
        df["dev"] = _dev(df["LEASE_NAME"])

    cols = ["dev", "DRILLING_DAYS", "COMPLETION_DAYS", "WELL_SPUD_DATE"]
    j = (
        frozen.set_index("api12")[cols]
        .join(
            cand.set_index("api12")[cols], lsuffix="_v30", rsuffix="_wed", how="outer"
        )
        .sort_index()
    )

    rows = []
    for api12, r in j.iterrows():
        in_v30 = pd.notna(r["dev_v30"])
        in_wed = pd.notna(r["dev_wed"])
        d_v30 = int(r["DRILLING_DAYS_v30"]) if in_v30 else 0
        c_v30 = int(r["COMPLETION_DAYS_v30"]) if in_v30 else 0
        d_wed = int(r["DRILLING_DAYS_wed"]) if in_wed else 0
        c_wed = int(r["COMPLETION_DAYS_wed"]) if in_wed else 0
        if in_v30 and in_wed:
            if pd.isna(r["WELL_SPUD_DATE_v30"]) and pd.notna(r["WELL_SPUD_DATE_wed"]):
                category = "late_data"  # placeholder row in V30, real WAR data now
            elif d_wed != d_v30:
                category = "drilling_changed"  # would falsify drilling stability
            elif c_wed != c_v30:
                category = "servicing_accrual"  # post-TD days on an old bore
            else:
                category = "unchanged"
        elif in_wed:
            category = "wed_only"
        else:
            category = "v30_only"
        rows.append(
            {
                "api12": api12,
                "dev": r["dev_wed"] if in_wed else r["dev_v30"],
                "category": category,
                "drill_v30": d_v30,
                "compl_v30": c_v30,
                "drill_wed": d_wed,
                "compl_wed": c_wed,
                "d_drill": d_wed - d_v30,
                "d_compl": c_wed - c_v30,
                "spud_wed": (
                    ""
                    if pd.isna(r["WELL_SPUD_DATE_wed"])
                    else str(r["WELL_SPUD_DATE_wed"])
                ),
            }
        )

    out = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    n_changed = (out["category"] == "drilling_changed").sum()
    print(
        f"wrote {OUT_CSV} — {len(out)} bores; "
        f"drilling_changed={n_changed} (0 = drilling days are stable), "
        f"late_data={(out['category'] == 'late_data').sum()}, "
        f"servicing_accrual={(out['category'] == 'servicing_accrual').sum()}, "
        f"wed_only={(out['category'] == 'wed_only').sum()}"
    )


if __name__ == "__main__":
    main()
