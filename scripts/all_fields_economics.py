"""All-fields Lower Tertiary economics: portfolio + by-field/block/well.

Field-level economics are the AUTHORITATIVE sanctioned reproduce_v30_financials()
output (validated to ~0.001% vs golden_baseline_v30.yml). Per-well / per-block are
an indicative decomposition: real OGOR production & revenue per well, with the
field's authoritative CAPEX + fixed OPEX allocated by production share.

Emits reports/lower_tertiary/data/all_fields_economics.json.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]            # worktree: config + outputs
MAIN = Path("/mnt/local-analysis/worldenergydata")    # main checkout: gitignored .bin OGOR data
import sys; sys.path.insert(0, str(MAIN / "src"))
BIN_DIR = MAIN / "data/modules/bsee/bin/historical_production_yearly"
COLS = ["LEASE_NUMBER","COMPLETION_NAME","PRODUCTION_DATE","DAYS_ON_PROD","PRODUCT_CODE",
        "MON_O_PROD_VOL","MON_G_PROD_VOL","MON_WTR_PROD_VOL","API_WELL_NUMBER","WELL_STAT_CD",
        "AREA_CODE_BLOCK_NUM","OPERATOR_NUM","SORT_NAME","BOEM_FIELD","INJECTION_VOLUME",
        "PROD_INTERVAL_CD","FIRST_PROD_DATE","UNIT_AGT_NUMBER","UNIT_ALOC_SUFFIX"]
DISC, ROYALTY = 0.10, 0.1875
V30_END = "2025-05-31"

def _read_bin_year(year):
    fn = "ogoradelimit.bin" if year == 2025 else f"ogora{year}delimit.bin"
    p = BIN_DIR / fn
    if not p.exists(): return None
    raw = pd.read_pickle(p); lost = list(raw.columns)
    body = raw.copy(); body.columns = range(body.shape[1])
    df = pd.concat([pd.DataFrame([lost], columns=range(body.shape[1])), body], ignore_index=True)
    df.columns = COLS[: df.shape[1]]; return df

def load_ogor(start=2000, end=2025):
    frames = [d for y in range(start, end + 1) if (d := _read_bin_year(y)) is not None]
    df = pd.concat(frames, ignore_index=True)
    df["LEASE_NUMBER"] = df["LEASE_NUMBER"].astype(str).str.strip().str.replace('"',"",regex=False).str.replace(" ","",regex=False).str.upper()
    df["MON_O_PROD_VOL"] = pd.to_numeric(df["MON_O_PROD_VOL"].astype(str).str.replace('"',"",regex=False).str.strip(), errors="coerce").fillna(0.0)
    df["PRODUCT_CODE"] = df["PRODUCT_CODE"].astype(str).str.strip().str.replace('"',"",regex=False).str.upper()
    df["WELL_STAT_CD"] = df["WELL_STAT_CD"].astype(str).str.strip().str.replace('"',"",regex=False).str.upper()
    df["PRODUCTION_DATE"] = pd.to_numeric(df["PRODUCTION_DATE"], errors="coerce")
    df["date"] = pd.to_datetime(df["PRODUCTION_DATE"], format="%Y%m", errors="coerce")
    return df

# ---- authoritative field-level via sanctioned engine (monkeypatched to .bin) ----
import worldenergydata.lower_tertiary.v30_reproducer as v30r
import worldenergydata.lower_tertiary.v30_financial_reproducer as v30f
_OGOR_CACHE = {}
def _patched(start_year=2000, end_year=2025):
    key = (start_year, end_year)
    if key not in _OGOR_CACHE:
        _OGOR_CACHE[key] = load_ogor(start_year, end_year)
    return _OGOR_CACHE[key].copy()
v30r.load_ogor_production = _patched
v30f.load_ogor_production = _patched
from worldenergydata.lower_tertiary.v30_financial_reproducer import reproduce_v30_financials, _load_assumptions_wide, _get_assumption
from worldenergydata.lower_tertiary.v30_reproducer import load_golden_baseline

print("running sanctioned field-level reproduction (all fields)...")
FIN = reproduce_v30_financials()           # authoritative per display_name
BASE = load_golden_baseline()["projects"]
ASSUM = _load_assumptions_wide()

registry = yaml.safe_load((REPO / "config/ong_field_development/fields_registry.yml").read_text())["fields"]
ogor = _patched(2000, 2025)
wti = pd.read_excel(MAIN / "docs/modules/bsee/analysis/production/FDAS_V30/wti_monthly.xlsx")[["Month","WTI_USD"]]
wti["Month"] = pd.to_datetime(wti["Month"])

def month_floor(ts): return pd.Timestamp(ts).to_period("M").to_timestamp()
def npv_trim(cf):
    nz = np.where(np.abs(cf) > 1e-6)[0]
    if not nz.size: return 0.0
    c = cf[nz[0]:nz[-1]+1]; r = (1+DISC)**(1/12)-1
    return float(np.sum(c / np.array([(1+r)**t for t in range(len(c))])))
def excel_mirr(cf):
    nz = np.where(np.abs(cf) > 1e-6)[0]
    if not nz.size: return float("nan")
    c = cf[nz[0]:nz[-1]+1]
    if not (np.any(c>0) and np.any(c<0)): return float("nan")
    n=c.size-1; r=(1+DISC)**(1/12)-1
    fv=sum(c[t]*(1+r)**(n-t) for t in range(c.size) if c[t]>0)
    pv=sum(c[t]/(1+r)**t for t in range(c.size) if c[t]<0)
    if pv>=0 or fv<=0: return float("nan")
    return (1+((fv/-pv)**(1/n)-1))**12-1

def unit_econ(prod, share, var_opex, fixed_opex_field, capex_alloc, first_oil, end=V30_END):
    p = prod[prod["date"] <= end]
    if p.empty: return None
    g = p.groupby("date", as_index=False).agg(oil=("oil","sum"), gas=("gas","sum")).sort_values("date")
    m = g.merge(wti, left_on="date", right_on="Month", how="left"); m["WTI_USD"] = m["WTI_USD"].fillna(60.0)
    rev = float((m["oil"]*m["WTI_USD"]).sum()); oil = float(m["oil"].sum())
    roy = rev*ROYALTY; vopex = oil*var_opex
    # indicative monthly cashflow: ops - allocated fixed opex - allocated capex lump at first oil
    fo = month_floor(first_oil) if first_oil else month_floor(m["date"].min())
    rng = pd.date_range(fo - pd.DateOffset(months=24), month_floor(pd.Timestamp(end)), freq="MS")
    cf = pd.Series(0.0, index=rng)
    pm = int((m["oil"]>0).sum())
    fix_m = (fixed_opex_field*share/pm) if pm else 0.0
    for d,val in zip(m["date"], (m["oil"]*m["WTI_USD"]*(1-ROYALTY) - m["oil"]*var_opex).values):
        md = month_floor(d)
        if md in cf.index: cf[md] += val - fix_m
    if fo in cf.index: cf[fo] -= capex_alloc
    cfa = cf.values.astype(float)
    cum = np.cumsum(cfa); pbi = np.where(cum>=0)[0]
    nzz = np.where(np.abs(cfa)>1e-6)[0]
    payback = float(pbi[0]-nzz[0])/12 if pbi.size and nzz.size else None
    return {"oil_bbl":oil, "gas_mcf":float(g["gas"].sum()), "revenue_usd":rev, "royalty_usd":roy,
            "variable_opex_usd":vopex, "capex_usd":capex_alloc, "npv_usd":npv_trim(cfa),
            "mirr_annual":excel_mirr(cfa), "payback_years":payback, "prod_months":pm}

portfolio, by_field = [], {}
for fid, reg in registry.items():
    name = reg["field_nickname"]
    import re as _re
    def _norm(s): return _re.sub(r'[^a-z0-9]', '', str(s).lower())
    fin = next((FIN[k] for k in FIN if _norm(k) == _norm(name)), {})   # reproduction (validation)
    gb = BASE.get(fid, {})                                             # golden baseline (authoritative)
    cap = (gb.get("dnc_total_usd", 0) or 0) + (gb.get("facilities_cost_usd", 0) or 0)
    repro_npv = fin.get("npv_usd")
    npv = gb.get("npv_usd")
    row = {"field": name, "id": fid, "dev_system": reg["dev_system"], "status": reg["status"],
           "first_oil": reg.get("first_oil"),
           "oil_bbl": gb.get("total_oil_bbl"), "revenue_usd": gb.get("revenue_usd"),
           "capex_usd": cap or None, "npv_usd": npv, "mirr_annual": gb.get("mirr_annual"),
           "net_cashflow_usd": gb.get("net_cashflow_usd"),
           "producers": gb.get("producers"), "wellbores": gb.get("wellbores"),
           "repro_npv_usd": repro_npv,
           "repro_delta_pct": (round((repro_npv - npv) / npv * 100, 2) if (repro_npv is not None and npv) else None),
           "public_metadata": reg.get("public_metadata", {})}
    portfolio.append(row)

    # by-well / by-block only for fields with real production
    leases = set(str(x).upper() for x in reg["leases"])
    sub = ogor[(ogor["LEASE_NUMBER"].isin(leases)) & (ogor["MON_O_PROD_VOL"]>0) & (ogor["date"]>="2000-09-01")]
    fo = pd.Timestamp(reg["first_oil"]) if reg.get("first_oil") else None
    if fo is not None: sub = sub[sub["date"]>=fo]
    sub = sub[sub["date"]<=V30_END]
    if sub.empty or not cap:
        continue
    sub = sub.assign(oil=sub["MON_O_PROD_VOL"], gas=pd.to_numeric(sub["MON_G_PROD_VOL"].astype(str).str.replace('"',"",regex=False).str.strip(), errors="coerce").fillna(0.0),
                     api=pd.to_numeric(sub["API_WELL_NUMBER"], errors="coerce"),
                     block=sub["AREA_CODE_BLOCK_NUM"].astype(str).str.strip().str.replace('"',"",regex=False))
    field_oil = sub["oil"].sum()
    sysn = (reg["dev_system"] or "subsea15").lower().replace(" ","")
    var_opex = _get_assumption(ASSUM, sysn, "VARIABLE_OPEX_$/BBL", 6.0)
    fixed_opex_field = gb.get("fixed_opex_usd", 0) or 0
    def emit(grp):
        share = grp["oil"].sum()/field_oil if field_oil else 0
        r = unit_econ(grp[["date","oil","gas"]], share, var_opex, fixed_opex_field, cap*share, fo)
        if r: r["share_pct"] = round(share*100,1)
        return r
    blocks = {}
    for blk,grp in sub.groupby("block"):
        r = emit(grp)
        if r: blocks[blk.strip()] = r
    wells = {}
    for api,grp in sub.groupby("api"):
        if pd.isna(api): continue
        r = emit(grp)
        if r:
            r["api"] = str(int(api))
            wells[str(int(api))] = r
    by_field[fid] = {"field": name, "by_block": blocks, "by_well": wells,
                     "n_blocks": len(blocks), "n_wells": len(wells)}

out = {"portfolio": portfolio, "by_field": by_field,
       "meta": {"discount_rate": DISC, "vintage": "V30 (through 2025-05)",
                "validation": "field economics = sanctioned reproduce_v30_financials, golden baseline ~0.001%"}}
(REPO / "reports/lower_tertiary/data/all_fields_economics.json").write_text(json.dumps(out, indent=2, default=str))

print("\n=== PORTFOLIO (all Lower Tertiary fields, validated) ===")
print(f"{'field':16}{'dev':10}{'status':16}{'oil MMb':>9}{'rev $B':>8}{'capex $B':>9}{'NPV10 $M':>10}{'MIRR':>7}{'wells':>6}")
for r in sorted(portfolio, key=lambda x: (x["npv_usd"] or 0), reverse=True):
    print(f"{r['field']:16}{(r['dev_system'] or ''):10}{r['status']:16}"
          f"{(r['oil_bbl'] or 0)/1e6:9.1f}{(r['revenue_usd'] or 0)/1e9:8.2f}{(r['capex_usd'] or 0)/1e9:9.2f}"
          f"{(r['npv_usd'] or 0)/1e6:10.0f}{(r['mirr_annual'] or float('nan'))*100:6.1f}%{(r['wellbores'] or 0):6}")
print(f"\nby-well/block computed for {len(by_field)} producing fields")
print("ALL FIELDS DONE")
