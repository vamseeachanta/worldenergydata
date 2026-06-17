"""Julia field economics at by-field / by-block / by-well granularity.

Reuses the validated V30 tieback15 methodology (matched to golden baseline to
~0.001%). Production from local OGOR-A .bin pickles; WTI deck + assumptions +
D&C days from FDAS_V30 workbooks. Two vintages: V30 (through 2025-05) and
LATEST (through last available OGOR month).
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
BIN_DIR = REPO / "data/modules/bsee/bin/historical_production_yearly"
V30 = REPO / "docs/modules/bsee/analysis/production/FDAS_V30"
JULIA_LEASE = "G20351"
FIRST_OIL = pd.Timestamp("2016-03-01")

# tieback15 assumptions (from lease_assumptions.xlsx)
DISC = 0.10
ROYALTY = 0.1875
VAR_OPEX = 6.0
FIXED_OPEX_MM_YR = 75.0
SURF_PER_WELL_MM = 250.0
BOOSTER_MM = 275.0
WI_FAC_MM = 100.0
MODU_RATE_MM = 0.8
WTI_FALLBACK = 60.0

COLS = [
    "LEASE_NUMBER", "COMPLETION_NAME", "PRODUCTION_DATE", "DAYS_ON_PROD",
    "PRODUCT_CODE", "MON_O_PROD_VOL", "MON_G_PROD_VOL", "MON_WTR_PROD_VOL",
    "API_WELL_NUMBER", "WELL_STAT_CD", "AREA_CODE_BLOCK_NUM", "OPERATOR_NUM",
    "SORT_NAME", "BOEM_FIELD", "INJECTION_VOLUME", "PROD_INTERVAL_CD",
    "FIRST_PROD_DATE", "UNIT_AGT_NUMBER", "UNIT_ALOC_SUFFIX",
]


def _read_bin_year(year):
    fn = "ogoradelimit.bin" if year == 2025 else f"ogora{year}delimit.bin"
    p = BIN_DIR / fn
    if not p.exists():
        return None
    raw = pd.read_pickle(p)
    lost = list(raw.columns)
    body = raw.copy(); body.columns = range(body.shape[1])
    head = pd.DataFrame([lost], columns=range(body.shape[1]))
    df = pd.concat([head, body], ignore_index=True)
    df.columns = COLS[: df.shape[1]]
    return df


def load_julia():
    frames = []
    for y in range(2000, 2026):
        d = _read_bin_year(y)
        if d is not None:
            frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["LEASE_NUMBER"] = (df["LEASE_NUMBER"].astype(str).str.strip()
                          .str.replace('"', "", regex=False).str.replace(" ", "", regex=False).str.upper())
    df = df[df["LEASE_NUMBER"] == JULIA_LEASE].copy()
    df["oil"] = pd.to_numeric(df["MON_O_PROD_VOL"].astype(str).str.replace('"', "", regex=False).str.strip(), errors="coerce").fillna(0.0)
    df["gas"] = pd.to_numeric(df["MON_G_PROD_VOL"].astype(str).str.replace('"', "", regex=False).str.strip(), errors="coerce").fillna(0.0)
    df["api"] = pd.to_numeric(df["API_WELL_NUMBER"], errors="coerce")
    df["block"] = df["AREA_CODE_BLOCK_NUM"].astype(str).str.strip().str.replace('"', "", regex=False)
    df["date"] = pd.to_datetime(pd.to_numeric(df["PRODUCTION_DATE"], errors="coerce"), format="%Y%m", errors="coerce")
    df = df[(df["date"] >= "2000-09-01") & (df["oil"] > 0) & (df["date"] >= FIRST_OIL)]
    return df


def load_wti():
    w = pd.read_excel(V30 / "wti_monthly.xlsx")
    w["Month"] = pd.to_datetime(w["Month"])
    return w[["Month", "WTI_USD"]]


def load_dnc():
    d = pd.read_excel(V30 / "drilling_and_completion_days.xlsx")
    s = d["SURF_LEASE_NUM"].astype(str).str.upper().str.replace('"', "", regex=False).str.replace(" ", "", regex=False)
    d = d[s == JULIA_LEASE].copy()
    d["api"] = pd.to_numeric(d["API_WELL_NUMBER"], errors="coerce")
    d["drill"] = pd.to_numeric(d["DRILLING_DAYS"], errors="coerce").fillna(0.0)
    d["comp"] = pd.to_numeric(d["COMPLETION_DAYS"], errors="coerce").fillna(0.0)
    d["spud"] = pd.to_datetime(d["WELL_SPUD_DATE"], errors="coerce")
    d["td"] = pd.to_datetime(d["TOTAL_DEPTH_DATE"], errors="coerce")
    return d


def month_floor(ts):
    return pd.Timestamp(ts).to_period("M").to_timestamp()


def excel_mirr(cf, disc):
    nz = np.where(np.abs(cf) > 1e-6)[0]
    if nz.size == 0:
        return float("nan")
    c = cf[nz[0]:nz[-1] + 1]
    if not (np.any(c > 0) and np.any(c < 0)):
        return float("nan")
    n = c.size - 1
    r = (1 + disc) ** (1 / 12) - 1
    fv = sum(c[t] * (1 + r) ** (n - t) for t in range(c.size) if c[t] > 0)
    pv = sum(c[t] / (1 + r) ** t for t in range(c.size) if c[t] < 0)
    if pv >= 0 or fv <= 0:
        return float("nan")
    return (fv / -pv) ** (1 / n) - 1


def npv_trimmed(cf, disc):
    nz = np.where(np.abs(cf) > 1e-6)[0]
    if nz.size == 0:
        return 0.0
    c = cf[nz[0]:nz[-1] + 1]
    r = (1 + disc) ** (1 / 12) - 1
    return float(np.sum(c / np.array([(1 + r) ** t for t in range(len(c))])))


def monthly_dnc_for_wells(dnc_rows, fopw):
    """Allocate D&C monthly: drilling forward from spud, completion backward from
    well first-oil (FOPW) else TD. Mirrors V30 generator. Returns dict month->cost."""
    out = {}
    for _, r in dnc_rows.iterrows():
        dd, cd = r["drill"], r["comp"]
        sp, td, api = r["spud"], r["td"], r["api"]
        if pd.notna(sp) and dd > 0:
            cur = pd.Timestamp(sp).normalize(); left = int(round(dd))
            while left > 0:
                m0 = pd.Timestamp(cur.year, cur.month, 1); m1 = m0 + pd.offsets.MonthBegin(1)
                alloc = min(left, (m1 - cur).days)
                out[month_floor(m0)] = out.get(month_floor(m0), 0.0) + alloc * MODU_RATE_MM * 1e6
                left -= alloc; cur = m1
        end = fopw.get(api, pd.NaT)
        if pd.isna(end):
            end = td
        if pd.notna(end) and cd > 0:
            cur = month_floor(end) + pd.offsets.MonthEnd(0); left = int(round(cd))
            while left > 0:
                m0 = pd.Timestamp(cur.year, cur.month, 1)
                dim = (m0 + pd.offsets.MonthBegin(1) - pd.Timedelta(days=1)).day
                alloc = min(left, dim)
                out[month_floor(m0)] = out.get(month_floor(m0), 0.0) + alloc * MODU_RATE_MM * 1e6
                left -= alloc; cur = m0 - pd.Timedelta(days=1)
    return out


def economics_for_unit(prod_m, wti, fopw, field_fo, share, end_date,
                       unit_producers, dnc_producers, nonprod_dnc_field):
    """prod_m: DataFrame[date, oil, gas] for the unit (already filtered).
    share: unit's fraction of field oil (allocates shared costs).
    unit_producers: set of producing APIs in this unit.
    dnc_producers: D&C rows for producing wells only (own-bore costs).
    nonprod_dnc_field: $ of field D&C from non-producing/appraisal bores (shared)."""
    prod_m = prod_m[prod_m["date"] <= end_date].copy()
    if prod_m.empty:
        return None
    g = prod_m.groupby("date", as_index=False).agg(oil=("oil", "sum"), gas=("gas", "sum")).sort_values("date")
    m = g.merge(wti, left_on="date", right_on="Month", how="left")
    m["WTI_USD"] = m["WTI_USD"].fillna(WTI_FALLBACK)
    revenue = float((m["oil"] * m["WTI_USD"]).sum())
    royalty = revenue * ROYALTY
    oil_total = float(m["oil"].sum())
    gas_total = float(g["gas"].sum())
    var_opex = oil_total * VAR_OPEX
    prod_months = int((m["oil"] > 0).sum())
    fixed_opex = (FIXED_OPEX_MM_YR * 1e6 / 12) * prod_months * share  # field-level cost, share-allocated

    n_prod = len(unit_producers)
    surf = SURF_PER_WELL_MM * 1e6 * n_prod          # SURF per PRODUCER (not per bore)
    shared_fac = (BOOSTER_MM + WI_FAC_MM) * 1e6 * share
    own_dnc = float((dnc_producers["drill"].sum() + dnc_producers["comp"].sum()) * MODU_RATE_MM * 1e6)
    alloc_nonprod_dnc = nonprod_dnc_field * share
    dnc_total = own_dnc + alloc_nonprod_dnc

    # build monthly timeline
    start = field_fo - pd.DateOffset(months=24)
    rng = pd.date_range(month_floor(start), month_floor(pd.Timestamp(end_date)), freq="MS")
    cf = pd.Series(0.0, index=rng)
    # ops cashflow (rev - royalty - var opex - fixed opex)
    ops = (m["oil"] * m["WTI_USD"]) * (1 - ROYALTY) - m["oil"] * VAR_OPEX
    # fixed opex is a FIELD-level cost ($75M/yr); allocate to this unit by production share
    fix_vec = np.where(m["oil"].values > 0, FIXED_OPEX_MM_YR * 1e6 / 12 * share, 0.0)
    for d, val, fx in zip(m["date"], ops.values, fix_vec):
        md = month_floor(d)
        if md in cf.index:
            cf[md] += val - fx
    # own-bore D&C monthly (real spud/completion timing)
    for md, c in monthly_dnc_for_wells(dnc_producers, fopw).items():
        if md in cf.index:
            cf[md] -= c
        else:
            cf[md] = cf.get(md, 0.0) - c
    # SURF booked at each producer's first oil
    for api in unit_producers:
        fo = fopw.get(api, field_fo)
        md = month_floor(fo if pd.notna(fo) else field_fo)
        if md in cf.index:
            cf[md] -= SURF_PER_WELL_MM * 1e6
    # shared facilities + allocated non-producer D&C lump at field first oil
    md_field = month_floor(field_fo)
    if md_field in cf.index:
        cf[md_field] -= shared_fac + alloc_nonprod_dnc

    cfa = cf.sort_index().values.astype(float)
    npv = npv_trimmed(cfa, DISC)
    mirr_m = excel_mirr(cfa, DISC)
    mirr_a = (1 + mirr_m) ** 12 - 1 if not math.isnan(mirr_m) else float("nan")
    net = float(cf.sum())
    capex = dnc_total + surf + shared_fac
    # payback: first month cumulative CF >= 0
    cum = np.cumsum(cfa)
    pb_idx = np.where(cum >= 0)[0]
    payback_yr = float(pb_idx[0] - np.where(np.abs(cfa) > 1e-6)[0][0]) / 12 if pb_idx.size else None

    return {
        "oil_bbl": oil_total, "gas_mcf": gas_total, "prod_months": prod_months,
        "first_date": str(m["date"].min().date()), "last_date": str(m["date"].max().date()),
        "revenue_usd": revenue, "royalty_usd": royalty, "variable_opex_usd": var_opex,
        "fixed_opex_usd": fixed_opex, "dnc_total_usd": dnc_total, "surf_usd": surf,
        "shared_fac_usd": shared_fac, "facilities_usd": surf + shared_fac,
        "capex_usd": capex, "net_cashflow_usd": net, "npv_usd": npv,
        "mirr_annual": mirr_a, "payback_years": payback_yr, "wells": int(n_prod),
    }


def run(jdf, wti, dnc, end_date, label):
    fopw = jdf.sort_values(["api", "date"]).groupby("api")["date"].min().to_dict()
    sub = jdf[jdf["date"] <= end_date]
    field_oil = sub["oil"].sum()
    field_producers = set(sub.loc[sub["oil"] > 0, "api"].dropna().unique())

    # field D&C decomposition: own (matches a producing API) vs non-producer pool
    field_total_dnc = float((dnc["drill"].sum() + dnc["comp"].sum()) * MODU_RATE_MM * 1e6)
    dnc_prod_field = dnc[dnc["api"].isin(field_producers)]
    own_dnc_field = float((dnc_prod_field["drill"].sum() + dnc_prod_field["comp"].sum()) * MODU_RATE_MM * 1e6)
    nonprod_dnc_field = field_total_dnc - own_dnc_field

    def unit(grp, unit_apis):
        uprod = field_producers & set(unit_apis)
        share = grp[grp["date"] <= end_date]["oil"].sum() / field_oil if field_oil else 0
        dnc_u = dnc[dnc["api"].isin(uprod)]
        r = economics_for_unit(grp[["date", "oil", "gas"]], wti, fopw, FIRST_OIL, share, end_date,
                               uprod, dnc_u, nonprod_dnc_field)
        if r:
            r["share_pct"] = round(share * 100, 1)
        return r

    res = {"label": label, "end_date": end_date}
    res["field"] = unit(jdf, field_producers)
    blocks = {}
    for blk, grp in jdf.groupby("block"):
        r = unit(grp, set(grp["api"].dropna().unique()))
        if r:
            blocks[blk] = r
    res["by_block"] = blocks
    wells = {}
    namemap = dnc.dropna(subset=["api"]).groupby("api")["WELL_NAME"].first().to_dict()
    for api, grp in jdf.groupby("api"):
        if pd.isna(api):
            continue
        r = unit(grp, {api})
        if r:
            r["api"] = str(int(api))
            r["well_name"] = str(namemap.get(api, ""))
            r["block"] = str(grp["block"].mode().iloc[0]) if not grp["block"].mode().empty else ""
            wells[str(int(api))] = r
    res["by_well"] = wells
    return res


_jdf = load_julia()
_wti = load_wti()
_dnc = load_dnc()
latest_month = str(_jdf["date"].max().date())
out = {}
out["v30"] = run(_jdf, _wti, _dnc, "2025-05-31", "V30 (through May 2025)")
out["latest"] = run(_jdf, _wti, _dnc, latest_month, f"Latest (through {latest_month})")
(REPO / "reports/lower_tertiary/data/julia_granular_economics.json").write_text(json.dumps(out, indent=2, default=str))

# console summary
def line(name, r):
    return (f"{name:22} oil={r['oil_bbl']/1e6:6.2f}MMbbl rev=${r['revenue_usd']/1e6:8.1f}M "
            f"capex=${r['capex_usd']/1e6:8.1f}M NPV=${r['npv_usd']/1e6:8.1f}M "
            f"MIRR={r['mirr_annual']*100 if r['mirr_annual']==r['mirr_annual'] else float('nan'):5.1f}% "
            f"wells={r['wells']}")

for vint in ("v30", "latest"):
    R = out[vint]
    print(f"\n===== {R['label']} =====")
    print(line("FIELD (Julia)", R["field"]))
    print("-- by block --")
    for b, r in R["by_block"].items():
        print(line(f"  block {b}", r))
    print("-- by well --")
    for w, r in R["by_well"].items():
        print(line(f"  {r['well_name']}/{w[-4:]}", r))
print("\nGRANULAR DONE")
