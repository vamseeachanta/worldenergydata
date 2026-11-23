"""Reproduce V30 Julia financials from LOCAL OGOR-A .bin pickles.

Bridges the data-representation gap: the sanctioned reproducer reads OGOR zips
(absent locally); we monkeypatch its loader to read the present .bin pickles,
then run the UNCHANGED V30 financial methodology and validate vs golden baseline.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
import sys as _sys
_sys.path.insert(0, str(REPO / "src"))
BIN_DIR = REPO / "data/modules/bsee/bin/historical_production_yearly"

COLS = [
    "LEASE_NUMBER", "COMPLETION_NAME", "PRODUCTION_DATE", "DAYS_ON_PROD",
    "PRODUCT_CODE", "MON_O_PROD_VOL", "MON_G_PROD_VOL", "MON_WTR_PROD_VOL",
    "API_WELL_NUMBER", "WELL_STAT_CD", "AREA_CODE_BLOCK_NUM", "OPERATOR_NUM",
    "SORT_NAME", "BOEM_FIELD", "INJECTION_VOLUME", "PROD_INTERVAL_CD",
    "FIRST_PROD_DATE", "UNIT_AGT_NUMBER", "UNIT_ALOC_SUFFIX",
]


def _read_bin_year(year: int) -> pd.DataFrame | None:
    fn = "ogoradelimit.bin" if year == 2025 else f"ogora{year}delimit.bin"
    path = BIN_DIR / fn
    if not path.exists():
        return None
    raw = pd.read_pickle(path)
    # The pickle was saved headerless: the original first data row became the
    # column index. Restore it as a real data row so totals stay exact.
    lost_first = list(raw.columns)
    body = raw.copy()
    body.columns = range(body.shape[1])
    head = pd.DataFrame([lost_first], columns=range(body.shape[1]))
    df = pd.concat([head, body], ignore_index=True)
    df.columns = COLS[: df.shape[1]]
    return df


def patched_load_ogor_production(start_year: int = 2000, end_year: int = 2025) -> pd.DataFrame:
    frames = []
    for year in range(start_year, end_year + 1):
        df = _read_bin_year(year)
        if df is not None:
            frames.append(df)
    if not frames:
        raise FileNotFoundError("No OGOR .bin files loaded")
    df = pd.concat(frames, ignore_index=True)
    df["LEASE_NUMBER"] = (
        df["LEASE_NUMBER"].astype(str).str.strip()
        .str.replace('"', "", regex=False).str.replace(" ", "", regex=False).str.upper()
    )
    df["MON_O_PROD_VOL"] = pd.to_numeric(
        df["MON_O_PROD_VOL"].astype(str).str.replace('"', "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)
    for col in ("PRODUCT_CODE", "WELL_STAT_CD"):
        df[col] = (
            df[col].astype(str).str.strip().str.replace('"', "", regex=False).str.upper()
        )
    df["PRODUCTION_DATE"] = pd.to_numeric(df["PRODUCTION_DATE"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRODUCTION_DATE"], format="%Y%m", errors="coerce")
    return df


# --- monkeypatch both modules that resolve load_ogor_production ---
import worldenergydata.lower_tertiary.v30_reproducer as v30r
import worldenergydata.lower_tertiary.v30_financial_reproducer as v30f

v30r.load_ogor_production = patched_load_ogor_production
v30f.load_ogor_production = patched_load_ogor_production

from worldenergydata.lower_tertiary.v30_financial_reproducer import reproduce_v30_financials
from worldenergydata.lower_tertiary.v30_reproducer import load_golden_baseline

results = reproduce_v30_financials()
baseline = load_golden_baseline()

# Map baseline projects by display name
base_by_name = {p["display_name"]: p for p in baseline["projects"].values()}

rows = []
for dev_name, r in results.items():
    b = base_by_name.get(dev_name, {})
    rows.append({
        "field": dev_name,
        "repro_oil_bbl": None,  # filled below from production
        "repro_revenue_usd": r["revenue_usd"],
        "base_revenue_usd": b.get("revenue_usd"),
        "repro_npv_usd": r["npv_usd"],
        "base_npv_usd": b.get("npv_usd"),
        "repro_mirr_annual": r["mirr_annual"],
        "base_mirr_annual": b.get("mirr_annual"),
        "repro_net_cf": r["net_cashflow_usd"],
        "base_net_cf": b.get("net_cashflow_usd"),
        "repro_dnc": r["dnc_total_usd"],
        "base_dnc": b.get("dnc_total_usd"),
        "repro_fac": r["facilities_cost_usd"],
        "base_fac": b.get("facilities_cost_usd"),
    })

out = {"results": rows}
(REPO / "reports/lower_tertiary/data/julia_v30_reproduction.json").write_text(json.dumps(out, indent=2, default=str))

# Pretty console focus on Julia
def fmt(x):
    return f"{x:,.0f}" if isinstance(x, (int, float)) else str(x)

print("=== V30 REPRODUCTION vs GOLDEN BASELINE (from local .bin) ===")
hdr = f"{'field':14} {'metric':12} {'reproduced':>18} {'baseline':>18} {'Δ%':>8}"
print(hdr)
for row in rows:
    for metric, rk, bk in [
        ("revenue", "repro_revenue_usd", "base_revenue_usd"),
        ("npv", "repro_npv_usd", "base_npv_usd"),
        ("mirr_annual", "repro_mirr_annual", "base_mirr_annual"),
        ("net_cf", "repro_net_cf", "base_net_cf"),
        ("dnc_total", "repro_dnc", "base_dnc"),
        ("facilities", "repro_fac", "base_fac"),
    ]:
        rv, bv = row[rk], row[bk]
        try:
            d = (rv - bv) / bv * 100 if bv else float("nan")
        except Exception:
            d = float("nan")
        star = " <<<" if row["field"] == "Julia" else ""
        print(f"{row['field']:14} {metric:12} {fmt(rv):>18} {fmt(bv):>18} {d:>7.2f}%{star}")
print("DONE")
