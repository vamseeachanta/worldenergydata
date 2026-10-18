#!/usr/bin/env python3
"""
Portable Drilling + Completion extract (OGORA removed)
=====================================================

Drop this script into ANY project folder (e.g., Lower Tertiary) and run:
  python extract_drilling_completion_days.py

It will AUTO-DISCOVER the required inputs in the current directory:

Required (auto-discovered by default):
- leases: leases*.xlsx|csv (prefers leases.xlsx)
- mv_war_main: mv_war_main*.txt
- mv_war_boreholes: mv_war_boreholes_view*.txt
- mv_war_remarks: mv_war_main_prop_remark*.txt

Override discovery with flags if needed:
  python extract_drilling_completion_days.py \
    --leases my_leases.xlsx \
    --war-main my_mv_war_main.txt \
    --war-boreholes my_mv_war_boreholes_view.txt \
    --war-remarks my_mv_war_main_prop_remark.txt \
    --out drilling_and_completion_days.xlsx

Outputs:
- Excel workbook (default 'drilling_and_completion_days.xlsx')
  Columns (sorted):
    LEASE_NAME, SURF_LEASE_NUM, WATER_DEPTH, API_WELL_NUMBER, WELL_NAME,
    WELL_SPUD_DATE, TOTAL_DEPTH_DATE, DRILLING_DAYS, COMPLETION_DAYS,
    MAX_BH_TOTAL_MD, MAX_WELL_BORE_TVD, MAX_DRILL_FLUID_WGT
  Tabs: Sheet1 (data), Lease_List, Diagnostics

Requires: Python 3.9+, pandas, openpyxl, numpy
"""

import argparse, re, sys, os
from pathlib import Path
import numpy as np
import pandas as pd

# Drilling and completion days come from the shared war_rig_days module -- this
# script no longer derives them (#1067/#1075). The bootstrap below makes the
# import resolve from whichever checkout this file lives in, rather than from
# whichever checkout happens to be editable-installed in the active venv. The
# script is invoked by subprocess with cwd set to its own directory and no
# PYTHONPATH, so relying on the install would silently bind a worktree run to
# a different tree's copy of the module.
_REPO_ROOT = Path(__file__).resolve().parents[6]
for _pkg in ("packages/worldenergydata-bsee/src", "packages/worldenergydata-core/src", "src"):
    _p = str(_REPO_ROOT / _pkg)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from worldenergydata.bsee.analysis.war_rig_days import (  # noqa: E402
    BASIS_DRL_COM,
    PRESET_BASES,
    rig_days_by_bore,
)

pd.options.mode.copy_on_write = True
DATE_FMT_OUT = "%m/%d/%Y"

# ------------------ Utilities ------------------
def parse_dt(x):
    return pd.to_datetime(x, errors="coerce")

def normalize_lease(s):
    if pd.isna(s):
        return None
    s = str(s).strip().upper()
    return s[1:] if s.startswith("G") else s

def normalize_api(x):
    if pd.isna(x):
        return None
    s = str(x).strip()
    s = re.sub(r"\.0$","",s)
    return s

def find_one(patterns, cwd):
    for pat in patterns:
        matches = sorted(Path(cwd).glob(pat))
        if matches:
            return str(matches[0])
    return None

def autodiscover_args(cwd):
    leases = find_one(["leases.xlsx", "leases_*.xlsx", "leases.csv", "leases_*.csv"], cwd)
    war_main = find_one(["mv_war_main.txt", "mv_war_main_*.txt"], cwd)
    war_bore = find_one(["mv_war_boreholes_view.txt", "mv_war_boreholes_view_*.txt"], cwd)
    war_remarks = find_one(["mv_war_main_prop_remark.txt", "mv_war_main_prop_remark_*.txt"], cwd)
    # mv_war_main_prop carries WELL_ACTIVITY_CD and is the reason days can be
    # attributed to drilling vs completion at all. Discovered after the remark
    # patterns so the longer "…_prop_remark…" name cannot be matched here.
    war_prop = find_one(["mv_war_main_prop.txt", "mv_war_main_prop_[!r]*.txt"], cwd)
    return leases, war_main, war_bore, war_remarks, war_prop

