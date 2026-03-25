#!/usr/bin/env python3
"""
Builds multi_year_lease_matrix_with_charts.xlsx from OGORA + WAR inputs.
Now supports ogora*.zip with headerless tab-delimited .txt files.

Output workbook structure (one set of sheets per lease/group):
- <LEASE_NAME or fallback>      -> monthly average oil rate (bbl/day) by API (base sheet expected downstream)
- <...>__days                   -> monthly days on production by API
- <...>__bbl                    -> monthly oil volume (bbl) by API
- <...>__water                  -> monthly water volume (bbl) by API

Notes:
- No __avg tab is created; the base sheet holds average oil rate (bbl/day) = OIL_BBL / DAYS_ON_PROD.
- Includes water volumes.
- If WAR API mapping is missing, sheets fall back to an OGORA-derived group (e.g., WD 31 or lease code like WD030).

Inputs (autodiscovered by default; override with CLI):
- --ogora-prod   : OGORA production file/dir/zip (csv/xlsx/txt or ogora*.zip)
- --war-main     : mv_war_main*.txt (API ↔ lease, well names)
- --leases       : leases.xlsx/csv (optional; lease enrichment)
- --out          : output filename (default: multi_year_lease_matrix_with_charts.xlsx)

Example:
  python build_multi_year_lease_matrix.py \
    --ogora-prod ./OGORA/ \
    --war-main mv_war_main.txt \
    --leases leases.xlsx \
    --out multi_year_lease_matrix_with_charts.xlsx
"""

import argparse
import os
from pathlib import Path
import re
import zipfile
import tempfile
import numpy as np
import pandas as pd

pd.options.mode.copy_on_write = True


