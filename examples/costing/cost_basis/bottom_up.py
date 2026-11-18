"""Bottom-up cost basis for offshore projects, set against the reported cost package by package (costing part 3, r1).

For a project the estimate is the sum of:

- wells: wells x drilling and completion days per well x rig day rate (the drilling contract), plus the same rig days x
  rig day rate x spread factor (drilling and well services);
- facility: hull or jacket tonnage x (steel price + fabrication rate); topsides dry weight x (structural steel share x
  steel price + equipment and bulk rate + fabrication rate); engineering hours per tonne x engineering rate;
- subsea: subsea trees x cost per tree; flowline length x SURF cost per km; host modifications for a tieback;
- installation: a share of the fabricated facility and subsea cost;
- owner's costs: a share of the subtotal.

A probabilistic incident allowance is added beside it: the expected number of loss-of-well-control events (BSEE
events per wellbore spudded, times the project's wells) times the rig spread days lost per event times the day cost.
It is an allowance (an expected value), not a forecast.

Every input is read from the repository's data, derived from it with the rule stated here, or taken from
data/inputs.csv where it is marked ASSUMED with the date by which it is to be measured. The low and high envelope set
every ASSUMED input to its low or high value together, and the award-derived unit rates to their least and greatest.

Usage (from the repository root):
  python examples/costing/cost_basis/bottom_up.py
writes examples/costing/cost_basis/out/results.json, project_register.csv, worked.csv and award_unit_rates.csv.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import register  # noqa: E402

ROOT = HERE.parents[2]
COST = ROOT / "data" / "modules" / "cost" / "curated"
DATA = HERE / "data"
OUT = HERE / "out"
# BSEE wellbore drilling and completion days (spud to total depth; well activity report days after total depth);
# the source and its hash are in data/bsee_sources.csv.
DC_DAYS = DATA / "bsee_dc_days.csv"
LWC_PAGE = ROOT / "data" / "modules" / "marine_safety" / "raw" / "bsee_incident_statistics.html"
WORKED = ("Anchor", "Julia (initial phase)", "Martin Linge (ex-Hild)")
DC_NAME = {"Anchor": "Anchor", "Julia (initial phase)": "Julia"}
# Rig day rate from a project's own drilling award: value over firm term (the term is stated in the award row).
RIG_AWARD = {"Anchor": (2018, "Transocean", 5), "Martin Linge (ex-Hild)": (2012, "Maersk Drilling", 4)}
# Rig day rate from the drillship fleet average of the years the measured wells were drilled.
RIG_FLEET = {"Julia (initial phase)": ("rig_day_rate_drillship", "ultra_deepwater")}
# Tonnages stated in a project's own award rows: (asset class, contractor prefix, words in the scope, tonnes).
TONNAGE = {("Anchor", "hull_t"): ("production_hub", "Daewoo", "22,000 t", 22000),
           ("Martin Linge (ex-Hild)", "topsides_t"): ("production_hub", "Technip", "~25,000 t", 25000)}
TREES_ARE_WELLS = {"Anchor", "Julia (initial phase)"}  # subsea wells, one tree each; Martin Linge has platform wells


def _read(p: Path) -> list[dict]:
    with p.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _f(s):
    s = (s or "").strip()
    return float(s) if s else None


def inputs() -> dict:
    return {(r["KEY"], r["PROJECT"]): r for r in _read(DATA / "inputs.csv")}


def param(inp: dict, key: str, project: str, case: str = "base") -> float:
    r = inp.get((key, project)) or inp[(key, "*")]
    col = {"base": "VALUE", "low": "LOW", "high": "HIGH"}[case] if r["BASIS"] == "ASSUMED" else "VALUE"
    return float(r[col])


def ppi_steel() -> dict[int, float]:
    return {int(r["YEAR"]): float(r["VALUE"]) for r in _read(COST / "cost_component_timeseries.csv")
            if r["COMPONENT"] == "index_ppi_steel_mill"}


def steel_price(year: int, inp: dict, case: str = "base") -> float:
    idx = ppi_steel()
    return param(inp, "steel_price_2020", "*", case) * idx[year] / idx[2020]


def award_rates() -> dict:
    """SPS cost per tree and SURF cost per km from awards that state both a value and a count (data/award_unit_rates.csv).
    A band counts at its midpoint; a point or backlog at its value."""
    aw = _read(COST / "contract_awards.csv")
    out: dict[str, dict] = {}
    for u in _read(DATA / "award_unit_rates.csv"):
        m = [a for a in aw if a["PROJECT"] == u["PROJECT"] and a["AWARD_YEAR"] == u["AWARD_YEAR"]
             and a["ASSET_CLASS"] == u["ASSET_CLASS"] and a["CONTRACTOR"].startswith(u["CONTRACTOR_STARTS"])]
        if len(m) != 1 or u["COUNT_TEXT"] not in m[0]["SCOPE_DESC"]:
            raise SystemExit(f"award unit rate row does not match one award with its count text: {u}")
        a = m[0]
        lo, hi = _f(a["VALUE_LOW_MM"]), _f(a["VALUE_HIGH_MM"])
        val = (lo + hi) / 2 if hi is not None and lo is not None else (lo if lo is not None else hi)
        rate = val / float(u["COUNT"])
        out.setdefault(u["KIND"], {"rows": []})["rows"].append(
            {"project": u["PROJECT"], "year": int(u["AWARD_YEAR"]), "contractor": a["CONTRACTOR"], "count": float(u["COUNT"]),
             "count_text": u["COUNT_TEXT"], "value_mm": val, "basis": a["VALUE_BASIS"], "rate_mm": rate,
             "source_url": a["SOURCE_URL"]})
    for k, d in out.items():
        rs = [r["rate_mm"] for r in d["rows"]]
        d.update({"median": median(rs), "min": min(rs), "max": max(rs), "n": len(rs)})
    return out


def well_days(project: str, fid: int, first_oil: int) -> dict:
    """Drilling plus completion days per well, from the BSEE wellbores spudded from the sanction year to the year
    after first oil that carry days; per well = total days over distinct 10-digit API wells with days."""
    rows = [r for r in _read(DC_DAYS) if r["LEASE_NAME"] == DC_NAME[project] and r["WELL_SPUD_DATE"]]
    use = [r for r in rows if fid <= int(r["WELL_SPUD_DATE"][-4:]) <= first_oil + 1
           and int(r["DRILLING_DAYS"] or 0) + int(r["COMPLETION_DAYS"] or 0) > 0]
    drill = sum(int(r["DRILLING_DAYS"]) for r in use)
    comp = sum(int(r["COMPLETION_DAYS"]) for r in use)
    wells = len({r["API_WELL_NUMBER"][:10] for r in use})
    return {"wellbores": len(use), "wells": wells, "drilling_days": drill, "completion_days": comp,
            "per_well": (drill + comp) / wells, "years": sorted({int(r["WELL_SPUD_DATE"][-4:]) for r in use})}


def rig_rate(project: str, years: list[int] | None = None) -> dict:
    if project in RIG_AWARD:
        y, c, term = RIG_AWARD[project]
        a = [x for x in _read(COST / "contract_awards.csv") if x["PROJECT"] == project and x["AWARD_YEAR"] == str(y)
             and x["ASSET_CLASS"] == "drilling_rig" and x["CONTRACTOR"].startswith(c)]
        assert len(a) == 1, (project, a)
        v = float(a[0]["VALUE_LOW_MM"])
        return {"usd_per_day": v * 1e6 / (term * 365), "basis": f"{v:g} USD million over {term} years firm, {a[0]['CONTRACTOR']}",
                "source_url": a[0]["SOURCE_URL"]}
    comp, seg = RIG_FLEET[project]
    ts = [r for r in _read(COST / "cost_component_timeseries.csv") if r["COMPONENT"] == comp and r["SEGMENT"] == seg
          and r["FIGURE_TYPE"] == "fleet_average" and int(r["YEAR"]) in set(years or [])]
    vals = [float(r["VALUE"]) for r in ts]
    return {"usd_per_day": sum(vals) / len(vals), "basis": f"ultra-deepwater drillship fleet average, mean of {len(vals)} years "
            f"({min(int(r['YEAR']) for r in ts)} to {max(int(r['YEAR']) for r in ts)})",
            "source_url": "; ".join(sorted({r['SOURCE_URL'] for r in ts}))}


def tonnage(project: str, key: str) -> float | None:
    t = TONNAGE.get((project, key))
    if not t:
        return None
    cls, c, words, tonnes = t
    a = [x for x in _read(COST / "contract_awards.csv") if x["PROJECT"] == project and x["ASSET_CLASS"] == cls
         and x["CONTRACTOR"].startswith(c) and words in x["SCOPE_DESC"]]
    assert len(a) == 1, (project, key)
    return float(tonnes)


def lwc_frequency() -> dict:
    """BSEE loss-of-well-control events, fiscal 2007 to calendar 2023 (Oct 2006 to Dec 2023), over the wellbores
    spudded in the same window."""
    s = LWC_PAGE.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"<[^>]+>", "\n", s)
    t = re.sub(r"\s*\n\s*", "\n", t)
    heads = list(re.finditer(r"\n(20\d\d) (CY|FY|4th Qtr)\d?\n", t))
    counts = {}
    for i, h in enumerate(heads):
        block = t[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(t)]
        m = re.search(r"Loss of Well Control\n(\d+)", block)
        counts[f"{h.group(1)} {h.group(2)}"] = int(m.group(1))
    window = [k for k in counts if (k.endswith("FY") and 2007 <= int(k[:4]) <= 2017) or k == "2017 4th Qtr"
              or (k.endswith("CY") and 2018 <= int(k[:4]) <= 2023)]
    events = sum(counts[k] for k in window)
    w = _read(DATA / "bsee_window_counts.csv")[0]
    n = int(w["WELLBORES_SPUDDED"])
    return {"events": events, "periods": len(window), "wellbores": n, "per_wellbore": events / n,
            "window": f"{w['WINDOW_START']} to {w['WINDOW_END']}", "by_period": {k: counts[k] for k in window}}


def estimate(project: str, reg: dict, inp: dict, rates: dict, case: str = "base") -> dict:
    """Bottom-up cost in USD million by package, for one case (base, low or high envelope)."""
    r = reg[project]
    fid, fo = int(r["fid_year"]), int(r["first_oil_year"])
    wells = r["wells"] if r["wells"] is not None else param(inp, "wells", project, case)
    if project in DC_NAME:
        wd = well_days(project, fid, fo)
        dpw = wd["per_well"]
    else:
        wd, dpw = None, param(inp, "days_per_well", project, case)
    rig = rig_rate(project, wd["years"] if wd else None)
    spread = param(inp, "spread_factor", "*", case)
    day_cost = rig["usd_per_day"] * (1 + spread) / 1e6
    p = {"wells_rig": wells * dpw * rig["usd_per_day"] / 1e6, "wells_services": wells * dpw * rig["usd_per_day"] * spread / 1e6}
    yr = int(param(inp, "fab_year", project)) if (("fab_year", project) in inp) else fid + 1
    ps = steel_price(yr, inp, case)
    hull = tonnage(project, "hull_t") or 0.0
    jacket = param(inp, "jacket_t", project, case) if ("jacket_t", project) in inp else 0.0
    top = tonnage(project, "topsides_t") or (param(inp, "topsides_t", project, case) if ("topsides_t", project) in inp else 0.0)
    eh_s, eh_t, er = (param(inp, k, "*", case) for k in ("eng_hours_structure", "eng_hours_topsides", "eng_rate"))
    p["hull"] = hull * (ps + param(inp, "hull_fab_rate", "*", case)) / 1e6
    p["jacket"] = jacket * (ps + param(inp, "jacket_fab_rate", "*", case)) / 1e6
    share = param(inp, "topsides_steel_share", "*", case)
    p["topsides"] = top * (share * ps + param(inp, "topsides_equipment_rate", "*", case)
                           + param(inp, "topsides_fab_rate", "*", case)) / 1e6
    p["engineering_structure"] = (hull + jacket) * eh_s * er / 1e6
    p["engineering_topsides"] = top * eh_t * er / 1e6
    pick = {"base": "median", "low": "min", "high": "max"}[case]
    trees = wells if project in TREES_ARE_WELLS else 0
    p["sps"] = trees * rates["sps_per_tree"][pick]
    km = param(inp, "surf_km", project, case) if ("surf_km", project) in inp else 0.0
    p["surf"] = km * rates["surf_per_km"][pick]
    p["host_mod"] = param(inp, "host_mod", project, case) if ("host_mod", project) in inp else 0.0
    fab = p["hull"] + p["jacket"] + p["topsides"] + p["sps"] + p["surf"] + p["host_mod"]
    p["installation"] = fab * param(inp, "installation_share", "*", case)
    sub = sum(p.values())
    p["owner"] = sub * param(inp, "owner_share", "*", case)
    total = sum(p.values())
    lwc = lwc_frequency()
    lam = wells * lwc["per_wellbore"]
    consequence = param(inp, "lwc_days_lost", "*", case) * day_cost
    return {"project": project, "case": case, "packages": p, "total": total,
            "inputs": {"wells": wells, "days_per_well": dpw, "rig_usd_per_day": rig["usd_per_day"], "rig_basis": rig["basis"],
                       "rig_source": rig["source_url"], "spread_factor": spread, "day_cost_mm": day_cost,
                       "steel_usd_t": ps, "fab_year": yr, "hull_t": hull, "jacket_t": jacket, "topsides_t": top,
                       "trees": trees, "surf_km": km, "well_days": wd},
            "incident": {"expected_events": lam, "p_at_least_one": 1 - math.exp(-lam), "consequence_mm": consequence,
                         "allowance_mm": lam * consequence}}


def reported_packages(project: str) -> dict:
    """Public award values by package, at low and high bound, with the count of awards without a value."""
    out: dict[str, dict] = {}
    for a in _read(COST / "contract_awards.csv"):
        if a["PROJECT"] != project:
            continue
        k = register.award_package(a)
        d = out.setdefault(k, {"low": 0.0, "high": 0.0, "valued": 0, "not_public": 0, "bases": []})
        if register.award_has_value(a):
            lo, hi = _f(a["VALUE_LOW_MM"]), _f(a["VALUE_HIGH_MM"])
            d["low"] += lo if lo is not None else hi
            d["high"] += hi if hi is not None else lo
            d["valued"] += 1
            d["bases"].append(a["VALUE_BASIS"])
        else:
            d["not_public"] += 1
    return out


def sensitivity(base: dict) -> list[dict]:
    """Percent change in the total for a 1 % change in each package's driving input (linear: the package share)."""
    t = base["total"]
    own = base["packages"]["owner"]
    rows = [{"package": k, "factor": 100.0 * v * (1 + (own / (t - own))) / t / 100.0} for k, v in base["packages"].items()
            if k != "owner" and v > 0]
    return sorted(rows, key=lambda r: -r["factor"])


