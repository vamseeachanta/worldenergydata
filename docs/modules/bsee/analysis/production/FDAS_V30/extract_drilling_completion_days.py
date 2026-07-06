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
    return leases, war_main, war_bore, war_remarks

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

# ------------------ Completion logic ------------------
COMPLETION_KEYWORDS = [
    "log","logging","core","coring","rft","mdt",
    "run completion","install completion","frac","perforate","perf",
    "test","well test","flow test","cleanup","pack","packer",
    "acid","stimulation","liner hanger","toe"
]

def is_completion_text(t):
    t = str(t).lower()
    return any(k in t for k in COMPLETION_KEYWORDS)

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

def derive_completion_days(td, remarks_for_api):
    """
    Simplified rule per user request:
      - After TD, ALL rig-on-well days for the same API count as completion.
      - Ignore FO; completion can extend past FO on subsea wells.
      - NO text/keyword filtering, NO 365-day cap, NO gap cutoff beyond data itself.
      - Use SN_WAR-joined rows (with WAR_START_DT..WAR_END_DT) to count DISTINCT active days >= TD.
      - Preserve mud-weight extraction from TEXT_REMARK.
    Returns: (completion_days:int, last_activity_timestamp:Timestamp, max_mud_weight:float|nan)
    """
    if pd.isna(td) or remarks_for_api.empty:
        return 0, pd.NaT, np.nan

    r = remarks_for_api.copy()

    # Coerce date columns
    for col in ["WAR_START_DT","WAR_END_DT"]:
        if col in r.columns:
            r[col] = pd.to_datetime(r[col], errors="coerce")

    # Build the set of distinct active days from WAR intervals
    dates = []
    for _, row in r.iterrows():
        s = row.get("WAR_START_DT", pd.NaT)
        e = row.get("WAR_END_DT", pd.NaT)
        if pd.isna(s) and pd.isna(e):
            continue
        if pd.isna(s): s = e
        if pd.isna(e): e = s
        try:
            rng = pd.date_range(s.normalize(), e.normalize(), freq="D")
            dates.append(rng)
        except Exception:
            continue

    if not dates:
        return 0, pd.NaT, np.nan

    all_days = pd.DatetimeIndex(np.unique(np.concatenate(dates)))
    # Only count days after (and including) TD
    td_day = pd.to_datetime(td).normalize()
    all_days = all_days[all_days >= td_day]
    if len(all_days) == 0:
        return 0, pd.NaT, np.nan

    last = pd.to_datetime(all_days.max())

    # Preserve mud-weight extraction from remarks (if available in the script)
    mw = np.nan
    if "TEXT_REMARK" in r.columns:
        try:
            mw = extract_max_mud_weight(r["TEXT_REMARK"].astype(str).tolist())
        except Exception:
            mw = np.nan

    return int(len(all_days)), last, mw

def union_days(intervals):
    if not intervals:
        return 0
    iv = sorted([(s.normalize(), e.normalize()) for s,e in intervals if pd.notna(s) and pd.notna(e)])
    if not iv:
        return 0
    merged = []
    cs, ce = iv[0]
    for s,e in iv[1:]:
        if s <= ce:
            if e > ce:
                ce = e
        else:
            merged.append((cs, ce))
            cs, ce = s, e
    merged.append((cs, ce))
    total = sum((e - s).days for s,e in merged)
    return int(total)

# ------------------ Main ------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--leases", default=None)
    parser.add_argument("--war-main", default=None)
    parser.add_argument("--war-boreholes", default=None)
    parser.add_argument("--war-remarks", default=None)
    parser.add_argument("--out", default="drilling_and_completion_days.xlsx")  # updated filename
    args = parser.parse_args()

    cwd = os.getcwd()

    # Auto-discover if not provided
    leases_path, war_main_path, war_bore_path, war_remarks_path = autodiscover_args(cwd)
    args.leases = args.leases or leases_path
    args.war_main = args.war_main or war_main_path
    args.war_boreholes = args.war_boreholes or war_bore_path
    args.war_remarks = args.war_remarks or war_remarks_path

    missing = [name for name, path in [
        ("leases", args.leases),
        ("war-main", args.war_main),
        ("war-boreholes", args.war_boreholes),
        ("war-remarks", args.war_remarks)
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

    # Drilling days (gap-adjust if >250)
    naive = (base["TOTAL_DEPTH_DATE"] - base["WELL_SPUD_DATE"]).dt.days
    base["DRILLING_DAYS"] = naive.fillna(0).astype(int)
    long_mask = base["DRILLING_DAYS"] > 250
    if long_mask.any():
        for idx in base.index[long_mask]:
            api = base.at[idx,"API_WELL_NUMBER"]
            spud = base.at[idx,"WELL_SPUD_DATE"]
            td = base.at[idx,"TOTAL_DEPTH_DATE"]
            rapi = sn[sn["API_WELL_NUMBER"]==api]
            if rapi.empty or pd.isna(spud) or pd.isna(td):
                continue
            rapi = rapi.dropna(subset=["WAR_START_DT","WAR_END_DT"]).copy()
            rapi = rapi[(rapi["WAR_END_DT"]>=spud) & (rapi["WAR_START_DT"]<=td)]
            intervals = [(max(spud, s), min(td, e)) for s,e in zip(rapi["WAR_START_DT"], rapi["WAR_END_DT"]) if pd.notna(s) and pd.notna(e)]
            if intervals:
                base.at[idx,"DRILLING_DAYS"] = union_days(intervals)

    # Completion days via remarks text
    comp_rows = []
    for api, grp in base.groupby("API_WELL_NUMBER"):
        td = grp["TOTAL_DEPTH_DATE"].iloc[0]
        rapi = rk[rk["API_WELL_NUMBER"]==api]
        d, last, ppg = derive_completion_days(td, rapi)
        comp_rows.append((api,d,last,ppg))
    comp_df = pd.DataFrame(comp_rows, columns=["API_WELL_NUMBER","COMPLETION_DAYS","LAST_COMPLETION_ACTIVITY","MAX_DRILL_FLUID_WGT"])
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
        "DRILLING_DAYS":        base["DRILLING_DAYS"].astype("Int64"),
        "COMPLETION_DAYS":      base["COMPLETION_DAYS"].fillna(0).astype("Int64"),
        "MAX_BH_TOTAL_MD":      base["MAX_BH_TOTAL_MD"],
        "MAX_WELL_BORE_TVD":    base["MAX_WELL_BORE_TVD"],
        "MAX_DRILL_FLUID_WGT":  base["MAX_DRILL_FLUID_WGT"],
    })

    with pd.ExcelWriter(args.out, engine="openpyxl") as xw:
        out.to_excel(xw, sheet_name="Sheet1", index=False)
        leases.to_excel(xw, sheet_name="Lease_List", index=False)
        diag = base[["API_WELL_NUMBER","WELL_SPUD_DATE","TOTAL_DEPTH_DATE","DRILLING_DAYS","COMPLETION_DAYS","LAST_COMPLETION_ACTIVITY","MAX_DRILL_FLUID_WGT"]]
        diag.to_excel(xw, sheet_name="Diagnostics", index=False)

    print(f"✅ Wrote {args.out} with {len(out)} rows.")

if __name__ == "__main__":
    main()