# ------------------ Loaders ------------------
def load_leases(path):
    p = Path(path)
    if p.suffix.lower() in (".xlsx",".xls"):
        df = pd.read_excel(p)
    else:
        df = pd.read_csv(p)

    cols = {c.upper(): c for c in df.columns}
    num_col = cols.get("LEASE_NUM") or cols.get("SURF_LEASE_NUM") or cols.get("LEASE_NUMBER")
    name_col = cols.get("LEASE_NAME")
    dev_col = cols.get("DEV_NAME")
    wd_col = cols.get("WATER_DEPTH")

    if not num_col:
        raise ValueError("leases file must include LEASE_NUM (e.g., G09868).")

    df["_LEASE_NUM_NORM"] = (
        df[num_col].astype(str).str.strip().str.upper().str.replace(r"^G","",regex=True)
    )

    keep = ["_LEASE_NUM_NORM"]
    if name_col: keep.append(name_col)
    if wd_col: keep.append(wd_col)
    if dev_col: keep.append(dev_col)

    out = df[keep].rename(columns={name_col:"LEASE_NAME", wd_col:"LEASE_WATER_DEPTH", dev_col:"DEV_NAME"})
    return out

def load_war_main(path):
    # Raw BSEE WAR is distributed as pickled DataFrames (.bin) on the data share and
    # as delimited text (.txt) in exports; both carry the same raw columns, so read
    # either and let the column-mapping below normalise. One canonical extractor.
    if str(path).lower().endswith(".bin"):
        df = pd.read_pickle(path)
    else:
        df = pd.read_csv(path, encoding="ISO-8859-1", on_bad_lines="skip", low_memory=False)
    C = {c.upper(): c for c in df.columns}

    api   = C.get("API_WELL_NUMBER") or C.get("API_NUMBER") or C.get("API")
    lease = C.get("SURF_LEASE_NUM")  or C.get("LEASE_NUM")  or C.get("SURF_LEASE")
    name  = C.get("WELL_NAME")       or C.get("WELL_NM")
    start = C.get("WAR_START_DT"); end = C.get("WAR_END_DT")
    wd    = C.get("WATER_DEPTH")

    if not api or not lease:
        raise ValueError("mv_war_main must include API_WELL_NUMBER and SURF_LEASE_NUM (or equivalents).")

    out = pd.DataFrame({
        "SN_WAR":          pd.to_numeric(df.get(C.get("SN_WAR")), errors="coerce"),
        "WAR_START_DT":    parse_dt(df.get(start)),
        "WAR_END_DT":      parse_dt(df.get(end)),
        "API_WELL_NUMBER": df[api].apply(normalize_api),
        "SURF_LEASE_NUM":  df[lease].apply(lambda x: normalize_lease(x)),
        "WELL_NAME":       df[name] if name else None,
        "WATER_DEPTH":     pd.to_numeric(df[wd], errors="coerce") if wd else np.nan,
        "LEASE_NAME":      df.get(C.get("LEASE_NAME"))
    })
    return out

def load_war_prop(path):
    """SN_WAR -> WELL_ACTIVITY_CD, the activity attribution for each WAR week."""
    if str(path).lower().endswith(".bin"):
        df = pd.read_pickle(path)
    else:
        df = pd.read_csv(path, encoding="ISO-8859-1", on_bad_lines="skip", low_memory=False)
    C = {c.upper(): c for c in df.columns}

    sn = C.get("SN_WAR")
    code = C.get("WELL_ACTIVITY_CD")
    if not sn or not code:
        raise ValueError(
            "mv_war_main_prop must include SN_WAR and WELL_ACTIVITY_CD; "
            f"found columns: {', '.join(sorted(C))[:200]}"
        )

    return pd.DataFrame({
        "SN_WAR": pd.to_numeric(df[sn], errors="coerce"),
        "WELL_ACTIVITY_CD": df[code],
    }).dropna(subset=["SN_WAR"])


def infer_prop_path(remarks_path):
    """mv_war_main_prop sits beside mv_war_main_prop_remark in every BSEE drop.

    Callers predating the activity-code basis pass only the remarks file, so
    infer its sibling rather than failing on an argument that did not exist
    when they were written. Returns None if the sibling is absent -- the
    caller reports that as a missing required input rather than proceeding
    without an activity attribution.
    """
    if not remarks_path:
        return None
    p = Path(remarks_path)
    name = p.name.replace("_prop_remark", "_prop")
    candidate = p.with_name(name)
    return str(candidate) if candidate.exists() else None


