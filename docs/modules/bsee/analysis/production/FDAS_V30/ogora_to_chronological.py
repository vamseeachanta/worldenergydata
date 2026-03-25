#!/usr/bin/env python3
"""
OGOR-A → Chronological Lease Analysis (V23_001)
===============================================
Directly build `chronological_lease_analysis.xlsx` **from raw OGOR-A zip files**,
merging the best parts of the legacy OGOR reader (unzipping, robust parsing) and
the chrono builder (long-form monthly output with optional D&C/WTI joins).

Outputs a single long-form sheet with one row per API × Month:
  LEASE_NAME | WELL_NAME | API_WELL_NUMBER | MONTH |
  MONTHLY_OIL_VOLUME | MONTHLY_WATER_VOLUME | DAYS_ON_PROD |
  ALLOCATED_DRILLING_DAYS | ALLOCATED_COMPLETION_DAYS | AVG_BBLS_PER_DAY |
  WTI_USD | MONTHLY_REVENUE_USD | (optional) DEV_NAME | DEV_SYSTEM

Usage examples
--------------
python ogor_to_chronological_v23_001.py \
  --dir ./ogor \
  --leases leases.xlsx \
  --pattern "ogora20??delimit.zip" \
  --dnc drilling_and_completion_days.xlsx \
  --wti wti_monthly.csv \
  --out chronological_lease_analysis.xlsx

Notes
-----
• Reads OGOR text/CSV inside zips using encoding='ISO-8859-1'.
• Expects 19 OGOR columns (LEASE_NUM, WELL_COMPLETION_ID, PROD_YEARMONTH, DAYS_ON,
  PRODUCT_CODE, OIL_PROD, GAS_PROD, COND_PROD, API_WELL_NUMBER, ...).
• Water is derived as WATER_PROD if present; if absent in source files, defaults to 0.
• Leases file (xlsx/csv) provides LEASE_NUM→LEASE_NAME (and optionally DEV_NAME/DEV_SYSTEM).
• D&C days and WTI price inputs are optional; joined by MONTH (and API for D&C).
"""

from __future__ import annotations
import argparse
import io
import os
import re
import glob
import zipfile
from collections import defaultdict
from typing import Optional

import numpy as np
import pandas as pd

# ----------------------------- Constants -----------------------------
OGORA_COLS = [
    'LEASE_NUM', 'WELL_COMPLETION_ID', 'PROD_YEARMONTH', 'DAYS_ON', 'PRODUCT_CODE',
    'OIL_PROD', 'GAS_PROD', 'COND_PROD', 'API_WELL_NUMBER', 'FIELD10',
    'BLOCK_DESC', 'FIELD12', 'OPERATOR_NAME', 'BLOCK_CODE', 'FIELD15',
    'SUFFIX', 'SPUD_DATE', 'ENTITY_ID', 'STATUS'
]

# ----------------------------- Helpers -----------------------------

def normalize_lease_num(val: str) -> str:
    s = str(val).strip().upper()
    m = re.fullmatch(r"G?(\d+)", s)
    return "G" + m.group(1) if m else s

def month_from_yyyymm(s: str) -> pd.Timestamp:
    s = re.sub(r"\D", "", str(s) or "")
    if len(s) < 6:
        return pd.NaT
    y = int(s[:4])
    m = int(s[4:6]) if len(s) >= 6 else 1
    m = min(max(m, 1), 12)
    return pd.Timestamp(year=y, month=m, day=1)

def choose_excel_engine() -> str:
    try:
        import xlsxwriter  # noqa: F401
        return "xlsxwriter"
    except ModuleNotFoundError:
        try:
            import openpyxl  # noqa: F401
            return "openpyxl"
        except ModuleNotFoundError:
            return "xlsxwriter"  # best-effort

# ----------------------------- Loaders -----------------------------