def build() -> dict:
    reg_built = register.build(ROOT)
    reg = {r["project"]: r for r in reg_built["rows"]}
    inp = inputs()
    rates = award_rates()
    worked = []
    for p in WORKED:
        cases = {c: estimate(p, reg, inp, rates, c) for c in ("base", "low", "high")}
        r = reg[p]
        b = cases["base"]
        worked.append({"project": p, "base": b, "low": cases["low"]["total"], "high": cases["high"]["total"],
                       "reported": {"sanction_usd_mm": r["sanction_usd_mm"], "sanction_local": r["sanction_local"],
                                    "final_mm": r["final_mm"], "final_ccy": r["final_ccy"], "final_kind": r["final_kind"],
                                    "packages": reported_packages(p)},
                       "vs_sanction_pct": 100.0 * (b["total"] / r["sanction_usd_mm"] - 1.0),
                       "low_vs_sanction_pct": 100.0 * (cases["low"]["total"] / r["sanction_usd_mm"] - 1.0),
                       "high_vs_sanction_pct": 100.0 * (cases["high"]["total"] / r["sanction_usd_mm"] - 1.0),
                       "sensitivity": sensitivity(b),
                       "register": {k: r[k] for k in ("operator", "region", "water_depth_m", "development_type", "facility",
                                                      "wells", "bsee_wellbores", "fid_year", "first_oil_year")}})
    assumed = [dict(r, KEY=k[0], PROJECT_SCOPE=k[1]) for k, r in inp.items() if r["BASIS"] == "ASSUMED"]
    recs = {"inputs": {**reg_built["inputs"], **{str(p.relative_to(ROOT)).replace("\\", "/"): register.sha256(p) for p in
                                                  [DC_DAYS, LWC_PAGE, DATA / "inputs.csv", DATA / "award_unit_rates.csv",
                                                   DATA / "bsee_window_counts.csv", COST / "cost_component_timeseries.csv"]}}}
    return {"coverage": reg_built["coverage"], "register_updates": reg_built["updates"], "rates": rates,
            "lwc": lwc_frequency(), "worked": worked, "assumed": assumed, "record": recs, "_rows": reg_built["rows"]}


