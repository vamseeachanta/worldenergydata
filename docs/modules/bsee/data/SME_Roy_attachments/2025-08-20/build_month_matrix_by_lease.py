#!/usr/bin/env python3
# build_multi_year_matrix_by_lease.py
# Scan a directory for OGOR-A zip files (wildcard), merge them, and write one sheet per lease.
# Rows = (Well Name, API), Columns = YYYY-MM, Values = OIL_PROD / DAYS_ON (BBL/day)

import argparse
import os
import re
import io
import glob
import zipfile
import pandas as pd
import sys
import subprocess
import importlib



# --- Helpers ---
def normalize_lease_num(val: str) -> str:
    s = str(val).strip().upper()
    m = re.fullmatch(r"G?(\d+)", s)
    return "G" + m.group(1) if m else s

def _ensure_pkg(pkg: str) -> bool:
    try:
        import importlib
        importlib.import_module(pkg)
        return True
    except ModuleNotFoundError:
        try:
            print(f"⚙️ Attempting to install '{pkg}' ...")
            import sys, subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            importlib.import_module(pkg)
            print(f"✅ Installed '{pkg}'.")
            return True
        except Exception as e:
            print(f"⚠️ Could not install '{pkg}': {e}")
            return False

def choose_excel_engine() -> str:
    # Prefer xlsxwriter; if missing, try to install, else fall back to openpyxl.
    try:
        import xlsxwriter  # noqa: F401
        return "xlsxwriter"
    except ModuleNotFoundError:
        if _ensure_pkg("xlsxwriter"):
            return "xlsxwriter"
    # Try openpyxl
    try:
        import openpyxl  # noqa: F401
        return "openpyxl"
    except ModuleNotFoundError:
        if _ensure_pkg("openpyxl"):
            return "openpyxl"
    raise SystemExit("❌ Neither 'xlsxwriter' nor 'openpyxl' is available and installation failed. "
                     "Please install one of them: pip install xlsxwriter (recommended) or openpyxl.")


def resolve_group_column(leases_df: pd.DataFrame, group_col: str) -> str:
    if group_col and str(group_col).upper() != "AUTO":
        cand = str(group_col).upper().strip()
        if cand in leases_df.columns:
            return cand
        raise SystemExit(f"❌ group-col '{group_col}' not found in leases columns: {list(leases_df.columns)}")
    for cand in ("GROUP_AS", "DEV_NAME", "GROUP", "GROUP_NAME", "LEASE_NAME"):
        if cand in leases_df.columns:
            return cand
    # Fallback to LEASE_NAME-like column heuristic
    for c in leases_df.columns:
        if "NAME" in c:
            return c
    # Last resort: use LEASE_NUM
    return "LEASE_NUM"

OGORA_COLS = [
    'LEASE_NUM', 'WELL_COMPLETION_ID', 'PROD_YEARMONTH', 'DAYS_ON', 'PRODUCT_CODE',
    'OIL_PROD', 'GAS_PROD', 'COND_PROD', 'API_WELL_NUMBER', 'FIELD10',
    'BLOCK_DESC', 'FIELD12', 'OPERATOR_NAME', 'BLOCK_CODE', 'FIELD15',
    'SUFFIX', 'SPUD_DATE', 'ENTITY_ID', 'STATUS'
]

# Try to pull a 4-digit year from a filename to help ordering; fallback 0
YEAR_IN_FN = re.compile(r'(?<!\d)(20\d{2})(?!\d)')