def load_leases_with_names(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    elif ext == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        raise ValueError("leases file must be .xlsx, .xls, or .csv")

    df.columns = df.columns.str.upper().str.strip()

    # Try common variants for lease number & name
    lease_num_col  = next((c for c in df.columns if "LEASE" in c and ("NUM" in c or "NO" in c or c.endswith("#"))), None)
    if lease_num_col is None:
        lease_num_col = df.columns[0]
    lease_name_col = next((c for c in df.columns if "LEASE" in c and "NAME" in c), lease_num_col)

    out = pd.DataFrame({
        "LEASE_NUM":  df[lease_num_col].map(normalize_lease_num),
        "LEASE_NAME": df[lease_name_col].astype(str).str.strip().fillna("")
    })

    # Optional dev mapping
    for col in ("DEV_NAME", "DEV_SYSTEM"):
        if col in df.columns:
            out[col] = df[col].astype(str).str.strip()
        else:
            out[col] = ""

    # Normalized keys for robust joins later
    out["LEASE_NAME_KEY"] = out["LEASE_NAME"].str.upper().str.strip()
    return out.drop_duplicates("LEASE_NUM")

def read_ogor_zip(zip_path: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as z:
        inner = [n for n in z.namelist() if n.lower().endswith((".txt", ".csv"))]
        if not inner:
            raise ValueError(f"No .txt/.csv found inside {zip_path}")
        with z.open(inner[0]) as f:
            df = pd.read_csv(
                io.TextIOWrapper(f, encoding="ISO-8859-1"),
                header=None, dtype=str, quotechar='"'
            )
    # pad/truncate to expected column count
    if df.shape[1] < len(OGORA_COLS):
        for _ in range(len(OGORA_COLS) - df.shape[1]):
            df[df.shape[1]] = None
    elif df.shape[1] > len(OGORA_COLS):
        df = df.iloc[:, :len(OGORA_COLS)]
    df.columns = OGORA_COLS
    return df

# ----------------------------- D&C and WTI -----------------------------

def allocate_dnc_by_month(dnc_path: Optional[str]) -> pd.DataFrame:
    if not dnc_path or not os.path.exists(dnc_path):
        return pd.DataFrame(columns=["API_WELL_NUMBER","MONTH","ALLOCATED_DRILLING_DAYS","ALLOCATED_COMPLETION_DAYS"])
    d = pd.read_excel(dnc_path)
    d.columns = d.columns.str.upper().str.strip().str.replace(" ", "_", regex=False)
    for c in ("WELL_SPUD_DATE","TOTAL_DEPTH_DATE","LAST_COMPLETION_ACTIVITY"):
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], errors="coerce")
    if "LAST_COMPLETION_ACTIVITY" not in d.columns:
        d["LAST_COMPLETION_ACTIVITY"] = d["TOTAL_DEPTH_DATE"] + pd.to_timedelta(d.get("COMPLETION_DAYS", 0), unit="D")

    def alloc_months(start, end, total):
        if pd.isna(start) or pd.isna(end) or not pd.notna(total):
            return {}
        rng = pd.date_range(start=start, end=end, freq="D")
        if len(rng) == 0:
            rng = pd.DatetimeIndex([pd.to_datetime(start).normalize()])
        buckets = defaultdict(int)
        for dte in rng:
            buckets[pd.Timestamp(dte.year, dte.month, 1)] += 1
        tot = sum(buckets.values()) or 1
        return {k: round(v * float(total) / tot) for k, v in buckets.items()}

    rows = []
    for _, r in d.iterrows():
        api = pd.to_numeric(r.get("API_WELL_NUMBER", np.nan), errors="coerce")
        d_days = r.get("DRILLING_DAYS", 0)
        c_days = r.get("COMPLETION_DAYS", 0)
        spud = r.get("WELL_SPUD_DATE")
        td   = r.get("TOTAL_DEPTH_DATE")
        last = r.get("LAST_COMPLETION_ACTIVITY")
        if pd.isna(api):
            continue
        drill = alloc_months(spud, td, d_days) if pd.notna(d_days) and d_days else {}
        comp  = alloc_months(td, last, c_days) if pd.notna(c_days) and c_days else {}
        months = set(drill) | set(comp)
        for m in months:
            rows.append({
                "API_WELL_NUMBER": float(api),
                "MONTH": pd.to_datetime(m).to_period("M").to_timestamp(),
                "ALLOCATED_DRILLING_DAYS": drill.get(m, 0),
                "ALLOCATED_COMPLETION_DAYS": comp.get(m, 0),
            })
    out = pd.DataFrame(rows)
    if not out.empty:
        out["API_WELL_NUMBER"] = pd.to_numeric(out["API_WELL_NUMBER"], errors="coerce")
        out["MONTH"] = pd.to_datetime(out["MONTH"]).dt.to_period("M").dt.to_timestamp()
    return out