def load_boreholes(path):
    if str(path).lower().endswith(".bin"):
        df = pd.read_pickle(path)
    else:
        df = pd.read_csv(path, encoding="ISO-8859-1", on_bad_lines="skip", low_memory=False)
    C = {c.upper(): c for c in df.columns}

    api = C.get("API_WELL_NUMBER") or C.get("API")
    spud = C.get("WELL_SPUD_DATE"); td = C.get("TOTAL_DEPTH_DATE")
    md = C.get("BH_TOTAL_MD") or C.get("MAX_BH_TOTAL_MD")
    tvd = C.get("WELL_BORE_TVD") or C.get("MAX_WELL_BORE_TVD")

    if not api:
        raise ValueError("mv_war_boreholes_view must include API_WELL_NUMBER.")

    out = pd.DataFrame({
        "API_WELL_NUMBER":    df[api].apply(normalize_api),
        "WELL_SPUD_DATE":     parse_dt(df.get(spud)),
        "TOTAL_DEPTH_DATE":   parse_dt(df.get(td)),
        "MAX_BH_TOTAL_MD":    pd.to_numeric(df.get(md), errors="coerce"),
        "MAX_WELL_BORE_TVD":  pd.to_numeric(df.get(tvd), errors="coerce"),
    })

    out = (
        out.sort_values(["API_WELL_NUMBER","MAX_BH_TOTAL_MD"], na_position="last")
           .groupby("API_WELL_NUMBER", as_index=False)
           .agg({
               "WELL_SPUD_DATE":"min",
               "TOTAL_DEPTH_DATE":"max",
               "MAX_BH_TOTAL_MD":"max",
               "MAX_WELL_BORE_TVD":"max"
           })
    )
    return out

def load_remarks(path):
    if str(path).lower().endswith(".bin"):
        df = pd.read_pickle(path)
        cols = {c.upper(): c for c in df.columns}
        df = df.rename(columns={cols.get("SN_WAR", "SN_WAR"): "SN_WAR",
                                cols.get("TEXT_REMARK", "TEXT_REMARK"): "TEXT_REMARK"})
    else:
        df = pd.read_csv(
            path, encoding="ISO-8859-1",
            header=None, names=["SN_WAR","TEXT_REMARK"],
            on_bad_lines="skip", low_memory=False
        )
    df = df[df["SN_WAR"].astype(str).str.upper()!="SN_WAR"].copy()
    df["SN_WAR"] = pd.to_numeric(df["SN_WAR"], errors="coerce")
    df = df.dropna(subset=["SN_WAR"])
    df["TEXT_REMARK"] = df["TEXT_REMARK"].astype(str)
    return df

# ------------------ Remarks-derived narrative fields ------------------
# COMPLETION_KEYWORDS / is_completion_text lived here and were dead: nothing
# called them, and completion days were never derived from remark text despite
# comments in this file saying so. Removed with the day derivation itself.

def extract_max_mud_weight(texts):
    mx = np.nan
    pat = re.compile(r'(\d{1,2}(?:\.\d+)?)\s*ppg', re.I)
    for t in texts:
        for m in pat.finditer(str(t)):
            try:
                v = float(m.group(1))
                mx = v if (np.isnan(mx) or v>mx) else mx
            except:
                pass
    return mx

def last_activity_and_mud_weight(remarks_for_api):
    """Narrative fields from the remarks join: last activity date, max mud weight.

    This function used to also return completion days, counted as every
    distinct rig-day at or after TD with no activity filter and no right
    bound -- so a workover a decade later was billed as completion. Worse,
    it was fed by a LEFT JOIN on remarks, so a WAR week carrying no remark
    text contributed zero completion days while still contributing to
    drilling. Days now come from war_rig_days; only the narrative survives.
    """
    if remarks_for_api.empty:
        return pd.NaT, np.nan

    r = remarks_for_api.copy()
    for col in ("WAR_START_DT", "WAR_END_DT"):
        if col in r.columns:
            r[col] = pd.to_datetime(r[col], errors="coerce")

    ends = r["WAR_END_DT"].dropna() if "WAR_END_DT" in r.columns else pd.Series(dtype="datetime64[ns]")
    last = ends.max() if len(ends) else pd.NaT

    mw = np.nan
    if "TEXT_REMARK" in r.columns:
        try:
            mw = extract_max_mud_weight(r["TEXT_REMARK"].astype(str).tolist())
        except Exception:
            mw = np.nan

    return last, mw