def main() -> int:
    res = build()
    OUT.mkdir(exist_ok=True)
    register.write(OUT, {"rows": res.pop("_rows")})
    with (OUT / "worked.csv").open("w", encoding="utf-8", newline="\n") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["project", "package", "bottom_up_usd_mm"])
        for x in res["worked"]:
            for k, v in x["base"]["packages"].items():
                w.writerow([x["project"], k, f"{v:.1f}"])
            w.writerow([x["project"], "total", f"{x['base']['total']:.1f}"])
    with (OUT / "award_unit_rates.csv").open("w", encoding="utf-8", newline="\n") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["kind", "project", "year", "contractor", "count", "value_usd_mm", "basis", "rate_usd_mm", "source_url"])
        for k, d in res["rates"].items():
            for r in d["rows"]:
                w.writerow([k, r["project"], r["year"], r["contractor"], f"{r['count']:g}", f"{r['value_mm']:g}", r["basis"],
                            f"{r['rate_mm']:.2f}", r["source_url"]])
    (OUT / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    sys.stdout.reconfigure(encoding="utf-8")
    c = res["coverage"]
    print(f"{c['projects']} projects; {c['with_sanction']} with sanction cost; {c['with_package_split']} with a package split")
    for x in res["worked"]:
        print(f"{x['project']}: bottom-up {x['base']['total']:.0f} ({x['low']:.0f} to {x['high']:.0f}) against sanction "
              f"{x['reported']['sanction_usd_mm']:g}: {x['vs_sanction_pct']:+.1f} %")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