def load_wti_monthly(wti_path: Optional[str]) -> pd.DataFrame:
    if not wti_path or not os.path.exists(wti_path):
        return pd.DataFrame(columns=["MONTH","WTI_USD"])
    df = pd.read_csv(wti_path)
    # Accept Month/DATE variants
    date_col = next((c for c in df.columns if str(c).strip().upper() in {"MONTH","DATE"}), None)
    if not date_col:
        raise ValueError("wti_monthly.csv must include a Month/DATE column")
    df = df.rename(columns={date_col: "MONTH"})
    df["MONTH"] = pd.to_datetime(df["MONTH"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    price_col = next((c for c in df.columns if str(c).strip().upper() in {"WTI_USD","WTI","PRICE","WTI_PRICE"}), None)
    if not price_col:
        raise ValueError("wti_monthly.csv missing WTI price column")
    return df[["MONTH", price_col]].rename(columns={price_col: "WTI_USD"})

# ----------------------------- Main build -----------------------------

def build_chrono(ogor_dir: str, leases_path: str, pattern: str,
                 dnc_path: Optional[str], wti_path: Optional[str], out_path: str) -> str:
    # Load lease mapping
    leases_df = load_leases_with_names(leases_path)

    # Collect OGOR data
    paths = sorted(glob.glob(os.path.join(ogor_dir, pattern)))
    if not paths:
        raise SystemExit(f"No OGOR files matched: {os.path.join(ogor_dir, pattern)}")

    parts = []
    for p in paths:
        df = read_ogor_zip(p)
        # Normalize
        df["LEASE_NUM"] = df["LEASE_NUM"].astype(str).map(normalize_lease_num)
        df = df[df["LEASE_NUM"].isin(leases_df["LEASE_NUM"])].copy()
        if df.empty:
            continue
        # Types
        df["DAYS_ON"]  = pd.to_numeric(df["DAYS_ON"], errors="coerce").fillna(0)
        df["OIL_PROD"] = pd.to_numeric(df["OIL_PROD"], errors="coerce").fillna(0)
        # WATER_PROD may not exist in standard 19-col set; try to find it 
        if "WATER_PROD" in df.columns:
            df["WATER_PROD"] = pd.to_numeric(df["WATER_PROD"], errors="coerce").fillna(0)
        else:
            water_col = next((c for c in df.columns if str(c).upper().startswith("WATER")), None)
            if water_col:
                df["WATER_PROD"] = pd.to_numeric(df[water_col], errors="coerce").fillna(0)
            else:
                df["WATER_PROD"] = 0.0

        # Parse month
        df["MONTH"] = df["PROD_YEARMONTH"].apply(month_from_yyyymm)
        df = df.dropna(subset=["MONTH"])  # keep only valid months

        # Labels
        df["WELL_NAME"]       = df["WELL_COMPLETION_ID"].astype(str).str.strip()
        df["API_WELL_NUMBER"] = pd.to_numeric(df["API_WELL_NUMBER"], errors="coerce")

        # Aggregate to lease/well/API/month
        g = (df.groupby(["LEASE_NUM","WELL_NAME","API_WELL_NUMBER","MONTH"], dropna=False)
               .agg(MONTHLY_OIL_VOLUME=("OIL_PROD","sum"),
                    MONTHLY_WATER_VOLUME=("WATER_PROD","sum"),
                    DAYS_ON_PROD=("DAYS_ON","sum"))
               .reset_index())
        parts.append(g)

    if not parts:
        raise SystemExit("No rows remained after filtering OGOR files for provided leases.")

    ogor_monthly = pd.concat(parts, ignore_index=True)

    # Map lease names & dev mapping via LEASE_NUM first
    ogor_monthly = ogor_monthly.merge(leases_df, on="LEASE_NUM", how="left")

    # Fallback: if DEV_NAME missing after LEASE_NUM join, try joining by LEASE_NAME
    needs_fallback = ("DEV_NAME" not in ogor_monthly.columns or
                      ogor_monthly["DEV_NAME"].isna().all() or
                      (ogor_monthly["DEV_NAME"].astype(str).str.strip() == "").all())
    if needs_fallback:
        ogor_monthly["LEASE_NAME_KEY"] = ogor_monthly["LEASE_NAME"].astype(str).str.upper().str.strip()
        ogor_monthly = ogor_monthly.drop(columns=[c for c in ["DEV_NAME","DEV_SYSTEM"] if c in ogor_monthly.columns])
        ogor_monthly = ogor_monthly.merge(leases_df[["LEASE_NAME_KEY","DEV_NAME","DEV_SYSTEM"]], on="LEASE_NAME_KEY", how="left")
        ogor_monthly.drop(columns=["LEASE_NAME_KEY"], inplace=True, errors="ignore")

    # Compute avg bbls/day
    ogor_monthly["AVG_BBLS_PER_DAY"] = np.where(
        ogor_monthly["DAYS_ON_PROD"] > 0,
        ogor_monthly["MONTHLY_OIL_VOLUME"] / ogor_monthly["DAYS_ON_PROD"],
        np.nan
    )

    # D&C allocation and WTI (optional)
    dnc = allocate_dnc_by_month(dnc_path)
    wti = load_wti_monthly(wti_path)

    df = ogor_monthly.merge(dnc, on=["API_WELL_NUMBER","MONTH"], how="left")
    df = df.merge(wti, on="MONTH", how="left")

    # Revenue convenience (can be overridden downstream)
    df["WTI_USD"] = pd.to_numeric(df.get("WTI_USD", np.nan), errors="coerce").fillna(0.0)
    df["MONTHLY_REVENUE_USD"] = df["MONTHLY_OIL_VOLUME"] * df["WTI_USD"]

    # Normalize column names (strip) and guarantee DEV_NAME/DEV_SYSTEM exist
    df.columns = df.columns.astype(str).str.strip()
    if "DEV_NAME" not in df.columns:
        df["DEV_NAME"] = df["LEASE_NAME"]
    if "DEV_SYSTEM" not in df.columns:
        df["DEV_SYSTEM"] = ""

    # Final column order
    cols = [
        "LEASE_NAME","WELL_NAME","API_WELL_NUMBER","MONTH",
        "ALLOCATED_DRILLING_DAYS","ALLOCATED_COMPLETION_DAYS",
        "AVG_BBLS_PER_DAY","DAYS_ON_PROD",
        "MONTHLY_OIL_VOLUME","MONTHLY_WATER_VOLUME",
        "WTI_USD","MONTHLY_REVENUE_USD",
        "DEV_NAME","DEV_SYSTEM"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan if c not in ("MONTHLY_OIL_VOLUME","MONTHLY_WATER_VOLUME","DAYS_ON_PROD") else 0.0

    df = df[cols].copy()
    df.sort_values(["DEV_NAME","LEASE_NAME","WELL_NAME","API_WELL_NUMBER","MONTH"], inplace=True)

    # Write workbook
    engine = choose_excel_engine()
    with pd.ExcelWriter(out_path, engine=engine, datetime_format="yyyy-mm-dd", date_format="yyyy-mm-dd") as xw:
        df.to_excel(xw, sheet_name="chronological", index=False)
        # README
        meta = pd.DataFrame({
            "Item": ["OGOR dir","Pattern","Leases","D&C","WTI","Generated"],
            "Value": [os.path.abspath(ogor_dir), pattern, leases_path,
                      dnc_path or "(none)", wti_path or "(none)",
                      pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")]
        })
        meta.to_excel(xw, sheet_name="README", index=False)

    return out_path

# ----------------------------- CLI -----------------------------

def parse_args():
    ap = argparse.ArgumentParser(prog="ogor_to_chronological_v23_001.py",
                                 description="Direct OGOR-A → chronological_lease_analysis.xlsx builder")
    ap.add_argument("--dir", default=".", help="Directory containing OGOR zip files")
    ap.add_argument("--leases", default="leases.xlsx", help="Leases file (.xlsx/.xls/.csv)")
    ap.add_argument("--pattern", default="ogora20??delimit.zip", help="Glob for OGOR zips")
    ap.add_argument("--dnc", default=None, help="Optional drilling_and_completion_days.xlsx")
    ap.add_argument("--wti", default=None, help="Optional wti_monthly.csv")
    ap.add_argument("--out", default="chronological_lease_analysis.xlsx", help="Output Excel path")
    return ap.parse_args()

def main():
    args = parse_args()
    out = build_chrono(args.dir, args.leases, args.pattern, args.dnc, args.wti, args.out)
    print(f"✅ Wrote {out}")

if __name__ == "__main__":
    main()