# ----------------------------- helpers -----------------------------
def normalize_api(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip()
    s = re.sub(r"\.0$", "", s)
    return s

def month_str(ts):
    ts = pd.Timestamp(ts)
    return f"{ts.year:04d}-{ts.month:02d}"

def to_month(ts):
    return pd.to_datetime(ts, errors="coerce").dt.to_period("M").dt.to_timestamp()

def find_one(cwd, patterns):
    for pat in patterns:
        hits = sorted(Path(cwd).glob(pat))
        if hits:
            return str(hits[0])
    return None

def find_many(cwd, patterns):
    files = []
    for pat in patterns:
        files.extend(sorted(Path(cwd).glob(pat)))
    return [str(p) for p in files]

def autodiscover_inputs(cwd):
    war_main = find_one(cwd, ["mv_war_main.txt", "mv_war_main_*.txt"])
    leases = find_one(cwd, ["leases.xlsx", "leases_*.xlsx", "leases.csv", "leases_*.csv"])
    ogora_files = find_many(cwd, ["ogora*.csv", "ogora*.xlsx", "ogora*.txt",
                                  "OGORA/*.csv", "OGORA/*.xlsx", "OGORA/*.txt"])
    ogora_zips = find_many(cwd, ["ogora*.zip", "OGORA/*.zip"])
    ogora_dir = find_one(cwd, ["OGORA"])
    return war_main, leases, ogora_files, ogora_zips, ogora_dir


# ----------------------------- tolerant readers -----------------------------
def sniff_read_csv_like(path, header="infer"):
    """
    Tolerant reader for delimited text: tries python sniff (unknown sep), then tab, pipe, comma, semicolon.
    header can be "infer" or None.
    """
    try:
        return pd.read_csv(path, sep=None, engine="python", encoding="ISO-8859-1",
                           on_bad_lines="skip", low_memory=True, header=header)
    except Exception:
        pass
    for sep in ["\t", "|", ",", ";"]:
        try:
            return pd.read_csv(path, sep=sep, encoding="ISO-8859-1",
                               on_bad_lines="skip", low_memory=True, header=header)
        except Exception:
            continue
    # Final fallback
    return pd.read_csv(path, encoding="utf-8", on_bad_lines="skip", low_memory=True, header=header)

def sniff_read_table(path):
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(p)
    elif ext in (".csv",):
        # CSVs usually have headers
        return sniff_read_csv_like(p, header="infer")
    elif ext in (".txt",):
        # OGORA 'delimit' text often has NO headers; default to header=None
        return sniff_read_csv_like(p, header=None)
    else:
        # Unknown extension; attempt as CSV-like without header
        return sniff_read_csv_like(p, header=None)


# ----------------------------- WAR loaders -----------------------------
def load_war_main(path):
    if not path or not os.path.exists(path):
        raise FileNotFoundError("WAR main file not found.")
    df = sniff_read_table(path)
    C = {c.upper(): c for c in df.columns}

    api   = C.get("API_WELL_NUMBER") or C.get("API_NUMBER") or C.get("API")
    lease = C.get("SURF_LEASE_NUM")  or C.get("LEASE_NUM")  or C.get("SURF_LEASE")
    lname = C.get("LEASE_NAME")
    wname = C.get("WELL_NAME")       or C.get("WELL_NM")

    out = pd.DataFrame({
        "API_WELL_NUMBER": df[api].apply(normalize_api) if api else None,
        "SURF_LEASE_NUM": df[lease].astype(str).str.strip().str.upper().str.replace(r"^G", "", regex=True) if lease else None,
        "LEASE_NAME": df[lname] if lname else None,
        "WELL_NAME": df[wname] if wname else None
    })
    out = out.dropna(subset=["API_WELL_NUMBER"]).copy()
    out["LEASE_KEY"] = out["LEASE_NAME"].fillna(out["SURF_LEASE_NUM"])
    return out[["API_WELL_NUMBER", "LEASE_NAME", "SURF_LEASE_NUM", "WELL_NAME", "LEASE_KEY"]].drop_duplicates()

def load_leases(path):
    if not path or not os.path.exists(path):
        return pd.DataFrame(columns=["SURF_LEASE_NUM", "LEASE_NAME", "DEV_NAME", "LEASE_KEY"])
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(p)
    else:
        df = sniff_read_table(p)
    C = {c.upper(): c for c in df.columns}
    num = C.get("LEASE_NUM") or C.get("SURF_LEASE_NUM") or C.get("LEASE_NUMBER")
    lname = C.get("LEASE_NAME")
    dev = C.get("DEV_NAME")

    out = pd.DataFrame({
        "SURF_LEASE_NUM": df[num].astype(str).str.strip().str.upper().str.replace(r"^G", "", regex=True) if num else None,
        "LEASE_NAME": df[lname] if lname else None,
        "DEV_NAME": df[dev] if dev else None
    })
    out["LEASE_KEY"] = out["LEASE_NAME"].fillna(out["SURF_LEASE_NUM"])
    return out.drop_duplicates()


# ----------------------------- OGORA extraction -----------------------------
def extract_ogora_zips_to_temp(zip_paths):
    """
    Extract CSV/XLSX/TXT from a list of zip files to a temporary directory.
    Returns (tempdir, [file_paths]). Keep the tempdir object referenced until you're done.
    """
    tempdir = tempfile.TemporaryDirectory()
    extracted = []
    for zp in zip_paths:
        try:
            with zipfile.ZipFile(zp) as zf:
                for name in zf.namelist():
                    lower = name.lower()
                    if lower.endswith((".csv", ".xlsx", ".txt")):
                        out_path = Path(tempdir.name) / Path(name).name
                        with zf.open(name) as src, open(out_path, "wb") as dst:
                            dst.write(src.read())
                        extracted.append(str(out_path))
        except zipfile.BadZipFile:
            print(f"⚠️ Skipping unreadable zip: {zp}")
    return tempdir, extracted

def read_any_table(path):
    return sniff_read_table(path)


# ----------------------------- OGORA loader -----------------------------
def pick(C, aliases):
    for k in aliases:
        v = C.get(k)
        if v:
            return v
    return None

def is_headerless_ogora(df):
    """
    Heuristic: headerless OGORA txt will come in with integer-like values as the first row,
    and we read with header=None, so columns are 0..N-1. We just ensure we have enough columns.
    """
    return set(df.columns) == set(range(df.shape[1])) and df.shape[1] >= 8

def parse_headerless_ogora(df):
    """
    Map positional columns based on observed OGORA 'delimit' structure:
      0: district/area code (ignore)
      1: WELL_ID (use as API_WELL_NUMBER surrogate)
      2: PROD_MONTH (YYYYMM)
      3: DAYS_ON_PROD
      4: product code (O/G/U) (ignore for now)
      5: OIL_BBL
      6: GAS (ignore)
      7: WATER_BBL
      10: AREA (e.g., WD)
      11: BLOCK (e.g., 31)
      14: LEASE_HINT (e.g., WD030)
    """
    df = df.copy()
    cols = list(range(df.shape[1]))
    def safe_col(i):
        return df[i] if i in cols else np.nan

    well_id = safe_col(1).astype(str).str.strip()
    yyyymm = pd.to_numeric(safe_col(2), errors="coerce").astype("Int64")
    prod_month = pd.to_datetime(yyyymm.astype(str) + "01", format="%Y%m%d", errors="coerce")

    days = pd.to_numeric(safe_col(3), errors="coerce").fillna(0)
    oil = pd.to_numeric(safe_col(5), errors="coerce").fillna(0.0)
    water = pd.to_numeric(safe_col(7), errors="coerce").fillna(0.0)

    area = safe_col(10).astype(str).str.strip()
    block = pd.to_numeric(safe_col(11), errors="coerce").astype("Int64")
    lease_hint = safe_col(14).astype(str).str.strip()

    # Build fallback grouping label
    area_block = (area.fillna("") + " " + block.astype(str).fillna("")).str.strip()
    lease_fallback = lease_hint.where(lease_hint.ne(""), area_block)
    lease_fallback = lease_fallback.where(lease_fallback.ne(""), "UNMAPPED")

    out = pd.DataFrame({
        "API_WELL_NUMBER": well_id.apply(normalize_api),   # surrogate if true API not present
        "MONTH": prod_month.dt.to_period("M").dt.to_timestamp(),
        "OIL_BBL": oil,
        "WATER_BBL": water,
        "DAYS_ON_PROD": days,
        "LEASE_FALLBACK": lease_fallback
    })
    out = out.dropna(subset=["API_WELL_NUMBER", "MONTH"])
    return out

def load_ogora_production(ogora_source):
    """
    Accepts:
      - A list of file paths (csv/xlsx/txt)
      - A directory with files
      - A single file path
      - A list of zip paths; or a directory containing ogora*.zip (handled below)

    Expected columns (aliases supported when headers exist):
      API: API, API_NUMBER, API_WELL_NUMBER
      DATE/MONTH: DATE, PROD_DATE, PRODUCTION_DATE, MONTH, FIRST_OF_MONTH, PRODUCTION_MONTH, PROD_MONTH
      or YEAR/MONTH pairs: YEAR, YR, PROD_YEAR, PRODUCTION_YEAR  AND  MONTH, MO, MN, PROD_MONTH, PRODUCTION_MONTH
      OIL: OIL_BBL, OIL, OIL_VOLUME, OIL_BBLS, OIL (BBL), OIL PROD (BBL)
      WATER: WATER_BBL, WATER, WTR, WATER_BBLS, WATER (BBL)
      DAYS: DAYS, DAYS_ON_PROD, PROD_DAYS, PRODUCTION_DAYS

    Also supports headerless tab-delimited OGORA text files (positional mapping).
    """
    files = []
    tempctx = None

    def add_from_dir(d):
        files.extend([str(x) for x in Path(d).glob("*.csv")])
        files.extend([str(x) for x in Path(d).glob("*.xlsx")])
        files.extend([str(x) for x in Path(d).glob("*.txt")])
        zips = [str(x) for x in Path(d).glob("ogora*.zip")]
        if zips:
            nonlocal tempctx
            tempctx, extracted = extract_ogora_zips_to_temp(zips)
            files.extend(extracted)

    # Normalize the input into a list of paths
    if isinstance(ogora_source, (list, tuple)):
        zip_list = [p for p in ogora_source if str(p).lower().endswith(".zip")]
        nonzip = [p for p in ogora_source if not str(p).lower().endswith(".zip")]
        if zip_list:
            tempctx, extracted = extract_ogora_zips_to_temp(zip_list)
            files.extend(extracted)
        for p in nonzip:
            if os.path.isdir(p):
                add_from_dir(p)
            elif os.path.exists(p):
                files.append(str(p))
    else:
        path = str(ogora_source)
        if os.path.isdir(path):
            add_from_dir(path)
        elif os.path.exists(path) and path.lower().endswith(".zip"):
            tempctx, extracted = extract_ogora_zips_to_temp([path])
            files.extend(extracted)
        elif os.path.exists(path):
            files.append(path)

    # Also scan current dir for ogora*.zip if nothing found
    if not files:
        zips_here = [str(p) for p in Path(".").glob("ogora*.zip")]
        if zips_here:
            tempctx, extracted = extract_ogora_zips_to_temp(zips_here)
            files.extend(extracted)

    if not files:
        raise FileNotFoundError("No OGORA production files found (csv/xlsx/txt or ogora*.zip).")

    frames = []
    for f in files:
        try:
            df = read_any_table(f)
        except Exception:
            print(f"⚠️ Skipping unreadable file: {f}")
            continue

        # Headerless OGORA .txt (positional)
        if is_headerless_ogora(df):
            frames.append(parse_headerless_ogora(df))
            continue

        # Header-based mapping
        C = {c.upper(): c for c in df.columns}

        api_col = pick(C, ["API_WELL_NUMBER", "API_NUMBER", "API", "API NO", "WELL_API"])
        dt_col  = pick(C, ["MONTH", "DATE", "PROD_DATE", "FIRST_OF_MONTH", "PRODUCTION_DATE",
                           "PRODUCTION_MONTH", "PROD_MONTH"])
        y_col   = pick(C, ["YEAR", "YR", "PROD_YEAR", "PRODUCTION_YEAR", "REPORT_YEAR"])
        m_col   = pick(C, ["MONTH", "MO", "MN", "PROD_MONTH", "PRODUCTION_MONTH", "REPORT_MONTH"])
        oil_col = pick(C, ["OIL_BBL", "OIL", "OIL_VOLUME", "OIL_BBLS", "OIL (BBL)", "OIL PROD (BBL)"])
        wat_col = pick(C, ["WATER_BBL", "WATER", "WTR", "WATER_BBLS", "WATER (BBL)"])
        day_col = pick(C, ["DAYS_ON_PROD", "DAYS", "PROD_DAYS", "PRODUCTION_DAYS", "DAYS ON"])

        if api_col is None:
            print(f"⚠️ Skipping file without API column: {f}")
            continue

        api_series = df[api_col].apply(normalize_api)

        # Build DATE
        if dt_col is not None:
            date_series = pd.to_datetime(df[dt_col], errors="coerce")
        elif y_col is not None and m_col is not None:
            y = pd.to_numeric(df[y_col], errors="coerce").astype("Int64")
            m = pd.to_numeric(df[m_col], errors="coerce").astype("Int64").clip(lower=1, upper=12)
            date_series = pd.to_datetime(dict(year=y, month=m, day=1), errors="coerce")
        else:
            print(f"⚠️ Skipping file without usable date/month columns: {f}")
            continue

        tmp = pd.DataFrame({
            "API_WELL_NUMBER": api_series,
            "DATE": date_series,
            "OIL_BBL": pd.to_numeric(df[oil_col], errors="coerce") if oil_col else np.nan,
            "WATER_BBL": pd.to_numeric(df[wat_col], errors="coerce") if wat_col else np.nan,
            "DAYS": pd.to_numeric(df[day_col], errors="coerce") if day_col else np.nan
        })
        frames.append(tmp)

    if not frames:
        raise ValueError("OGORA loader did not find any usable files/columns after scanning inputs/zips.")

    prod = pd.concat(frames, ignore_index=True)

    # If header-based path provided "DATE", normalize; headerless path already provided "MONTH"
    if "MONTH" not in prod.columns:
        prod = prod.dropna(subset=["API_WELL_NUMBER", "DATE"]).copy()
        prod["MONTH"] = to_month(prod["DATE"])
        # Daily vs monthly: duplicates imply daily; sum and count days if needed
        counts = prod.groupby(["API_WELL_NUMBER", "MONTH"]).size()
        daily_mode = (counts > 1).sum() > 0
        if daily_mode:
            prod["has_prod"] = ((prod["OIL_BBL"].fillna(0) > 0) | (prod["WATER_BBL"].fillna(0) > 0)).astype(int)
            grouped = prod.groupby(["API_WELL_NUMBER", "MONTH"], as_index=False).agg({
                "OIL_BBL": "sum",
                "WATER_BBL": "sum",
                "DAYS": "sum",
                "has_prod": "sum"
            })
            grouped["DAYS_ON_PROD"] = np.where(
                grouped["DAYS"].fillna(0) > 0,
                grouped["DAYS"].fillna(0),
                grouped["has_prod"].fillna(0)
            )
            monthly = grouped.drop(columns=["DAYS", "has_prod"])
        else:
            monthly = prod.groupby(["API_WELL_NUMBER", "MONTH"], as_index=False).agg({
                "OIL_BBL": "sum",
                "WATER_BBL": "sum",
                "DAYS": "sum"
            }).rename(columns={"DAYS": "DAYS_ON_PROD"})
        # Ensure fallback column exists
        if "LEASE_FALLBACK" not in monthly.columns:
            monthly["LEASE_FALLBACK"] = np.nan
    else:
        # Headerless already monthly and has LEASE_FALLBACK
        monthly = prod.copy()

    # Fill NaNs with zeros for measures
    for c in ["OIL_BBL", "WATER_BBL", "DAYS_ON_PROD"]:
        monthly[c] = pd.to_numeric(monthly[c], errors="coerce").fillna(0.0)

    return monthly


# ----------------------------- builder -----------------------------
def build_workbook(prod_monthly, war_map, leases_df, out_path):
    """
    prod_monthly: columns [API_WELL_NUMBER, MONTH, OIL_BBL, WATER_BBL, DAYS_ON_PROD, LEASE_FALLBACK?]
    war_map: API to LEASE_NAME, SURF_LEASE_NUM, WELL_NAME, LEASE_KEY
    leases_df: optional lease list with LEASE_KEY enrichment
    out_path: excel filename
    """
    prod = prod_monthly.merge(
        war_map[["API_WELL_NUMBER", "LEASE_NAME", "SURF_LEASE_NUM", "WELL_NAME", "LEASE_KEY"]],
        on="API_WELL_NUMBER", how="left"
    )

    # Lease name fallback from leases_df by SURF_LEASE_NUM
    if not leases_df.empty:
        lease_names = leases_df[["SURF_LEASE_NUM", "LEASE_NAME"]].dropna()
        if not lease_names.empty:
            prod = prod.merge(
                lease_names.rename(columns={"LEASE_NAME": "LEASE_NAME_FROM_LIST"}),
                on="SURF_LEASE_NUM", how="left"
            )
            prod["LEASE_NAME"] = prod["LEASE_NAME"].fillna(prod["LEASE_NAME_FROM_LIST"])
            prod = prod.drop(columns=["LEASE_NAME_FROM_LIST"], errors="ignore")

    # Final group label: prefer WAR lease name; else OGORA fallback; else SURF_LEASE_NUM; else UNMAPPED
    prod["GROUP_LABEL"] = prod["LEASE_NAME"]
    if "LEASE_FALLBACK" in prod.columns:
        prod["GROUP_LABEL"] = prod["GROUP_LABEL"].fillna(prod["LEASE_FALLBACK"])
    prod["GROUP_LABEL"] = prod["GROUP_LABEL"].fillna(prod["SURF_LEASE_NUM"]).fillna("UNMAPPED")

    # Well name: prefer WAR well name; else use API string
    prod["WELL_NAME"] = prod["WELL_NAME"].fillna(prod["API_WELL_NUMBER"])

    # Month label strings for columns
    prod["MONTH_STR"] = prod["MONTH"].apply(month_str)

    # Keep only rows with a group label
    prod = prod.dropna(subset=["GROUP_LABEL"]).copy()

    # Workbook writer
    with pd.ExcelWriter(out_path, engine="xlsxwriter") as xw:
        # Index sheet
        index_cols = ["GROUP_LABEL", "LEASE_NAME", "SURF_LEASE_NUM"]
        leases_sorted = (
            prod[index_cols]
            .drop_duplicates()
            .sort_values(index_cols)
        )
        leases_sorted.to_excel(xw, sheet_name="Lease_Index", index=False)

        # Build per-group sheets
        for lease_key, g in prod.groupby("GROUP_LABEL", dropna=True):
            # Id columns
            id_cols = ["WELL_NAME", "API_WELL_NUMBER"]

            # Pivot helper
            def pivot_metric(val_col):
                p = g.pivot_table(
                    index=id_cols,
                    columns="MONTH_STR",
                    values=val_col,
                    aggfunc="sum",
                    fill_value=0.0,
                )
                # Order columns chronologically by YYYY-MM
                cols = sorted(p.columns, key=lambda s: (int(s[:4]), int(s[5:7])))
                return p.reindex(columns=cols)

            p_bbl = pivot_metric("OIL_BBL")
            p_water = pivot_metric("WATER_BBL")
            p_days = pivot_metric("DAYS_ON_PROD")

            # Average oil rate (bbl/day) = OIL_BBL / DAYS_ON_PROD (guard div by zero)
            common_cols = sorted(set(p_bbl.columns).intersection(set(p_days.columns)),
                                 key=lambda s: (int(s[:4]), int(s[5:7])))
            avg = p_bbl.reindex(columns=common_cols)
            days = p_days.reindex(columns=common_cols)
            with np.errstate(divide="ignore", invalid="ignore"):
                avg_vals = np.where(days.values > 0, avg.values / days.values, 0.0)
            p_avg = pd.DataFrame(avg_vals, index=avg.index, columns=avg.columns)

            # Excel sheet names (<=31 chars)
            ws_name = (str(lease_key) if pd.notna(lease_key) else "LEASE")[:31]

            # Base sheet: avg rate
            p_avg.reset_index().to_excel(xw, sheet_name=ws_name, index=False)

            # __days
            p_days.reset_index().to_excel(xw, sheet_name=f"{ws_name}__days"[:31], index=False)

            # __bbl
            p_bbl.reset_index().to_excel(xw, sheet_name=f"{ws_name}__bbl"[:31], index=False)

            # __water
            p_water.reset_index().to_excel(xw, sheet_name=f"{ws_name}__water"[:31], index=False)


# ----------------------------- main -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Build multi-year lease matrix from OGORA + WAR.")
    parser.add_argument("--ogora-prod", default=None, help="OGORA production file/dir/zip (csv/xlsx/txt or ogora*.zip).")
    parser.add_argument("--war-main", default=None, help="WAR main file (mv_war_main*.txt).")
    parser.add_argument("--leases", default=None, help="Lease mapping file (xlsx/csv), optional.")
    parser.add_argument("--out", default="multi_year_lease_matrix_with_charts.xlsx", help="Output Excel filename.")
    args = parser.parse_args()

    cwd = os.getcwd()
    auto_war_main, auto_leases, auto_ogora_files, auto_ogora_zips, auto_ogora_dir = autodiscover_inputs(cwd)

    war_main_path = args.war_main or auto_war_main
    if not war_main_path:
        raise SystemExit("Missing WAR main file. Provide --war-main or place mv_war_main.txt in the directory.")

    leases_path = args.leases or auto_leases  # optional

    ogora_source = args.ogora_prod or auto_ogora_files or auto_ogora_zips or auto_ogora_dir
    if not ogora_source:
        raise SystemExit("Missing OGORA production source. Provide --ogora-prod or place ogora*.zip or .txt in the directory.")

    print(f"Using WAR main: {war_main_path}")
    if leases_path:
        print(f"Using leases:   {leases_path}")
    print(f"Using OGORA:    {ogora_source}")
    print(f"Output:         {args.out}")

    war_map = load_war_main(war_main_path)
    leases_df = load_leases(leases_path) if leases_path else pd.DataFrame()
    prod_monthly = load_ogora_production(ogora_source)

    if prod_monthly.empty:
        raise SystemExit("OGORA production appears empty after loading.")

    build_workbook(prod_monthly, war_map, leases_df, args.out)

    print(f"✅ Built {args.out} with {len(prod_monthly)} rows.")

if __name__ == "__main__":
    main()