# union_days() lived here. It failed to merge back-to-back WAR weeks (Jan 1-7
# plus Jan 8-14 summed to 12 days, not 14) and counted exclusively while
# completion counted inclusively. Both are fixed in war_rig_days.union_days,
# which merges adjacency and normalises to midnight before counting.

# ------------------ Main ------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leases", default=None)
    parser.add_argument("--war-main", default=None)
    parser.add_argument("--war-boreholes", default=None)
    parser.add_argument("--war-remarks", default=None)
    parser.add_argument("--war-prop", default=None,
                        help="mv_war_main_prop (WELL_ACTIVITY_CD). Inferred from "
                             "--war-remarks when omitted.")
    parser.add_argument("--basis", default=BASIS_DRL_COM.label, choices=sorted(PRESET_BASES),
                        help="Which activity codes constitute drilling and completion.")
    parser.add_argument("--out", default="drilling_and_completion_days.xlsx")  # updated filename
    args = parser.parse_args()

    cwd = os.getcwd()

    # Auto-discover if not provided
    (leases_path, war_main_path, war_bore_path,
     war_remarks_path, war_prop_path) = autodiscover_args(cwd)
    args.leases = args.leases or leases_path
    args.war_main = args.war_main or war_main_path
    args.war_boreholes = args.war_boreholes or war_bore_path
    args.war_remarks = args.war_remarks or war_remarks_path
    args.war_prop = args.war_prop or war_prop_path or infer_prop_path(args.war_remarks)

    missing = [name for name, path in [
        ("leases", args.leases),
        ("war-main", args.war_main),
        ("war-boreholes", args.war_boreholes),
        ("war-remarks", args.war_remarks),
        ("war-prop", args.war_prop),
    ] if not path or not os.path.exists(path)]
    if missing:
        raise SystemExit(f"Missing required inputs: {', '.join(missing)}. "
                         f"Run with --help or place files in the current directory.")

    leases = load_leases(args.leases)
    wm = load_war_main(args.war_main)
    bh = load_boreholes(args.war_boreholes)
    rk = load_remarks(args.war_remarks)

    # Filter by leases
    wm = wm[wm["SURF_LEASE_NUM"].isin(leases["_LEASE_NUM_NORM"])].copy()

    # SN_WAR map for remarks
    sn = wm[["SN_WAR","API_WELL_NUMBER","WAR_START_DT","WAR_END_DT"]].dropna(subset=["SN_WAR"]).copy()
    rk = rk.merge(sn, on="SN_WAR", how="left").dropna(subset=["API_WELL_NUMBER"])

    # Base per API
    base = (wm.groupby("API_WELL_NUMBER", as_index=False)
              .agg({"SURF_LEASE_NUM":"first","WELL_NAME":"first","WATER_DEPTH":"max","LEASE_NAME":"first"}))
    base = base.merge(bh, on="API_WELL_NUMBER", how="left")

    # Authoritative lease name/depth from leases.xlsx
    base = base.merge(leases.rename(columns={"_LEASE_NUM_NORM":"SURF_LEASE_NUM"}),
                      on="SURF_LEASE_NUM", how="left", suffixes=("","_LEASE"))
    base["LEASE_NAME"] = base["LEASE_NAME"].fillna(base["LEASE_NAME_LEASE"])
    base["WATER_DEPTH"] = np.where(base["LEASE_WATER_DEPTH"].notna(), base["LEASE_WATER_DEPTH"], base["WATER_DEPTH"])

    # Drilling and completion days from WAR activity codes.
    #
    # Both were previously derived here: drilling as a calendar spud->TD span
    # (switching to a WAR union above an undocumented 250-day threshold), and
    # completion as every rig-day after TD forever, fed by a remarks join so
    # WARs lacking a remark contributed nothing. Neither measured rig time.
    # The shared module replaces both; the 250-day branch is gone rather than
    # retuned, because it was an artifact of the wrong basis.
    basis = PRESET_BASES[args.basis]
    # LEFT, not inner. mv_war_main_prop does not cover every SN_WAR in
    # mv_war_main -- 2,030 weeks on the 2026-02-19 vintage, 280 of them inside
    # this population. An inner join discarded them silently, and for 38 bores
    # that was EVERY week they have, so a bore with 32 weeks of recorded rig
    # presence was published as having no WAR activity at all. Those weeks are
    # unattributed, not absent; war_rig_days carries them as coverage and
    # excludes them from every activity total. See #1120.
    prop = load_war_prop(args.war_prop)
    war_for_days = wm[["SN_WAR", "API_WELL_NUMBER", "WAR_START_DT", "WAR_END_DT"]].merge(
        prop, on="SN_WAR", how="left"
    )
    unattributed = int(war_for_days["WELL_ACTIVITY_CD"].isna().sum())
    if unattributed:
        print(
            f"  {unattributed} of {len(war_for_days)} WAR weeks carry no activity "
            f"code; counted as coverage, excluded from activity totals."
        )
    days = rig_days_by_bore(
        war_for_days, basis=basis, population=list(base["API_WELL_NUMBER"])
    ).rename(columns={
        "api12": "API_WELL_NUMBER",
        "drilling_days": "DRILLING_DAYS",
        "completion_days": "COMPLETION_DAYS",
        "pnd_days": "PND_DAYS",
        "days_status": "DAYS_STATUS",
        "basis": "BASIS",
    })
    base = base.merge(
        days[["API_WELL_NUMBER", "DRILLING_DAYS", "COMPLETION_DAYS",
              "PND_DAYS", "DAYS_STATUS", "BASIS"]],
        on="API_WELL_NUMBER", how="left",
    )

    # Remarks still supply the narrative fields, but no longer any day count.
    comp_rows = []
    for api, grp in base.groupby("API_WELL_NUMBER"):
        rapi = rk[rk["API_WELL_NUMBER"] == api]
        last, ppg = last_activity_and_mud_weight(rapi)
        comp_rows.append((api, last, ppg))
    comp_df = pd.DataFrame(
        comp_rows,
        columns=["API_WELL_NUMBER", "LAST_COMPLETION_ACTIVITY", "MAX_DRILL_FLUID_WGT"],
    )
    base = base.merge(comp_df, on="API_WELL_NUMBER", how="left")

    # Sort and output
    base = base.sort_values(by=["LEASE_NAME","WELL_NAME","WELL_SPUD_DATE"], ascending=[True,True,True])

    out = pd.DataFrame({
        "LEASE_NAME":           base["LEASE_NAME"],
        "SURF_LEASE_NUM":       base["SURF_LEASE_NUM"].apply(lambda x: f"G{int(x):05d}" if pd.notna(x) and str(x).isdigit() else ("G"+str(x) if x and not str(x).upper().startswith("G") else x)),
        "WATER_DEPTH":          base["WATER_DEPTH"],
        "API_WELL_NUMBER":      base["API_WELL_NUMBER"],
        "WELL_NAME":            base["WELL_NAME"],
        "WELL_SPUD_DATE":       base["WELL_SPUD_DATE"].dt.strftime(DATE_FMT_OUT),
        "TOTAL_DEPTH_DATE":     base["TOTAL_DEPTH_DATE"].dt.strftime(DATE_FMT_OUT),
        # No fillna(0) on either column. A bore with no WAR coverage is not a
        # bore that took zero days, and rendering it as 0 is what made 38 of
        # 253 bores indistinguishable from genuine zero-day results.
        "DRILLING_DAYS":        base["DRILLING_DAYS"].astype("Int64"),
        "COMPLETION_DAYS":      base["COMPLETION_DAYS"].astype("Int64"),
        "PND_DAYS":             base["PND_DAYS"].astype("Int64"),
        "MAX_BH_TOTAL_MD":      base["MAX_BH_TOTAL_MD"],
        "MAX_WELL_BORE_TVD":    base["MAX_WELL_BORE_TVD"],
        "MAX_DRILL_FLUID_WGT":  base["MAX_DRILL_FLUID_WGT"],
        # Every row states the rule that produced it, so no consumer can mix
        # two bases without noticing.
        "DAYS_STATUS":          base["DAYS_STATUS"],
        "BASIS":                base["BASIS"],
    })

    with pd.ExcelWriter(args.out, engine="openpyxl") as xw:
        out.to_excel(xw, sheet_name="Sheet1", index=False)
        leases.to_excel(xw, sheet_name="Lease_List", index=False)
        diag = base[["API_WELL_NUMBER","WELL_SPUD_DATE","TOTAL_DEPTH_DATE","DRILLING_DAYS","COMPLETION_DAYS","LAST_COMPLETION_ACTIVITY","MAX_DRILL_FLUID_WGT"]]
        diag.to_excel(xw, sheet_name="Diagnostics", index=False)

    print(f"✅ Wrote {args.out} with {len(out)} rows.")

if __name__ == "__main__":
    main()
