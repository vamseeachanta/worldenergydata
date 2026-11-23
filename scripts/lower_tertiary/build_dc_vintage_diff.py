#!/usr/bin/env python3
"""Diff the frozen V30 D&C workbook against the wed candidate extract, per bore.

Answers the drilling-days resolution question in the WO April 2026 QA/QC:
does any bore's DRILLING day count change between data vintages, or is all
movement new data arriving? Output is a committed CSV consumed by
``build_wo_per_well_dc.py`` (which stays stdlib-only) to render the
"Drilling-days resolution" section.

Requires pandas + openpyxl (reads the frozen ``.xlsx``); run manually when
either input changes. Publication requires a digest-bound frozen sidecar and
labelled candidate. Cross-rule differences do not establish drilling stability;
``same_basis`` identifies whether the recorded rules agree.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lower_tertiary.dc_provenance import (
    carries_basis,
    provenance,
    validate_day_schema,
    vintage_labels,
)
from lower_tertiary.frozen_dc_metadata import load_frozen

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


def build_diff(frozen: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """Retain MB comparisons and append labels only for basis-bearing inputs."""
    labelled = carries_basis(frozen.columns) or carries_basis(cand.columns)
    cand = cand.copy()
    frozen = frozen.dropna(subset=["API_WELL_NUMBER"]).copy()
    frozen["api12"] = frozen["API_WELL_NUMBER"].astype("int64").astype(str)
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
    if labelled:
        labels = pd.DataFrame(vintage_labels(frozen, cand, out["api12"]))
        validate_day_schema(labels.columns)
        labels["pnd_days"] = labels["pnd_days"].astype("Int64")
        for column in ("basis", "basis_v30", "basis_wed", "days_status"):
            labels[column] = labels[column].astype("string")
        out = pd.concat([out, labels], axis=1)
        validate_day_schema(out.columns)
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--frozen-metadata",
        type=Path,
        help="Digest-bound JSON sidecar; defaults to the workbook's provenance.json",
    )
    args = parser.parse_args(argv)
    frozen = load_frozen(FROZEN_XLSX, args.frozen_metadata)
    cand = pd.read_csv(CANDIDATE_CSV, dtype={"API_WELL_NUMBER": str})
    # Publication contract: issue #1633, acceptance; archived unknown coverage
    # is allowed only through the digest-bound frozen loader, never inferred.
    required = {"BASIS", "PND_DAYS", "DAYS_STATUS"}
    if not required.issubset(cand.columns) or cand.empty:
        raise ValueError("candidate requires recorded provenance")
    statuses = {"war_covered", "no_war_activity", "war_covered_no_activity_code"}
    for row in cand.to_dict("records"):
        provenance(row)
        if row["DAYS_STATUS"] not in statuses:
            raise ValueError("unsupported candidate coverage provenance")
    out = build_diff(frozen, cand)
    for suffix, frame in (("v30", frozen), ("wed", cand)):
        labels = {
            str(row["API_WELL_NUMBER"]).strip().removesuffix(".0"): provenance(row)
            for row in frame.dropna(subset=["API_WELL_NUMBER"]).to_dict("records")
        }
        absent = "wed_only" if suffix == "v30" else "v30_only"
        present = out["category"].ne(absent)
        if out.loc[present, f"basis_{suffix}"].isna().any():
            raise ValueError("present vintage side requires recorded provenance")
        for column in ("pnd_days", "days_status"):
            out[f"{column}_{suffix}"] = [
                labels.get(api, {}).get(column) for api in out["api12"]
            ]
        out[f"pnd_days_{suffix}"] = out[f"pnd_days_{suffix}"].astype("Int64")
        out[f"days_status_{suffix}"] = out[f"days_status_{suffix}"].astype("string")
    # Keep legacy numeric differences for existing consumers; this flag marks
    # whether they compare two present sides on the same recorded rule.
    out["same_basis"] = (
        out["basis_v30"].notna()
        & out["basis_wed"].notna()
        & out["basis_v30"].eq(out["basis_wed"])
    ).fillna(False)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    n_changed = (out["category"] == "drilling_changed").sum()
    print(
        f"wrote {OUT_CSV} — {len(out)} bores; "
        f"drilling_changed={n_changed}, "
        f"same_basis={out['same_basis'].sum()} (cross-rule counts are archival), "
        f"late_data={(out['category'] == 'late_data').sum()}, "
        f"servicing_accrual={(out['category'] == 'servicing_accrual').sum()}, "
        f"wed_only={(out['category'] == 'wed_only').sum()}"
    )


if __name__ == "__main__":
    main()
