"""Project register for the costing series, part 3: every offshore project with a cost record in this repository.

The register joins, by project name, the repository's curated and staged cost tables:

- data/modules/cost/curated/sanctioned_projects.csv (curated sanction estimates, 80 projects);
- data/modules/cost/staging/*-2016-2026.csv (staged research rows by region; rows marked as a cost update of a project
  already in the register are kept as statements of that project, not as new projects);
- data/modules/cost/curated/cost_revision_trails.csv (dated cost statements; adds the projects that have a trail only);
- data/modules/cost/curated/contract_awards.csv (public contract awards, grouped into packages);
- examples/costing/cost_basis/data/bsee_deepwater_field_wells.csv (BSEE wellbores and field water depth, US Gulf
  projects matched by BSEE field nickname in data/gom_field_map.csv).

A value is kept as its source states it; a cell with no value in any source is left blank and counted as a gap.
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COST = ROOT / "data" / "modules" / "cost"
DATA = HERE / "data"
STAGING = ("americas-2016-2026.csv", "asia-pacific-caspian-2016-2026.csv", "europe-2016-2026.csv")
# Staged rows that restate a project already in the register (a later cost or the original estimate).
UPDATE_OF = {
    "Barossa (cost update 2024)": "Barossa",
    "Scarborough Energy Project incl. Pluto Train 2 (cost update 2024)": "Scarborough (incl. Pluto Train 2)",
    "Balder Future (Balder X) - original PDO estimate [UPDATE to existing row]": "Balder X / Balder Future",
}
# Contract award asset classes, grouped into the packages a project is let in.
PACKAGE = {"production_hub": "facility", "drilling_rig": "drilling", "sps": "subsea", "surf": "subsea",
           "installation": "installation"}
VALUED = {"point", "band", "backlog", "range", "lease_contract", "combined"}
FT_TO_M = 0.3048


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _num(s) -> float | None:
    s = (s or "").strip()
    try:
        return float(s) if s else None
    except ValueError:
        return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def award_package(a: dict) -> str:
    """The package of an award: its asset class, with drilling and well services in 'other' counted as drilling."""
    if a["ASSET_CLASS"] == "other" and "drilling" in a["SCOPE_DESC"].lower():
        return "drilling"
    return PACKAGE.get(a["ASSET_CLASS"], "other")


def award_has_value(a: dict) -> bool:
    return a["VALUE_BASIS"] in VALUED and (_num(a["VALUE_LOW_MM"]) is not None or _num(a["VALUE_HIGH_MM"]) is not None)


def build(root: Path = ROOT) -> dict:
    cost = root / "data" / "modules" / "cost"
    curated = _read(cost / "curated" / "sanctioned_projects.csv")
    staged = [dict(r, _file=f) for f in STAGING for r in _read(cost / "staging" / f)]
    trails = _read(cost / "curated" / "cost_revision_trails.csv")
    awards = _read(cost / "curated" / "contract_awards.csv")
    bsee = {r["FIELD_NAME_CODE"]: r for r in _read(DATA / "bsee_deepwater_field_wells.csv")}
    gmap = {r["PROJECT"]: r for r in _read(DATA / "gom_field_map.csv")}

    reg: dict[str, dict] = {}
    for r in curated:
        reg[r["PROJECT"]] = dict(r, TIER="curated")
    updates = []
    for r in staged:
        p = r["PROJECT"]
        if p in UPDATE_OF:
            updates.append((UPDATE_OF[p], r))
        elif p not in reg:
            reg[p] = dict(r, TIER="staged")
    for t in trails:
        if t["PROJECT"] not in reg:
            reg[t["PROJECT"]] = {"PROJECT": t["PROJECT"], "TIER": "trail"}

    by_trail: dict[str, list[dict]] = {}
    for t in trails:
        if _num(t["VALUE_MM"]) is not None:
            by_trail.setdefault(t["PROJECT"], []).append(t)
    by_award: dict[str, list[dict]] = {}
    for a in awards:
        by_award.setdefault(a["PROJECT"], []).append(a)
    upd: dict[str, list[dict]] = {}
    for parent, r in updates:
        upd.setdefault(parent, []).append(r)

    rows = []
    for p, r in reg.items():
        tr = by_trail.get(p, [])
        sanc = _num(r.get("SANCTIONED_CAPEX_USD_MM"))
        sanc_src = r.get("SOURCE_URL", "") if sanc is not None else ""
        if sanc is None:
            s = next((t for t in tr if t["KIND"] == "sanction_estimate" and t["CURRENCY"] == "USD"), None)
            if s:
                sanc, sanc_src = _num(s["VALUE_MM"]), s["SOURCE_URL"]
        sanc_local = next((t for t in tr if t["KIND"] == "sanction_estimate" and t["CURRENCY"] != "USD"), None)
        final = _num(r.get("ACTUAL_COST_USD_MM"))
        final_ccy, final_kind, final_src = ("USD", "final (register)", r.get("SOURCE_URL", "")) if final else ("", "", "")
        f = [t for t in tr if t["KIND"] in ("final_outturn", "final_forecast")]
        if f:
            f.sort(key=lambda t: (t["KIND"] != "final_outturn", t["STATEMENT_DATE"]))
            t = f[0]
            final, final_ccy, final_kind, final_src = _num(t["VALUE_MM"]), t["CURRENCY"], t["KIND"], t["SOURCE_URL"]
        aw = by_award.get(p, [])
        valued = [a for a in aw if award_has_value(a)]
        pk_valued = sorted({award_package(a) for a in valued} - {"other"})
        pk_any = sorted({award_package(a) for a in aw} - {"other"})
        wd = _num(r.get("WATER_DEPTH_M"))
        wd_src = "cost table" if wd is not None else ""
        bwells = bwb = None
        codes = gmap.get(p, {}).get("FIELD_NAME_CODES", "").split()
        if codes:
            bwb = sum(int(_num(bsee[c]["WELLBORES"]) or 0) for c in codes if c in bsee)
            bwells = sum(int(_num(bsee[c]["WELLS_API10"]) or 0) for c in codes if c in bsee)
            if wd is None:
                d = [_num(bsee[c]["AVG_WATER_DEPTH_FT"]) for c in codes if c in bsee]
                d = [x for x in d if x is not None]
                if d:
                    wd, wd_src = round(max(d) * FT_TO_M), "BSEE field average"
        wells = _num(r.get("WELL_COUNT"))
        rows.append({
            "project": p, "tier": r["TIER"], "operator": r.get("OPERATOR", ""), "region": r.get("REGION", ""),
            "country": r.get("COUNTRY", ""), "water_depth_m": wd, "water_depth_source": wd_src,
            "development_type": r.get("DEVELOPMENT_TYPE", ""), "facility": r.get("HOST_TYPE", ""),
            "wells": int(wells) if wells is not None else None, "bsee_wellbores": bwb, "bsee_wells": bwells,
            "bsee_fields": " ".join(codes), "fid_year": r.get("FID_YEAR", ""), "first_oil_year": r.get("FIRST_OIL_YEAR", ""),
            "sanction_usd_mm": sanc, "sanction_local": (f"{_num(sanc_local['VALUE_MM']):g} {sanc_local['CURRENCY']}"
                                                         if sanc_local else ""),
            "final_mm": final, "final_ccy": final_ccy, "final_kind": final_kind,
            "n_statements": len(tr) + len(upd.get(p, [])), "n_awards": len(aw), "n_awards_valued": len(valued),
            "packages_awarded": " ".join(pk_any), "packages_valued": " ".join(pk_valued),
            "source_priority": r.get("SOURCE_PRIORITY", ""), "confidence": r.get("CONFIDENCE", ""),
            "sanction_source": sanc_src, "final_source": final_src})
    rows.sort(key=lambda x: (x["region"] or "~", x["fid_year"] or "9999", x["project"]))
    inputs = {str(p.relative_to(root)).replace("\\", "/"): sha256(p) for p in
              [cost / "curated" / "sanctioned_projects.csv", cost / "curated" / "cost_revision_trails.csv",
               cost / "curated" / "contract_awards.csv", DATA / "bsee_deepwater_field_wells.csv",
               DATA / "gom_field_map.csv"] + [cost / "staging" / f for f in STAGING]}
    return {"rows": rows, "coverage": coverage(rows, bsee, gmap), "inputs": inputs,
            "updates": sorted(UPDATE_OF.values())}


def coverage(rows: list[dict], bsee: dict, gmap: dict) -> dict:
    n = len(rows)

    def c(f):
        return sum(1 for r in rows if f(r))
    mapped = {c_ for r in gmap.values() for c_ in r["FIELD_NAME_CODES"].split()}
    return {
        "projects": n,
        "curated": c(lambda r: r["tier"] == "curated"), "staged": c(lambda r: r["tier"] == "staged"),
        "trail_only": c(lambda r: r["tier"] == "trail"),
        "with_operator": c(lambda r: r["operator"]), "with_region": c(lambda r: r["region"]),
        "with_water_depth": c(lambda r: r["water_depth_m"] is not None),
        "water_depth_from_bsee": c(lambda r: r["water_depth_source"] == "BSEE field average"),
        "with_development_type": c(lambda r: r["development_type"]), "with_facility": c(lambda r: r["facility"]),
        "with_wells": c(lambda r: r["wells"] is not None), "with_bsee_wells": c(lambda r: r["bsee_wellbores"] is not None),
        "with_wells_any": c(lambda r: r["wells"] is not None or r["bsee_wellbores"] is not None),
        "with_fid": c(lambda r: r["fid_year"]),
        "with_sanction": c(lambda r: r["sanction_usd_mm"] is not None),
        "with_final": c(lambda r: r["final_mm"] is not None),
        "with_sanction_and_final": c(lambda r: r["sanction_usd_mm"] is not None and r["final_mm"] is not None),
        "with_awards": c(lambda r: r["n_awards"] > 0), "with_award_value": c(lambda r: r["n_awards_valued"] > 0),
        "with_package_split": c(lambda r: len(r["packages_valued"].split()) >= 2),
        "with_three_packages": c(lambda r: len(r["packages_valued"].split()) >= 3),
        "with_wells_facility_depth": c(lambda r: r["water_depth_m"] is not None and bool(r["facility"])
                                       and (r["wells"] is not None or r["bsee_wellbores"] is not None)),
        "with_all_fields": c(lambda r: all([r["water_depth_m"] is not None, r["development_type"], r["facility"],
                                            r["wells"] is not None or r["bsee_wellbores"] is not None,
                                            r["sanction_usd_mm"] is not None])),
        "gom_deepwater_fields": len(bsee), "gom_fields_mapped": len(mapped & set(bsee)),
        "gom_fields_no_cost_record": len(set(bsee) - mapped),
    }


def write(out_dir: Path, built: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "project_register.csv"
    rows = built["rows"]
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path