def load_leases_with_names(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    elif ext == ".csv":
        df = pd.read_csv(path, dtype=str)
    else:
        raise ValueError("leases file must be .xlsx, .xls, or .csv")

    df.columns = df.columns.str.upper().str.strip()

    lease_num_col  = next((c for c in df.columns if "LEASE" in c and "NUM"  in c), None) or df.columns[0]
    lease_name_col = next((c for c in df.columns if "LEASE" in c and "NAME" in c), lease_num_col)

    # Prefer GROUP_AS or DEV_NAME if present, else fall back to LEASE_NAME
    group_col = None
    for cand in ("GROUP_AS", "DEV_NAME", "GROUP", "GROUP_NAME"):
        if cand in df.columns:
            group_col = cand
            break
    if not group_col:
        group_col = lease_name_col

    out = pd.DataFrame({
        "LEASE_NUM":  df[lease_num_col].map(normalize_lease_num),
        "SHEET_NAME": df[group_col].astype(str).str.strip().fillna(""),
        "LEASE_NAME": df[lease_name_col].astype(str).str.strip().fillna("")
    })
    return out

def read_ogor_zip(zip_path: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path, "r") as z:
        inner = [n for n in z.namelist() if n.lower().endswith((".txt", ".csv"))]
        if not inner:
            raise ValueError(f"No .txt/.csv found inside {zip_path}")
        with z.open(inner[0]) as f:
            df = pd.read_csv(io.TextIOWrapper(f, encoding="ISO-8859-1"),
                             header=None, dtype=str, quotechar='"')
    # Normalize to 19 columns
    if df.shape[1] < len(OGORA_COLS):
        for _ in range(len(OGORA_COLS) - df.shape[1]):
            df[df.shape[1]] = None
    elif df.shape[1] > len(OGORA_COLS):
        df = df.iloc[:, :len(OGORA_COLS)]
    df.columns = OGORA_COLS
    return df

def main():
    ap = argparse.ArgumentParser(prog="build_month_matrix_by_lease_020.py",
                              description="Multi-year grouped monthly BBL/day matrix (one sheet per DEV/GROUP_AS).")
    ap.add_argument("--dir",     default=".", help="Directory containing OGOR zip files (default: .)")
    ap.add_argument("--leases",  default="AUTO", help="Leases file (.xlsx/.xls/.csv). If 'AUTO', search in --dir then CWD.")
    ap.add_argument("--out",     default="multi_year_lease_matrix_with_charts.xlsx", help="Output Excel path (default shown)")
    ap.add_argument("--pattern", default="ogora20??delimit.zip", help="Glob for OGOR zips (default shown)")
    args = ap.parse_args()
    # Fallbacks for older CLIs
    if not hasattr(args, 'group_mode'): args.group_mode = 'leases'
    if not hasattr(args, 'group_col'): args.group_col = 'AUTO'
    # Auto-resolve leases file if requested
    if str(args.leases).upper() == "AUTO":
        candidates = ["leases.xlsx", "leases.xls", "leases.csv"]
        chosen = None
        for c in candidates:
            p1 = os.path.join(args.dir, c)
            p2 = c
            if os.path.exists(p1):
                chosen = p1
                break
            if os.path.exists(p2):
                chosen = p2
                break
        if not chosen:
            raise SystemExit("❌ Could not find leases.xlsx/.xls/.csv in current directory or --dir. Pass --leases <path>.")
        args.leases = chosen
        print(f"🔎 Using leases file: {args.leases}")
    else:
        if not os.path.exists(args.leases):
            raise SystemExit(f"❌ Leases file not found: {args.leases}")

    print(f"📂 OGOR dir: {os.path.abspath(args.dir)}")
    print(f"🔎 Pattern: {args.pattern}")
    print(f"📄 Output : {args.out}")
# Auto-resolve leases file if requested
    if str(args.leases).upper() == "AUTO":
        candidates = ["leases.xlsx", "leases.xls", "leases.csv"]
        chosen = None
        for c in candidates:
            p1 = os.path.join(args.dir, c)
            p2 = c
            if os.path.exists(p1):
                chosen = p1
                break
            if os.path.exists(p2):
                chosen = p2
                break
        if not chosen:
            raise SystemExit("❌ Could not find leases.xlsx/.xls/.csv in current directory or --dir. Pass --leases <path>.")
        args.leases = chosen
        print(f"🔎 Using leases file: {args.leases}")
    else:
        if not os.path.exists(args.leases):
            raise SystemExit(f"❌ Leases file not found: {args.leases}")

    print(f"📂 OGOR dir: {os.path.abspath(args.dir)}")
    print(f"🔎 Pattern: {args.pattern}")
    print(f"📄 Output : {args.out}")

    # Load lease map
    leases_df = load_leases_with_names(args.leases)
    lease_map = dict(zip(leases_df["LEASE_NUM"], leases_df["SHEET_NAME"]))
    lease_set = set(lease_map.keys())
    lease_set = set(leases_df["LEASE_NUM"])

    # Find files by wildcard
    search_glob = os.path.join(args.dir, args.pattern)
    paths = glob.glob(search_glob)
    if not paths:
        raise SystemExit(f"No files matched pattern: {search_glob}")

    # Sort by inferred year for sanity (not required, we still sort YYYY-MM later)
    def year_key(p):
        m = YEAR_IN_FN.search(os.path.basename(p))
        return int(m.group(1)) if m else 0
    paths.sort(key=year_key)

    # Process each file and collect monthly bbl/day
    parts = []
    for p in paths:
        df = read_ogor_zip(p)
        # Normalize lease numbers to G#####
        df["LEASE_NUM"] = df["LEASE_NUM"].astype(str).map(normalize_lease_num)
        # Keep only our leases
        df = df[df["LEASE_NUM"].isin(lease_set)].copy()
        if df.empty:
            continue

        # Types
        df["DAYS_ON"]  = pd.to_numeric(df["DAYS_ON"], errors="coerce").fillna(0)
        df["OIL_PROD"] = pd.to_numeric(df["OIL_PROD"], errors="coerce").fillna(0)

        # Parse year-month into YYYY-MM
        s = df["PROD_YEARMONTH"].astype(str).str.replace(r"\D", "", regex=True)
        df["PROD_YEAR"]  = pd.to_numeric(s.str[:4], errors="coerce")
        df["PROD_MONTH"] = pd.to_numeric(s.str[4:6], errors="coerce")
        df = df.dropna(subset=["PROD_YEAR","PROD_MONTH"])
        df["PROD_YEAR"]  = df["PROD_YEAR"].astype(int)
        df["PROD_MONTH"] = df["PROD_MONTH"].astype(int).clip(1, 12)
        df["YEAR_MONTH"] = df["PROD_YEAR"].astype(str) + "-" + df["PROD_MONTH"].astype(str).str.zfill(2)

        # Well labels
        df["WELL_NAME"]       = df["WELL_COMPLETION_ID"].astype(str).str.strip()
        df["API_WELL_NUMBER"] = df["API_WELL_NUMBER"].astype(str).str.strip()

        # Aggregate to well-month, then compute bbl/day
        g = (df.groupby(["LEASE_NUM","WELL_NAME","API_WELL_NUMBER","YEAR_MONTH"], dropna=False)
                .agg(OIL_SUM=("OIL_PROD","sum"), DAYS_SUM=("DAYS_ON","sum"))
                .reset_index())
        g["BBLS_PER_DAY"] = g.apply(
            lambda r: (r["OIL_SUM"] / r["DAYS_SUM"]) if r["DAYS_SUM"] and r["DAYS_SUM"] > 0 else 0, axis=1
        )
        parts.append(g[["LEASE_NUM","WELL_NAME","API_WELL_NUMBER","YEAR_MONTH","BBLS_PER_DAY"]])

    if not parts:
        raise SystemExit("No matching rows found across the OGOR files for the given leases.")

    all_g = pd.concat(parts, ignore_index=True)

    # Full set of YYYY-MM columns across all files
    ym_sorted = sorted(all_g["YEAR_MONTH"].unique())

    # Write workbook: sheet per lease NAME; row per well; columns = all YYYY-MM
    excel_engine = choose_excel_engine()
    with pd.ExcelWriter(args.out, engine=excel_engine) as writer:
        # Determine column order across all data
        ym_sorted = sorted(all_g["YEAR_MONTH"].unique())

        if args.group_mode == "group":
            # Build group -> list of lease_nums using selected group column
            grp_col = resolve_group_column(leases_df, args.group_col)
            group_to_leases = {}
            for _, row in leases_df.iterrows():
                ln = row["LEASE_NUM"]
                sn = row.get(grp_col, row.get("LEASE_NAME", ln))
                sn = str(sn).strip() or str(ln)
                group_to_leases.setdefault(sn, set()).add(ln)

            # Write one sheet per group
            used_names = set()
            mapping_rows = []
            for sheet_name in sorted(group_to_leases.keys()):
                group_leases = group_to_leases[sheet_name]
                sub = all_g[all_g["LEASE_NUM"].isin(group_leases)].copy()
                safe_name = str(sheet_name)[:31]
                if safe_name in used_names:
                    # Disambiguate duplicate names
                    safe_name = (str(sheet_name)[:27] + "_dup")[:31]
                used_names.add(safe_name)

                if sub.empty:
                    pd.DataFrame(columns=["WELL_NAME","API_WELL_NUMBER"]).to_excel(writer, sheet_name=safe_name, index=False)
                else:
                    mat = sub.pivot_table(
                        index=["WELL_NAME","API_WELL_NUMBER"],
                        columns="YEAR_MONTH",
                        values="BBLS_PER_DAY",
                        aggfunc="sum",
                        fill_value=0.0
                    )
                    mat = mat.reindex(columns=ym_sorted, fill_value=0.0).reset_index()
                    mat.to_excel(writer, sheet_name=safe_name, index=False)

                for ln in sorted(group_leases):
                    mapping_rows.append({"LEASE_NUM": ln, "GROUP_SHEET": sheet_name, "SHEET_WRITTEN": safe_name})

            # QA mapping tab
            if mapping_rows:
                pd.DataFrame(mapping_rows).to_excel(writer, sheet_name="QA_Lease_to_Group", index=False)

        else:
            
            # Per-lease-name sheets (default)
            used_names = set()
            # Build LEASE_NAME -> set(LEASE_NUM) mapping
            if "LEASE_NAME" in leases_df.columns:
                name_col = "LEASE_NAME"
            else:
                # if not present, fall back to DEV_NAME, then LEASE_NUM
                name_col = "DEV_NAME" if "DEV_NAME" in leases_df.columns else "LEASE_NUM"

            name_to_leases = {}
            for _, row in leases_df.iterrows():
                ln = row["LEASE_NUM"]
                nm = str(row.get(name_col, ln)).strip() or str(ln)
                name_to_leases.setdefault(nm, set()).add(ln)

            for sheet_name in sorted(name_to_leases.keys()):
                group_leases = name_to_leases[sheet_name]
                sub = all_g[all_g["LEASE_NUM"].isin(group_leases)].copy()
                safe_name = str(sheet_name)[:31]
                if safe_name in used_names:
                    # Disambiguate duplicate names (should be rare)
                    safe_name = (str(sheet_name)[:27] + "_dup")[:31]
                used_names.add(safe_name)

                if sub.empty:
                    pd.DataFrame(columns=["WELL_NAME","API_WELL_NUMBER"]).to_excel(writer, sheet_name=safe_name, index=False)
                else:
                    mat = sub.pivot_table(
                        index=["WELL_NAME","API_WELL_NUMBER"],
                        columns="YEAR_MONTH",
                        values="BBLS_PER_DAY",
                        aggfunc="sum",
                        fill_value=0.0
                    )
                    mat = mat.reindex(columns=ym_sorted, fill_value=0.0).reset_index()
                    mat.to_excel(writer, sheet_name=safe_name, index=False)

            # QA tab with mapping Name -> Leases
            mapping_rows = []
            for nm, leases in sorted(name_to_leases.items()):
                for ln in sorted(leases):
                    mapping_rows.append({"LEASE_NAME_SHEET": nm, "LEASE_NUM": ln})
            if mapping_rows:
                pd.DataFrame(mapping_rows).to_excel(writer, sheet_name="QA_LeaseName_to_Leases", index=False)
        

    print(f"✅ Wrote multi-year matrix to {args.out}")

if __name__ == "__main__":
    main()
