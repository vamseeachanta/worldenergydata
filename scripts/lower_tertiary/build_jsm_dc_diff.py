#!/usr/bin/env python3
"""Build the Jack St Malo D&C over-count diagnostic report (#846)."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from worldenergydata.lower_tertiary.jsm_dc_report import write_html  # noqa: E402
from worldenergydata.lower_tertiary.jsm_dc_sensitivity import (  # noqa: E402
    annotate_rule_sensitivity as _annotate_rule_sensitivity,
)
from worldenergydata.lower_tertiary.jsm_dc_sensitivity import (  # noqa: E402
    rule_sensitivity,
)

annotate_rule_sensitivity = _annotate_rule_sensitivity

FDAS_DIR = PROJECT_ROOT / "docs/modules/bsee/analysis/production/FDAS_V30"
EXTRACTOR = FDAS_DIR / "extract_drilling_completion_days.py"
FROZEN_WORKBOOK = FDAS_DIR / "drilling_and_completion_days.xlsx"
LEASES = FDAS_DIR / "leases_v21_kc.csv"
WAR_DIR = Path("/mnt/ace/worldenergydata/data/modules/bsee/bin/war")
WAR_MAIN = WAR_DIR / "mv_war_main.bin"
WAR_BOREHOLES = WAR_DIR / "mv_war_boreholes_view.bin"
WAR_REMARKS = WAR_DIR / "mv_war_main_prop_remark.bin"
REPORT_DIR = PROJECT_ROOT / "reports" / "lower_tertiary"
DATA_DIR = REPORT_DIR / "data"
DIFF_CSV = DATA_DIR / "jsm_dc_per_bore_diff.csv"
ACTIVITY_CSV = DATA_DIR / "jsm_post_td_activity.csv"
SENSITIVITY_CSV = DATA_DIR / "jsm_rule_sensitivity.csv"
HTML_REPORT = REPORT_DIR / "jsm_dc_diff.html"

JSM_LEASES = {"G21245", "G18753", "G18745", "G17015", "G17016", "G20394"}
EXPECTED = {
    "frozen_bores": 73,
    "candidate_bores": 73,
    "frozen_drilling_days": 2949,
    "frozen_completion_days": 3864,
    "frozen_dc_days": 6813,
    "candidate_drilling_days": 3065,
    "candidate_completion_days": 3982,
    "candidate_dc_days": 7047,
    "drilling_delta": 116,
    "completion_delta": 118,
    "dc_delta": 234,
}


def _load_extractor():
    spec = importlib.util.spec_from_file_location("fdas_extract_dc", EXTRACTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _norm_lease(value) -> str:
    text = str(value).strip().upper()
    return text if text.startswith("G") else f"G{text.zfill(5)}"


def _norm_api(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return str(int(value))
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def classify_delta(drill_delta: int, compl_delta: int) -> str:
    has_drill = drill_delta != 0
    has_compl = compl_delta != 0
    if has_drill and has_compl:
        return "BOTH"
    if has_drill:
        return "DRILL_DELTA"
    if has_compl:
        return "COMPL_DELTA"
    return "MATCH"


def filter_jsm(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["SURF_LEASE_NUM"] = out["SURF_LEASE_NUM"].map(_norm_lease)
    return out[out["SURF_LEASE_NUM"].isin(JSM_LEASES)].copy()


def build_per_bore_diff(frozen: pd.DataFrame, candidate: pd.DataFrame) -> pd.DataFrame:
    cols = ["API_WELL_NUMBER", "SURF_LEASE_NUM", "DRILLING_DAYS", "COMPLETION_DAYS"]
    left = frozen[cols].rename(
        columns={
            "API_WELL_NUMBER": "api_well_number",
            "SURF_LEASE_NUM": "surf_lease_num_frozen",
            "DRILLING_DAYS": "drill_frozen",
            "COMPLETION_DAYS": "compl_frozen",
        }
    )
    right = candidate[cols].rename(
        columns={
            "API_WELL_NUMBER": "api_well_number",
            "SURF_LEASE_NUM": "surf_lease_num_candidate",
            "DRILLING_DAYS": "drill_cand",
            "COMPLETION_DAYS": "compl_cand",
        }
    )
    left["api_well_number"] = left["api_well_number"].map(_norm_api)
    right["api_well_number"] = right["api_well_number"].map(_norm_api)
    merged = left.merge(right, on="api_well_number", how="outer", indicator=True)
    for col in ["drill_frozen", "compl_frozen", "drill_cand", "compl_cand"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int)
    merged["drill_delta"] = merged["drill_cand"] - merged["drill_frozen"]
    merged["compl_delta"] = merged["compl_cand"] - merged["compl_frozen"]
    merged["screening_status"] = [
        classify_delta(d, c)
        for d, c in zip(merged["drill_delta"], merged["compl_delta"])
    ]
    order = [
        "api_well_number",
        "surf_lease_num_frozen",
        "surf_lease_num_candidate",
        "drill_frozen",
        "drill_cand",
        "drill_delta",
        "compl_frozen",
        "compl_cand",
        "compl_delta",
        "screening_status",
        "_merge",
    ]
    return merged[order].sort_values(["screening_status", "api_well_number"])


def summarize_diff(diff: pd.DataFrame) -> dict[str, int]:
    frame = diff.copy()
    if "drill_delta" not in frame:
        frame["drill_delta"] = frame["drill_cand"] - frame["drill_frozen"]
    if "compl_delta" not in frame:
        frame["compl_delta"] = frame["compl_cand"] - frame["compl_frozen"]
    fd = int(frame["drill_frozen"].sum())
    fc = int(frame["compl_frozen"].sum())
    cd = int(frame["drill_cand"].sum())
    cc = int(frame["compl_cand"].sum())
    dd = int(frame["drill_delta"].sum())
    dc = int(frame["compl_delta"].sum())
    return {
        "frozen_bores": (
            int((frame["_merge"] != "right_only").sum())
            if "_merge" in frame
            else int(len(frame))
        ),
        "candidate_bores": (
            int((frame["_merge"] != "left_only").sum())
            if "_merge" in frame
            else int(len(frame))
        ),
        "frozen_drilling_days": fd,
        "frozen_completion_days": fc,
        "frozen_dc_days": fd + fc,
        "candidate_drilling_days": cd,
        "candidate_completion_days": cc,
        "candidate_dc_days": cd + cc,
        "drilling_delta": dd,
        "completion_delta": dc,
        "dc_delta": dd + dc,
    }


def run_extractor() -> pd.DataFrame:
    with tempfile.TemporaryDirectory(prefix="wed-846-jsm-") as tmp:
        out = Path(tmp) / "dc_days_candidate.xlsx"
        cmd = [
            sys.executable,
            str(EXTRACTOR),
            "--leases",
            str(LEASES),
            "--war-main",
            str(WAR_MAIN),
            "--war-boreholes",
            str(WAR_BOREHOLES),
            "--war-remarks",
            str(WAR_REMARKS),
            "--out",
            str(out),
        ]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            cwd=FDAS_DIR,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.decode() or proc.stdout.decode())
        return pd.read_excel(out, sheet_name="Sheet1")


def post_td_activity(diff: pd.DataFrame) -> pd.DataFrame:
    mod = _load_extractor()
    apis = set(diff.loc[diff["compl_delta"] != 0, "api_well_number"].astype(str))
    if not apis:
        return pd.DataFrame()
    wm = mod.load_war_main(WAR_MAIN)
    bh = mod.load_boreholes(WAR_BOREHOLES)
    rk = mod.load_remarks(WAR_REMARKS)
    wm = wm[wm["SURF_LEASE_NUM"].map(_norm_lease).isin(JSM_LEASES)]
    sn = wm[["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT"]].dropna(
        subset=["SN_WAR"]
    )
    rows = rk.merge(sn, on="SN_WAR", how="inner").merge(
        bh, on="API_WELL_NUMBER", how="left"
    )
    rows["API_WELL_NUMBER"] = rows["API_WELL_NUMBER"].map(_norm_api)
    rows = rows[rows["API_WELL_NUMBER"].astype(str).isin(apis)].copy()
    rows["WAR_START_DT"] = pd.to_datetime(rows["WAR_START_DT"], errors="coerce")
    rows["WAR_END_DT"] = pd.to_datetime(rows["WAR_END_DT"], errors="coerce")
    rows["TOTAL_DEPTH_DATE"] = pd.to_datetime(rows["TOTAL_DEPTH_DATE"], errors="coerce")
    rows = rows[rows["WAR_END_DT"] >= rows["TOTAL_DEPTH_DATE"]].copy()
    rows = rows.sort_values(["API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT"])
    rows["prev_end"] = rows.groupby("API_WELL_NUMBER")["WAR_END_DT"].shift()
    rows["gap_to_previous_days"] = (rows["WAR_START_DT"] - rows["prev_end"]).dt.days
    rows["is_completion_text"] = rows["TEXT_REMARK"].map(mod.is_completion_text)
    rows["text_remark_snippet"] = (
        rows["TEXT_REMARK"]
        .fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.slice(0, 220)
    )
    keep = [
        "API_WELL_NUMBER",
        "SN_WAR",
        "TOTAL_DEPTH_DATE",
        "WAR_START_DT",
        "WAR_END_DT",
        "gap_to_previous_days",
        "is_completion_text",
        "text_remark_snippet",
    ]
    return rows[keep]


def build_rule_sensitivity(all_candidate: pd.DataFrame) -> pd.DataFrame:
    return rule_sensitivity(
        all_candidate,
        extractor=_load_extractor(),
        leases=LEASES,
        war_main=WAR_MAIN,
        war_boreholes=WAR_BOREHOLES,
        war_remarks=WAR_REMARKS,
        norm_lease=_norm_lease,
        norm_api=_norm_api,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=None)
    args = parser.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frozen = filter_jsm(pd.read_excel(FROZEN_WORKBOOK, sheet_name="Sheet1"))
    all_candidate = (
        pd.read_excel(args.candidate, sheet_name="Sheet1")
        if args.candidate
        else run_extractor()
    )
    candidate = filter_jsm(all_candidate)
    diff = build_per_bore_diff(frozen, candidate)
    summary = summarize_diff(diff)
    mismatches = {
        k: (summary.get(k), v) for k, v in EXPECTED.items() if summary.get(k) != v
    }
    if mismatches:
        raise SystemExit(f"JSM headline mismatch: {mismatches}")
    diff.to_csv(DIFF_CSV, index=False)
    activity = post_td_activity(diff)
    activity.to_csv(ACTIVITY_CSV, index=False)
    sensitivity = build_rule_sensitivity(all_candidate)
    sensitivity.to_csv(SENSITIVITY_CSV, index=False)
    write_html(
        diff,
        activity,
        sensitivity,
        summary,
        HTML_REPORT,
        EXTRACTOR,
        LEASES,
        WAR_MAIN,
        WAR_BOREHOLES,
        WAR_REMARKS,
    )
    print(
        "frozen: {frozen_bores} bores / {frozen_dc_days} D&C  "
        "candidate: {candidate_bores} bores / {candidate_dc_days} D&C  "
        "delta: {dc_delta:+d} "
        "(drill {drilling_delta:+d}, completion {completion_delta:+d})".format(
            **summary
        )
    )


if __name__ == "__main__":
    main()
